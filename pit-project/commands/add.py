# The command: pit add <file>
# What it does: Takes a snapshot of files from the working directory and stages them for the next commit by updating the index
# How it does: It reads the current index file into an in-memory dictionary. Then, for each specified file, it calculates a content hash (creating a "blob" object) and updates the dictionary with the file's path and new hash. Finally, it overwrites the index file with the content of the updated dictionary
# What data structure it uses: Hash Table / Dictionary (to manage the index in memory), List (to hold the list of files to add), and performs a Tree Traversal (when expanding `.` using os.walk)

import os
import sys
from utils import repository, objects, ignore

def run(args):

#Hashes file contents and stores them as blob objects.
#Updates the index file to stage the changes for the next commit.
    
    repo_root = repository.find_repo_root() #Finding the root of the repository
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    index_path = os.path.join(repo_root, '.pit', 'index')
    ignore_patterns = ignore.get_ignored_patterns(repo_root) # Load ignore patterns from .pitgnore
    
    # Read the current index into a dictionary
    index = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                index[path] = hash_val

    files_to_add = _expand_files(args.files, repo_root)

    for file_path in files_to_add:
        rel_path = os.path.relpath(file_path, repo_root)
        
        # Check if the file should be ignored
        if ignore.is_ignored(rel_path, ignore_patterns):
            continue

        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            print(f"fatal: pathspec '{file_path}' did not match any files", file=sys.stderr)
            continue
            
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Create a blob object and get its hash
            hash_val = objects.hash_object(repo_root, content, 'blob')
            
            # Update the index
            index[rel_path] = hash_val
            print(f"Added '{rel_path}' to the index.")

        except Exception as e:
            print(f"Error adding file {file_path}: {e}", file=sys.stderr)

    # Write the updated index back to the file
    try:
        with open(index_path, 'w') as f:
            for path, hash_val in sorted(index.items()):
                f.write(f"{hash_val} {path}\n")
    except Exception as e:
        print(f"Error writing to index: {e}", file=sys.stderr)
        sys.exit(1)

def _expand_files(file_args, repo_root):
    """
    Expands file arguments like '.' into a list of all files in the directory.
    """
    expanded_files = []
    if '.' in file_args or './' in file_args:
        for root, _, files in os.walk(repo_root):
            for file in files:
                full_path = os.path.join(root, file)
                expanded_files.append(full_path)
    else:
        expanded_files = [os.path.join(repo_root, f) for f in file_args]
        
    return expanded_files

