# The command: pit status
# What it does: Provides a summary of the repository state by comparing the HEAD commit, the index (staging area), and the working directory
# How it does: It generates three dictionaries of {path: hash} for the three states. It then compares these dictionaries to find staged changes (HEAD vs. index), unstaged changes (index vs. workdir), and untracked files (files in workdir but not in index)
# What data structure it uses: Hash Table / Dictionary (to represent the three states for efficient O(1) average time complexity lookups), Sets (for efficient comparison of file lists to find additions/deletions in O(N) time)

import os
import sys
from utils import repository, objects, ignore, index as index_utils

def run(args): # Compares the HEAD, index, and working directory states and prints the status
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    # Use centralized function for HEAD status
    print(repository.get_head_status(repo_root))

    # Get status of HEAD vs Index (staged changes)
    head_commit = repository.get_head_commit(repo_root)
    head_files = objects.get_commit_files(repo_root, head_commit) if head_commit else {}
    
    # Get index files using centralized function
    index_files = index_utils.read_index_hashes(repo_root)

    # Get status of Index vs Working Directory (unstaged changes)
    working_files = {}
    ignore_patterns = ignore.get_ignored_patterns(repo_root)
    for root, dirs, files in os.walk(repo_root):
        # Filter out the .pit directory
        if '.pit' in dirs:
            dirs.remove('.pit')
            
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_root)
            
            if not ignore.is_ignored(rel_path, ignore_patterns):
                with open(file_path, 'rb') as f:
                    content = f.read()
                working_files[rel_path] = objects.hash_object(repo_root, content, 'blob', write=False)
    
    #Comapring staged and unstaged changes
    staged_changes = _compare_dicts(head_files, index_files)
    unstaged_changes = _compare_dicts(index_files, working_files)
    
    # Untracked files are in working dir but not in index
    untracked_files = sorted(list(set(working_files.keys()) - set(index_files.keys())))

    _print_status("Changes to be committed", staged_changes)
    _print_status("Changes not staged for commit", {'modified': unstaged_changes['modified'], 'deleted': unstaged_changes['deleted']})


    if untracked_files:
        print("\nUntracked files:")
        print("  (use \"pit add <file>...\" to include in what will be committed)")
        for path in untracked_files:
            print(f"\t{path}")

def _compare_dicts(d1, d2): # Compares two {path: hash} dictionaries and returns a dict of changes
    changes = {'new file': [], 'modified': [], 'deleted': []}
    
    keys1, keys2 = set(d1.keys()), set(d2.keys())
    
    # New files (in d2 but not d1)
    for path in sorted(list(keys2 - keys1)):
        changes['new file'].append(path)
        
    # Deleted files (in d1 but not d2)
    for path in sorted(list(keys1 - keys2)):
        changes['deleted'].append(path)
        
    # Modified files (in both but with different hashes)
    for path in sorted(list(keys1 & keys2)):
        if d1[path] != d2[path]:
            changes['modified'].append(path)
            
    return changes

def _print_status(header, changes):
    has_changes = any(changes.values())
    if not has_changes:
        return
        
    print(f"\n{header}:")
    for change_type, paths in changes.items():
        for path in paths:
            print(f"\t{change_type}:   {path}")

