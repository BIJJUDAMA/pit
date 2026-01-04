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
    if command == 'push':
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
    
    # Update with working directory files
    ignore_patterns = ignore.get_ignored_patterns(repo_root)
    for root, dirs, files in os.walk(repo_root):
        if '.pit' in dirs:
            dirs.remove('.pit')
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_root)
            
            if ignore.is_ignored(rel_path, ignore_patterns):
                continue
                
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                stats = os.stat(file_path)
                mtime = stats.st_mtime_ns
                size = stats.st_size
                
                # Hash object but don't strictly need to write blob if it exists? 
                # Actually, effectively we are 'adding' everything to this temp index.
                # So we must write blobs for modified/new files.
                hash_val = objects.hash_object(repo_root, content, 'blob')
                workdir_index[rel_path] = (hash_val, mtime, size)
            except:
                pass

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
    
    # Revised Workdir Capture:
    # Iterate all files in workdir -> add/update in `workdir_index`.
    # Iterate all files in `index_files` -> if not in workdir, it's a deletion check.
    # If file is in index but missing from disk, it implies it was deleted in workdir.
    # The `workdir_index` should reflect that deletion (i.e., remove from dict).
    
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
    # If no HEAD, we essentially clear everything? Or just leave it?
    # Git stash on initial commit is tricky. Assuming valid HEAD usually.
    if head_commit:
        from commands import reset, checkout
        # Hard reset: index = HEAD, workdir = HEAD
        # 1. Update index to match HEAD
        head_files = objects.get_commit_files(repo_root, head_commit)
        # Write head_files to index
        index_path = os.path.join(repo_root, '.pit', 'index')
        with open(index_path, 'w') as f:
            for path, hash_val in sorted(head_files.items()):
                # We don't have mtime/size for HEAD files easily available without stat-ing checkouts? 
                # Or just put 0.
                f.write(f"{hash_val} 0 0 {path}\n")
        
        # 2. Update workdir to match HEAD
        # Read all files in workdir, if not in HEAD remove?
        # If in HEAD, restore?
        # This is `git reset --hard`.
        # Simplest implementation for stash: 
        # Checkout HEAD with overwrite.
        # Clean untracked/modified files that were stashed?
        # The stash captured everything.
        # We need to make workdir match HEAD.
        
        # Restore HEAD files
        for path, hash_val in head_files.items():
            obj_type, content = objects.read_object(repo_root, hash_val)
            full_path = os.path.join(repo_root, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(content)
        
        # Remove files not in HEAD (but tracked or stashed?)
        # For `stash`, we usually leave untracked files alone unless `-u`.
        # Assuming standard behavior: only reset tracked files.
        # Since we updated index to HEAD, checking `git status` would show untracked.
        # We should remove changes to tracked files.
        pass # The overwrite above handles modifications to tracked files.
             # What about files added to index (newly tracked) but reset?
             # They are in `index_files` (stashed) but not in `head_files`.
             # We should remove them from workdir if they were tracked in the stash.
             # But if they are just in workdir and not in HEAD, they become untracked?
             # `git stash` removes added files from workdir.
             
        # Identify files in stash (workdir_index) that are NOT in HEAD.
        # Remove them from disk?
        for path in workdir_index:
             if path not in head_files:
                 # It was added in stash (index or workdir). Removing it to clean state.
                 full_path = os.path.join(repo_root, path)
                 if os.path.exists(full_path):
                     os.remove(full_path)
                     
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
    
    # Restore logic
    # 1. Get stash commit (workdir)
    # 2. Get its 2nd parent (index commit)
    # 3. Load index commit to Index
    # 4. Load workdir commit to Workdir
    
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

        # Restore Index
        if index_parent:
            index_files = objects.get_commit_files(repo_root, index_parent)
            index_path = os.path.join(repo_root, '.pit', 'index')
            with open(index_path, 'w') as f:
                for path, hash_val in sorted(index_files.items()):
                    f.write(f"{hash_val} 0 0 {path}\n")

        # Restore WorkDir
        # Read files from stash_commit_hash
        workdir_files = objects.get_commit_files(repo_root, stash_commit_hash)
        for path, hash_val in workdir_files.items():
            obj_type, content = objects.read_object(repo_root, hash_val)
            full_path = os.path.join(repo_root, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(content)
        
        # Remove from log
        lines.pop()
        with open(log_path, 'w') as f:
            f.write('\n'.join(lines) + ('\n' if lines else ''))
            
        print(f"Dropped refs/stash@{{{len(lines)}}} ({stash_commit_hash[:7]})")
        
    except Exception as e:
         print(f"Error popping stash: {e}")
         sys.exit(1)

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
