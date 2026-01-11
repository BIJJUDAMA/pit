# The command: pit stash [push|pop|list|clear]
# What it does: Temporarily stores the current state of the index and working directory to a stash stack, allowing users to switch contexts.
# How it does: It creates two commit objects: one representing the index state and another representing the working directory state (which points to the index commit as a parent). These commits are stored in a reflog file `.pit/logs/stash`. `reset` is used to revert the workspace after pushing. `pop` restores these states.
# What data structure it uses: Stack (implemented via the append-only reflog file `.pit/logs/stash`), Trees/Commits (to persist state).

import os
import sys
import time
from utils import repository, objects, config, ignore

def run(args):
    command = args.stash_command
    if command == 'push' or command is None:
        # Default to push if no subcommand (mimics git behavior)
        push(args)
    elif command == 'pop':
        pop(args)
    elif command == 'list':
        list_stashes(args)
    elif command == 'clear':
        clear_stashes(args)
    else:
        # Default to push if no subcommand (or mimic git behavior? stick to explicit for now)
        # Actually argparse requires subcommand if configured that way.
        # But if we want `pit stash` to default to push, we need to handle that in pit.py parser.
        # For now let's assume specific subcommand is required or `push` is default if args allows.
        print(f"Unknown stash command: {command}", file=sys.stderr)
        sys.exit(1)

def push(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    head_commit = repository.get_head_commit(repo_root)
    # Allow stash even if no HEAD (initial commit not yet made)? 
    # Git allows stashing initial state if things are added.
    # But our commit logic requires parents for non-root.
    # If no HEAD, parent is empty list.
    
    # 1. Create Index Commit (state of the staging area)
    index_files = objects.read_index(repo_root)
    # Build tree from index
    tree_dict_idx = objects.build_tree_from_dict(index_files)
    tree_hash_idx = objects.write_tree(repo_root, tree_dict_idx)
    
    # Create commit object for index
    idx_parents = [head_commit] if head_commit else []
    index_commit_hash = _create_stash_commit(repo_root, tree_hash_idx, idx_parents, f"index on {repository.get_current_branch(repo_root)}: {head_commit[:7] if head_commit else 'initial'}")

    # 2. Create Workdir Commit (state of working directory, including staged and unstaged changes)
    # We need to scan working dir, similar to `add.py`, but not write to index file.
    # We construct an in-memory index representing the workdir state.
    
    workdir_index = index_files.copy() # Start with index state
    


    # Handle deleted files?
    # If file is in index but not in working dir, it should be removed from workdir_index.
    # But os.walk only finds existing files.
    # So we must check if keys in `index_files` (staged) exist in disk?
    # Wait, `add -A` logic handles deletions.
    # Only files present in workdir or index matter.
    # Correct logic:
    # 1. Start with Empty index? No, untracked files are captured if we want `git stash -u`.
    # Standard `git stash` captures tracked files modification. 
    # Let's simplify: Capture everything currently in workdir + things in index that might be deleted in workdir.
    
    # Updated Workdir Capture:
    # Only capture tracked files (in HEAD) or staged files (in Index).
    # Ignore strictly untracked files.
    
    # Identify tracked files
    head_files = objects.get_commit_files(repo_root, head_commit) if head_commit else {}
    tracked_files = set(head_files.keys()) if head_files else set()
    staged_files = set(index_files.keys())
    
    ignore_patterns = ignore.get_ignored_patterns(repo_root)
    for root, dirs, files in os.walk(repo_root):
        if '.pit' in dirs:
            dirs.remove('.pit')
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_root)
            
            if ignore.is_ignored(rel_path, ignore_patterns):
                continue

            # Skip if not tracked and not staged
            if rel_path not in tracked_files and rel_path not in staged_files:
                continue
                
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                stats = os.stat(file_path)
                mtime = stats.st_mtime_ns
                size = stats.st_size
                
                hash_val = objects.hash_object(repo_root, content, 'blob')
                workdir_index[rel_path] = (hash_val, mtime, size)
            except:
                pass
    
    for path in list(workdir_index.keys()):
        full_path = os.path.join(repo_root, path)
        if not os.path.exists(full_path):
            del workdir_index[path]

    tree_dict_wd = objects.build_tree_from_dict(workdir_index)
    tree_hash_wd = objects.write_tree(repo_root, tree_dict_wd)
    
    # Workdir commit parent is HEAD (or empty) AND Index commit
    wd_parents = [head_commit] if head_commit else []
    wd_parents.append(index_commit_hash)
    
    # Message
    msg = args.message if hasattr(args, 'message') and args.message else f"WIP on {repository.get_current_branch(repo_root)}: {head_commit[:7] if head_commit else 'initial'}"
    workdir_commit_hash = _create_stash_commit(repo_root, tree_hash_wd, wd_parents, msg)
    
    # 3. Write to Reflog
    log_path = os.path.join(repo_root, '.pit', 'logs', 'stash')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a') as f:
        f.write(f"{workdir_commit_hash}\n")
        
    print(f"Saved working directory and index state {workdir_commit_hash[:7]}: {msg}")
    
    # 4. Reset Workspace to HEAD
    if head_commit:
        from commands import reset, checkout
        
        # 1. Update index to match HEAD
        # Write head_files to index
        index_path = os.path.join(repo_root, '.pit', 'index')
        with open(index_path, 'w') as f:
            for path, hash_val in sorted(head_files.items()):
                f.write(f"{hash_val} 0 0 {path}\n")
        
        # 2. Update workdir to match HEAD
        # Restore HEAD files
        for path, hash_val in head_files.items():
            obj_type, content = objects.read_object(repo_root, hash_val)
            full_path = os.path.join(repo_root, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(content)
        
        # Clean up files that were stashed (modified/added) but are not in HEAD
        # (i.e. revert changes to tracked files, and remove staged new files)
        # Note: We must NOT delete untracked files that were NOT stashed.
        
        # Iterate files in workdir_index (which contains everything we stashed)
        for path in workdir_index:
             if path not in head_files:
                 # It was in the stash, but not in HEAD. It must be a file we added to index.
                 # Since we are resetting to HEAD, we should remove it.
                 full_path = os.path.join(repo_root, path)
                 if os.path.exists(full_path):
                     os.remove(full_path)
             # If path IS in head_files, we already overwrote it above with HEAD version.

                     
    else:
        # No HEAD. Stash saves everything. Reset means empty?
        # Remove all tracked-like files?
        pass


def pop(args):
    repo_root = repository.find_repo_root()
    log_path = os.path.join(repo_root, '.pit', 'logs', 'stash')
    
    if not os.path.exists(log_path):
        print("No stash entries found.")
        return

    # Read log
    with open(log_path, 'r') as f:
        lines = f.read().splitlines()
        
    if not lines:
        print("No stash entries found.")
        return
        
    stash_commit_hash = lines[-1]
    
    # Overwrite Protection
    # Check if working directory or index is dirty
    if not _is_clean(repo_root):
        print("error: Your local changes would be overwritten by pop.", file=sys.stderr)
        return

    try:
        # Get commit object
        obj_type, content = objects.read_object(repo_root, stash_commit_hash)
        lines_content = content.decode().splitlines()
        parents = []
        for line in lines_content:
            if line.startswith('parent '):
                parents.append(line.split(' ')[1])
        
        if len(parents) < 2:
             print("Error: Stash commit seems corrupted (missing index parent).")
             # Fallback: just restore stash commit as workdir?
             index_parent = None
        else:
             index_parent = parents[1] # Parent 0 is HEAD, Parent 1 is Index Commit

        # Restore WorkDir
        workdir_files = objects.get_commit_files(repo_root, stash_commit_hash)
        for path, hash_val in workdir_files.items():
            obj_type, content = objects.read_object(repo_root, hash_val)
            full_path = os.path.join(repo_root, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(content)

        # Restore Index
        # We need to build the index dictionary.
        # While building, if the file content in index matches workdir, we grab the stat from disk.
        if index_parent:
            index_files = objects.get_commit_files(repo_root, index_parent)
            index_path = os.path.join(repo_root, '.pit', 'index')
            with open(index_path, 'w') as f:
                for path, hash_val in sorted(index_files.items()):
                    # Check if file on disk matches hash (implicit via hash match)
                    mtime = 0
                    size = 0
                    
                    if path in workdir_files and workdir_files[path] == hash_val:
                        # Content matches! Use real stats.
                        full_path = os.path.join(repo_root, path)
                        if os.path.exists(full_path):
                            stats = os.stat(full_path)
                            mtime = stats.st_mtime_ns
                            size = stats.st_size
                            
                    f.write(f"{hash_val} {mtime} {size} {path}\n")

        # Remove from log
        lines.pop()
        with open(log_path, 'w') as f:
            f.write('\n'.join(lines) + ('\n' if lines else ''))
            
        print(f"Dropped refs/stash@{{{len(lines)}}} ({stash_commit_hash[:7]})")
        
    except Exception as e:
         print(f"Error popping stash: {e}")
         sys.exit(1)

def _is_clean(repo_root):
    from utils import diff as diff_utils
    
    # Check HEAD vs Index
    head_commit = repository.get_head_commit(repo_root)
    files1_head = objects.get_commit_files(repo_root, head_commit) if head_commit else {}
    
    index_full = objects.read_index(repo_root)
    files2_idx = {path: data[0] for path, data in index_full.items()}
    
    staged = diff_utils.compare_states(files1_head, files2_idx)
    if any(staged.values()):
        return False
        
    # Check Index vs Workdir
    # Reuse diff._get_working_dir_files? Or status logic.
    # Let's import from COMMANDS.diff is tricky due to circular imports potential.
    # Re-implement simple logic or import cautiously. 
    # Actually stash.py imports utils.objects.
    # Let's import diff logic from commands.diff if possible or copy `_get_working_dir_files`.
    # Copying _get_working_dir_files logic is safer to avoid circular dep with commands module structure.
    
    working_files = {}
    ignore_patterns = ignore.get_ignored_patterns(repo_root)
    for root, dirs, files in os.walk(repo_root):
        if '.pit' in dirs:
            dirs.remove('.pit')
        for file in files:
            path = os.path.relpath(os.path.join(root, file), repo_root)
            if not ignore.is_ignored(path, ignore_patterns):
                 try:
                    with open(os.path.join(root, file), 'rb') as f:
                         content = f.read()
                    working_files[path] = objects.hash_object(repo_root, content, 'blob', write=False)
                 except: pass
                 
    unstaged = diff_utils.compare_states(files2_idx, working_files)
    if any(unstaged['modified']) or any(unstaged['deleted']):
        # Note: untracked files (new file in unstaged) usually don't block pop in git unless they conflict.
        # Provide strict safety: if ANY modified/deleted, abort.
        return False
        
    return True

def list_stashes(args):
    repo_root = repository.find_repo_root()
    log_path = os.path.join(repo_root, '.pit', 'logs', 'stash')
    if not os.path.exists(log_path):
        return

    with open(log_path, 'r') as f:
        lines = f.read().splitlines()
        
    for i, commit_hash in enumerate(reversed(lines)):
        # Read message
        try:
            obj_type, content = objects.read_object(repo_root, commit_hash)
            msg = ""
            for line in content.decode().splitlines():
                if not line.startswith('tree') and not line.startswith('parent') and not line.startswith('author') and not line.startswith('committer') and line.strip():
                    msg = line
                    break # Take first non-header line? Actually message is after empty line.
            
            # Better message extraction using existing utils if possible, or parse simply
            parts = content.decode().split('\n\n', 1)
            if len(parts) > 1:
                msg = parts[1].splitlines()[0]
                
            print(f"stash@{{{i}}}: {msg}")
        except:
             print(f"stash@{{{i}}}: {commit_hash[:7]}")

def clear_stashes(args):
    repo_root = repository.find_repo_root()
    log_path = os.path.join(repo_root, '.pit', 'logs', 'stash')
    if os.path.exists(log_path):
        os.remove(log_path)
    print("Stash entries cleared.")

def _create_stash_commit(repo_root, tree_hash, parents, message):
    user_name, user_email = config.get_user_config(repo_root)
    timestamp = int(time.time())
    timezone = time.strftime('%z', time.gmtime())
    author = f"{user_name or 'Pit User'} <{user_email or 'pit@example.com'}> {timestamp} {timezone}"
    
    lines = [f'tree {tree_hash}']
    for p in parents:
        lines.append(f'parent {p}')
    lines.append(f'author {author}')
    lines.append(f'committer {author}')
    lines.append('')
    lines.append(message)
    
    content = '\n'.join(lines).encode()
    return objects.hash_object(repo_root, content, 'commit')
