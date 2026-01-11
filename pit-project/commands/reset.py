# The command: pit reset <file>
# What it does: Unstages files by removing them from the staging area (the index). It is the opposite of `pit add`
# How it does: It uses a "filter and rewrite" strategy. It reads all entries from the current index, filters out the files the user wants to reset, and rewrites the index with the remaining entries
# What data structure it uses: Dictionary (to hold the index entries that are being kept)

import sys
import os
from utils import repository, index as index_utils

def run(args): # Executes the reset command to unstage files
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    # Read the current index using centralized function
    index = index_utils.read_index(repo_root)
    
    if not index:
        return # Nothing to do if there's no index
    
    # Filter out files to be reset
    files_reset = []
    for file_path in args.files:
        if file_path in index:
            del index[file_path]
            files_reset.append(file_path)
    
    # Write updated index using centralized function
    index_utils.write_index(repo_root, index)
    
    if files_reset:
        print("Unstaged changes after reset:")
        for file_path in files_reset:
            print(f" M {file_path}")

