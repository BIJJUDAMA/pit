# The command: pit branch [<branch-name>]
# What it does: Creates a new branch pointer to the current commit, or if no name is given, it lists all existing branches
# How it does: To create a branch, it gets the current HEAD commit hash and writes it to a new file named `<branch-name>` inside `.pit/refs/heads`
# To list branches, it reads all the filenames in that directory and prints them, marking the current one with an asterisk
# What data structure it uses: Map / Dictionary (conceptually, the `refs/heads` directory maps branch names to commit hashes), List (to hold branch names for sorting and display)

import os
import sys
from utils import repository

def run(args):
#With no arguments, lists all branches.
#With an argument, creates a new branch.

    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    if args.name:
        # Create a new branch
        try:
            head_commit_hash = repository.get_head_commit(repo_root)
            repository.create_branch(repo_root, args.name, head_commit_hash)
            print(f"Branch '{args.name}' created at commit {head_commit_hash[:7]}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # List all branches
        current_branch = repository.get_current_branch(repo_root)
        branches = repository.get_all_branches(repo_root)
        for branch in sorted(branches):
            if branch == current_branch:
                print(f"* {branch}")
            else:
                print(f"  {branch}")
