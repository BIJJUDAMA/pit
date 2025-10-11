# The command: pit merge <branch-name>
# What it does: Performs a three-way merge between the current branch, the target branch, and their common ancestor
# How it does: It finds the common ancestor, computes differences, and intelligently combines changes
# What data structure it uses: DAG (for finding common ancestor), Merkle Trees (for content comparison)

#Implemented 3 way diff similar to Git's
import sys
import os
from utils import repository, objects, diff as diff_utils
from commands import commit, add

def run(args): 
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    try:
        # Get current branch and the branch to merge
        current_branch = repository.get_current_branch(repo_root)
        branch_to_merge = args.branch
        
        if current_branch == branch_to_merge:
            print("Already on this branch.", file=sys.stderr)
            sys.exit(1)

        branches = repository.get_all_branches(repo_root)
        if branch_to_merge not in branches:
            print(f"fatal: '{branch_to_merge}' does not appear to be a pit repository", file=sys.stderr)
            sys.exit(1)

        # Get the commit hashes for both branches
        head_commit_hash = repository.get_head_commit(repo_root)
        merge_commit_hash = repository.get_branch_commit(repo_root, branch_to_merge)
        
        if not head_commit_hash or not merge_commit_hash:
            print("fatal: cannot merge - missing commit history", file=sys.stderr)
            sys.exit(1)

        # Find the common ancestor (merge base)
        common_ancestor = _find_common_ancestor(repo_root, head_commit_hash, merge_commit_hash)
        
        if not common_ancestor:
            print("fatal: no common ancestor found", file=sys.stderr)
            sys.exit(1)

        print(f"Merging {branch_to_merge} into {current_branch}")
        print(f"Found common ancestor: {common_ancestor[:7]}")

        # Perform three-way merge
        merge_successful = _perform_three_way_merge(repo_root, common_ancestor, head_commit_hash, merge_commit_hash)
        
        if not merge_successful:
            print("Merge failed due to conflicts. Resolve conflicts and commit manually.")
            sys.exit(1)

        # Create merge commit
        parents = [head_commit_hash, merge_commit_hash]
        message = f"Merge branch '{branch_to_merge}' into {current_branch}"
        
        new_commit_hash = commit.create_commit(repo_root, message, parents)
        
        print(f"Merge made by the 'three-way' strategy.")
        print(f"{new_commit_hash[:7]} {message}")

    except Exception as e:
        print(f"Error during merge: {e}", file=sys.stderr)
        sys.exit(1)

#Find the common ancestor of two commits using a breadth-first approach
def _find_common_ancestor(repo_root, commit1, commit2):
    if commit1 == commit2:
        return commit1
        
    visited = set()
    queue1 = [commit1]
    queue2 = [commit2]
    
    # Mark the starting commits
    ancestors1 = {commit1: True}
    ancestors2 = {commit2: True}
    
    while queue1 or queue2:
        # Process commit1's ancestors
        if queue1:
            current1 = queue1.pop(0)
            if current1 in ancestors2:
                return current1
                
            if current1 not in visited:
                visited.add(current1)
                parents = _get_commit_parents(repo_root, current1)
                for parent in parents:
                    if parent not in ancestors1:
                        ancestors1[parent] = True
                        queue1.append(parent)
        
        # Process commit2's ancestors  
        if queue2:
            current2 = queue2.pop(0)
            if current2 in ancestors1:
                return current2
                
            if current2 not in visited:
                visited.add(current2)
                parents = _get_commit_parents(repo_root, current2)
                for parent in parents:
                    if parent not in ancestors2:
                        ancestors2[parent] = True
                        queue2.append(parent)
    
    return None
#Get all parent commits
def _get_commit_parents(repo_root, commit_hash):
    try:
        obj_type, content = objects.read_object(repo_root, commit_hash)
        if obj_type != 'commit':
            return []
            
        lines = content.decode().splitlines()
        parents = []
        for line in lines:
            if line.startswith('parent '):
                parents.append(line.split(' ')[1])
        return parents
    except:
        return []

def _perform_three_way_merge(repo_root, ancestor_hash, head_hash, merge_hash):
    """Perform three-way merge between common ancestor, current HEAD, and merge target"""
    
    # Get file states from all three commits
    ancestor_files = objects.get_commit_files(repo_root, ancestor_hash)
    head_files = objects.get_commit_files(repo_root, head_hash)
    merge_files = objects.get_commit_files(repo_root, merge_hash)
    
    all_files = set(ancestor_files.keys()) | set(head_files.keys()) | set(merge_files.keys())
    conflicts = []
    
    # Read current index
    index_path = os.path.join(repo_root, '.pit', 'index')
    current_index = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                current_index[path] = hash_val
    
    # Process each file for three-way merge
    for file_path in sorted(all_files):
        ancestor_hash = ancestor_files.get(file_path)
        head_hash = head_files.get(file_path) 
        merge_hash = merge_files.get(file_path)
        
        result = _merge_file(repo_root, file_path, ancestor_hash, head_hash, merge_hash)
        
        if result == 'conflict':
            conflicts.append(file_path)
            print(f"CONFLICT (content): Merge conflict in {file_path}")
            _create_conflict_file(repo_root, file_path, head_hash, merge_hash)
        elif result == 'added':
            print(f"Adding {file_path}")
        elif result == 'deleted':
            print(f"Removing {file_path}")
        elif result == 'modified':
            print(f"Auto-merging {file_path}")
    
    if conflicts:
        print("\nAutomatic merge failed; fix conflicts and then commit the result.")
        return False
    
    # Write the merged index
    with open(index_path, 'w') as f:
        for path, hash_val in sorted(current_index.items()):
            f.write(f"{hash_val} {path}\n")
    
    return True

def _merge_file(repo_root, file_path, ancestor_hash, head_hash, merge_hash):
    """Merge a single file using three-way merge algorithm"""
    
    # Case 1: File unchanged in both branches
    if head_hash == merge_hash:
        return 'unchanged'
    
    # Case 2: File deleted in both branches
    if head_hash is None and merge_hash is None:
        return 'unchanged'
    
    # Case 3: File unchanged from ancestor in HEAD
    if head_hash == ancestor_hash:
        if merge_hash is not None:
            # Take the version from merge branch
            _stage_file_version(repo_root, file_path, merge_hash)
            return 'added' if ancestor_hash is None else 'modified'
        else:
            # File was deleted in merge branch
            _remove_file(repo_root, file_path)
            return 'deleted'
    
    # Case 4: File unchanged from ancestor in merge branch  
    if merge_hash == ancestor_hash:
        if head_hash is not None:
            # Keep the version from HEAD
            _stage_file_version(repo_root, file_path, head_hash)
            return 'unchanged'
        else:
            # File was deleted in HEAD
            _remove_file(repo_root, file_path)
            return 'unchanged'
    
    # Case 5: Both branches made different changes - CONFLICT
    if head_hash != merge_hash:
        return 'conflict'
    
    return 'unchanged'

def _stage_file_version(repo_root, file_path, blob_hash):
    """Stage a specific version of a file"""
    index_path = os.path.join(repo_root, '.pit', 'index')
    
    # Read current index
    current_index = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                current_index[path] = hash_val
    
    # Update index with new version
    current_index[file_path] = blob_hash
    
    # Write file content to working directory
    obj_type, content = objects.read_object(repo_root, blob_hash)
    if obj_type == 'blob':
        full_path = os.path.join(repo_root, file_path)
        dir_name = os.path.dirname(full_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(content)
    
    # Write updated index
    with open(index_path, 'w') as f:
        for path, hash_val in sorted(current_index.items()):
            f.write(f"{hash_val} {path}\n")

def _remove_file(repo_root, file_path):
    """Remove a file from index and working directory"""
    index_path = os.path.join(repo_root, '.pit', 'index')
    
    # Read current index
    current_index = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                current_index[path] = hash_val
    
    # Remove from index
    if file_path in current_index:
        del current_index[file_path]
    
    # Remove from working directory
    full_path = os.path.join(repo_root, file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    
    # Write updated index
    with open(index_path, 'w') as f:
        for path, hash_val in sorted(current_index.items()):
            f.write(f"{hash_val} {path}\n")

def _create_conflict_file(repo_root, file_path, head_hash, merge_hash):
    full_path = os.path.join(repo_root, file_path)
    dir_name = os.path.dirname(full_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    
    conflict_content = []
    
    # Add HEAD version
    conflict_content.append("<<<<<<< HEAD")
    if head_hash:
        obj_type, content = objects.read_object(repo_root, head_hash)
        if obj_type == 'blob':
            conflict_content.append(content.decode('utf-8', errors='ignore'))
    else:
        conflict_content.append("(file does not exist in HEAD)")
    
    # Add separator
    conflict_content.append("=======")
    
    # Add MERGE version  
    if merge_hash:
        obj_type, content = objects.read_object(repo_root, merge_hash)
        if obj_type == 'blob':
            conflict_content.append(content.decode('utf-8', errors='ignore'))
    else:
        conflict_content.append("(file does not exist in merge branch)")
    
    # Add end marker
    conflict_content.append(">>>>>>> " + file_path)
    
    # Write conflict file
    with open(full_path, 'w') as f:
        f.write('\n'.join(conflict_content))