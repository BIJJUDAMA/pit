# The command: pit checkout <branch-name>
# What it does: Switches the active branch by changing which branch the special HEAD pointer is pointing to
# How it does: After validating that the requested branch exists, it overwrites the `.pit/HEAD` file with a symbolic reference to that branch (e.g., "ref: refs/heads/feature-branch")
# What data structure it uses: List (for validating branch existence against all branches). The HEAD file itself acts as a single pointer, a fundamental concept in data structures like Linked Lists and Graphs

import sys
import os
from utils import repository

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)
    
    branch_name = args.branch_name # The target branch to switch to
    branches = repository.get_all_branches(repo_root)
    
    if branch_name not in branches: # Validate branch existence
        print(f"error: pathspec '{branch_name}' did not match any file(s) known to pit", file=sys.stderr)
        sys.exit(1)

    try: # Switch the HEAD to point to the new branch
        head_path = os.path.join(repo_root, '.pit', 'HEAD')
        ref_path = f"ref: refs/heads/{branch_name}"
        with open(head_path, 'w') as f:
            f.write(f"{ref_path}\n")
        print(f"Switched to branch '{branch_name}'")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)