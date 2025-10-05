# The command: pit reset <file>
# What it does: Unstages files by removing them from the staging area (the index). It is the opposite of `pit add`
# How it does: It uses a "filter and rewrite" strategy. It reads all lines from the current index file into an in-memory list, excluding lines for files that the user wants to reset. It then overwrites the index file with the contents of this filtered list
# What data structure it uses: List / Array (to temporarily hold the index lines that are being kept)

import sys
import os
from utils import repository

def run(args): #Executes the reset command to unstage files
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    index_path = os.path.join(repo_root, '.pit', 'index')
    
    if not os.path.exists(index_path):
        return # Nothing to do if there's no index

    lines_to_keep = []
    try:
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                # If the path is not one of the files to be reset, keep it
                if path not in args.files:
                    lines_to_keep.append(line)
        
        with open(index_path, 'w') as f:
            f.writelines(lines_to_keep)
        
        print("Unstaged changes after reset:")
        for file_path in args.files:
            print(f" M {file_path}")

    except Exception as e:
        print(f"Error resetting files: {e}", file=sys.stderr)
        sys.exit(1)
