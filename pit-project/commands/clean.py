# The command: pit clean
# What it does: Removes untracked files and directories from the working tree to maintain a clean workspace
# How it does: It identifies untracked items by comparing the working directory's contents with the index, while strictly respecting .pitignore rules. It supports preview (dry-run) and forced deletion modes
# What data structure it uses: Set (for efficient lookup of tracked files and directories), List (to store candidate items for removal), and Tree Traversal (using os.walk to scan the repository)

import os
import sys
import shutil
from utils import repository, ignore, index as index_utils

def run(args): #Starts the workspace cleanup process
    repo_root = repository.find_repo_root() # Locats the repository root directory
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    # Get tracked files from index using centralized function
    index_data = index_utils.read_index(repo_root)
    index_files = set()
    for path in index_data.keys():
        # Normalizing path and case to support cross-OS comparisons
        norm_path = os.path.normpath(path)
        index_files.add(os.path.normcase(norm_path))

    ignore_patterns = ignore.get_ignored_patterns(repo_root) 
    
    tracked_dirs = set() # Tracking parent directories of all indexed files
    for f in index_files:
        path_parts = f.split(os.sep)
        for i in range(1, len(path_parts)):
            tracked_dirs.add(os.sep.join(path_parts[:i]))

    untracked_files = [] #Candidates for file removal
    untracked_dirs = [] #Candidates for directory removal

    for root, dirs, files in os.walk(repo_root): #Walking the repository tree
        if '.pit' in dirs: # Always skip the internal .pit directory
            dirs.remove('.pit')
        
        rel_root = os.path.relpath(root, repo_root)
        if rel_root == '.':
            rel_root = ""

        for d in list(dirs): # Identifying untracked directories
            d_rel_path = os.path.normpath(os.path.join(rel_root, d)).lstrip(os.sep)
            if d_rel_path == '.':
                d_rel_path = ""
            
            if ignore.is_ignored(d_rel_path, ignore_patterns): # respecting .pitignore
                dirs.remove(d)
                continue
            
            if getattr(args, 'd', False): # Only clean directories if -d is specified
                norm_d_path = os.path.normcase(d_rel_path)
                if norm_d_path not in tracked_dirs:
                    untracked_dirs.append(d_rel_path)
                    dirs.remove(d)

        for f in files: # Identifying untracked files
            f_rel_path = os.path.normpath(os.path.join(rel_root, f)).lstrip(os.sep)
            if f_rel_path == '.':
                f_rel_path = ""
            
            norm_f_path = os.path.normcase(f_rel_path)
            # Add to clean list if not tracked and not ignored
            if norm_f_path not in index_files and not ignore.is_ignored(f_rel_path, ignore_patterns):
                untracked_files.append(f_rel_path)

    items_to_clean = sorted(untracked_files + untracked_dirs)

    if not items_to_clean: # Exit if everything is already clean
        return

    force = getattr(args, 'f', False) # Check for force flag
    dry_run = getattr(args, 'n', False) # Check for dry-run flag

    if not force and not dry_run: # Prevent accidental deletion by default
        print("Would remove:")
        for item in items_to_clean:
            if item in untracked_dirs:
                print(f"  {item}/")
            else:
                print(f"  {item}")
        print("\nUse 'pit clean -f' to delete them.")
        return

    if dry_run: # Preview mode
        for item in items_to_clean:
            if item in untracked_dirs:
                print(f"Would remove {item}/")
            else:
                print(f"Would remove {item}")
        return

    for item in items_to_clean: # Executing physical deletion
        item_path = os.path.join(repo_root, item)
        if os.path.isdir(item_path):
            print(f"Removing {item}/")
            shutil.rmtree(item_path)
        elif os.path.exists(item_path):
            print(f"Removing {item}")
            os.remove(item_path)
