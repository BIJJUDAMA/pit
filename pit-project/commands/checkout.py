# The command: pit checkout [-b] <branch-name> | <file>...
# What it does: Switches branches (updating HEAD, index, and working directory) or restores files. Supports creating a new branch with -b.
# How it does:
#   - Checks for a dirty working tree (uncommitted changes) and aborts if unsafe.
#   - If -b is present, creates a new branch ref pointing to current HEAD.
#   - Swaps the working directory files to match the target commit tree (creates, updates, deletes).
#   - Rewrites the .pit/index to match the target commit.
#   - Updates .pit/HEAD to point to the new branch.
# What data structure it uses:
#   - Dictionary/Hash Table: For loading the index and commit trees ({path: hash}) to efficiently compare differences (O(1) lookups).
#   - Set: To compute file differences (additions, deletions) between current and target trees using set operations (difference, intersection) in O(N).

import sys
import os
import shutil
from utils import repository, objects, ignore

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    targets = args.targets
    create_branch = args.branch

    # Case 1: checkout -b <new_branch>
    if create_branch:
        if len(targets) != 1:
            print("fatal: -b requires exactly one branch name", file=sys.stderr)
            sys.exit(1)
        new_branch_name = targets[0]
        handle_create_and_checkout(repo_root, new_branch_name)
    
    # Case 2: checkout <branch_name>
    elif len(targets) == 1 and _is_branch(repo_root, targets[0]):
        handle_branch_checkout(repo_root, targets[0])
        
    # Case 3: checkout <file>...
    else:
        handle_file_restore(repo_root, targets)

def _is_branch(repo_root, name):
    branches = repository.get_all_branches(repo_root)
    return name in branches

def handle_create_and_checkout(repo_root, branch_name):
    # 1. Check if branch already exists
    if _is_branch(repo_root, branch_name):
        print(f"fatal: A branch named '{branch_name}' already exists.", file=sys.stderr)
        sys.exit(1)
    
    # 2. Create the branch pointing to current HEAD
    head_commit = repository.get_head_commit(repo_root)
    if not head_commit:
        print("fatal: You have no commits to branch from.", file=sys.stderr)
        sys.exit(1)
        
    # Create the branch ref
    repository.create_branch(repo_root, branch_name, head_commit)
    
    # 3. Perform checkout (transition from current to new, which are identical commit-wise)
    # We still run validation to be safe and consistent with requirements
    perform_checkout(repo_root, branch_name)

def handle_branch_checkout(repo_root, branch_name):
    current_branch = repository.get_current_branch(repo_root)
    if current_branch == branch_name:
        print(f"Already on '{branch_name}'")
        return # Standard behavior usually returns status 0
        
    perform_checkout(repo_root, branch_name)

def perform_checkout(repo_root, target_branch):
    # 1. Validate clean state
    if not is_clean(repo_root):
        print("error: Your local changes to the following files would be overwritten by checkout:", file=sys.stderr)
        print("       (Please commit your changes or stash them before you switch branches.)", file=sys.stderr)
        sys.exit(1)
        
    # 2. Get trees
    target_commit_hash = repository.get_branch_commit(repo_root, target_branch)
    target_files = objects.get_commit_files(repo_root, target_commit_hash) if target_commit_hash else {}
    
    current_commit_hash = repository.get_head_commit(repo_root)
    # Note: If we are in detached HEAD or initial state, current files might differ.
    # We use the current committed state as the baseline for swapping.
    current_files = objects.get_commit_files(repo_root, current_commit_hash) if current_commit_hash else {}

    # 3. Apply tree swap (Update Working Directory)
    update_working_directory(repo_root, current_files, target_files)
    
    # 4. Rewrite Index
    update_index(repo_root, target_files)
    
    # 5. Update HEAD
    head_path = os.path.join(repo_root, '.pit', 'HEAD')
    ref_path = f"ref: refs/heads/{target_branch}"
    with open(head_path, 'w') as f:
        f.write(f"{ref_path}\n")
        
    print(f"Switched to branch '{target_branch}'")


def is_clean(repo_root):
    # Check HEAD vs Index vs Working Tree
    # 1. HEAD vs Index
    head_commit = repository.get_head_commit(repo_root)
    head_files = objects.get_commit_files(repo_root, head_commit) if head_commit else {}
    
    index_files = load_index(repo_root)
    
    # Compare keys and hashes
    if head_files != index_files:
        return False # Staged changes exist
        
    # 2. Index vs Working Dir
    # We need to scan working dir
    ignore_patterns = ignore.get_ignored_patterns(repo_root)
    for root, dirs, files in os.walk(repo_root):
        if '.pit' in dirs:
            dirs.remove('.pit')
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_root)
            
            if ignore.is_ignored(rel_path, ignore_patterns):
                continue
                
            # If file in working dir but not in index -> Untracked (Dirty?)
            # Usually untracked files are ignored by checkout unless they would be overwritten.
            # But requirement says "Validate that no uncommitted or unstaged changes exist".
            # This usually refers to tracked files.
            # "If any tracked file differs, stop..." (from requirements technical detail)
            
            if rel_path in index_files:
                # Check contents
                with open(file_path, 'rb') as f:
                    content = f.read()
                current_hash = objects.hash_object(repo_root, content, 'blob', write=False)
                if current_hash != index_files[rel_path]:
                    return False # Modified tracked file
            
            # If unsaved/untracked file exists and TARGET has a file with same name, we should error.
            # But the requirement "If any tracked file differs" implies we focus on tracked changes.
    
    # Also check if files in index are missing from working dir
    for rel_path in index_files:
        full_path = os.path.join(repo_root, rel_path)
        if not os.path.exists(full_path):
            return False # Deleted tracked file
            
    return True

def load_index(repo_root):
    index_path = os.path.join(repo_root, '.pit', 'index')
    index_files = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                index_files[path] = hash_val
    return index_files

def update_working_directory(repo_root, current_files, target_files):
    # Calculate diff
    # Files to delete: in current but not in target
    files_to_delete = set(current_files.keys()) - set(target_files.keys())
    
    # Files to create/update: in target
    for rel_path, params_hash in target_files.items():
        full_path = os.path.join(repo_root, rel_path)
        
        should_write = False
        if rel_path not in current_files:
            should_write = True # New file
        elif current_files[rel_path] != params_hash:
            should_write = True # Changed file
            
        if should_write:
            obj_type, content = objects.read_object(repo_root, params_hash)
            if obj_type != 'blob':
                print(f"warning: skipped non-blob object {rel_path}", file=sys.stderr)
                continue
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(content)
                
    # Delete files
    for rel_path in files_to_delete:
        full_path = os.path.join(repo_root, rel_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            # Potentially remove empty dirs
            cleanup_empty_dirs(repo_root, os.path.dirname(full_path))
            
def cleanup_empty_dirs(repo_root, dir_path):
    if dir_path == repo_root or not dir_path.startswith(repo_root):
        return
    try:
        os.rmdir(dir_path) # Fails if not empty
        cleanup_empty_dirs(repo_root, os.path.dirname(dir_path))
    except OSError:
        pass

def update_index(repo_root, target_files):
    index_path = os.path.join(repo_root, '.pit', 'index')
    with open(index_path, 'w') as f:
        for rel_path, sha1 in sorted(target_files.items()):
            f.write(f"{sha1} {rel_path}\n")

def handle_file_restore(repo_root, targets):
    # Existing file checkout logic (Refactored)
    print("Restoring file(s) from index...")
    index_files = load_index(repo_root)
    files_restored = 0
    errors_occurred = 0
    
    for file_target in targets:
        abs_target_path = os.path.abspath(file_target)
        rel_path = os.path.relpath(abs_target_path, repo_root)
        
        if rel_path in index_files:
            blob_hash = index_files[rel_path]
            try:
                obj_type, content = objects.read_object(repo_root, blob_hash)
                if obj_type == 'blob':
                    full_path = os.path.join(repo_root, rel_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'wb') as f_work:
                        f_work.write(content)
                    print(f"Restored '{rel_path}'")
                    files_restored += 1
                else: 
                     errors_occurred += 1
            except Exception as e:
                print(f"Error restoring {rel_path}: {e}", file=sys.stderr)
                errors_occurred += 1
        else:
            print(f"error: pathspec '{file_target}' did not match any file(s) known to pit index.", file=sys.stderr)
            errors_occurred += 1

    if errors_occurred > 0:
        sys.exit(1)
    elif files_restored == 0:
        print("No files were restored.")