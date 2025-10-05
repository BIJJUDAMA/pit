# The command: pit merge <branch-name>
# What it does: Joins two branches by creating a new, special "merge commit" that has two parents
# How it does: It finds the latest commit hashes from both the current branch (parent 1) and the target branch (parent 2). It then reuses the `create_commit` function, passing it a list containing both parent hashes, which creates a commit object with two `parent` entries
# What data structure it uses: This is an operation on a Directed Acyclic Graph (DAG). It creates a new node (commit) with two parent pointers, thus merging two distinct paths in the graph

import sys
from utils import repository, objects
from commands import commit

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
        
        # NOTE: This is a simplified merge. It does not handle content merging or conflicts.
        # It simply merges the histories by creating a new commit with two parents.
        
        # Create commit object with two parents
        parents = [head_commit_hash, merge_commit_hash]
        message = f"Merge branch '{branch_to_merge}' into {current_branch}"
        
        # Use the commit logic to create the new commit
        new_commit_hash = commit.create_commit(repo_root, message, parents)
        
        print(f"Merge made by the 'recursive' strategy.")
        print(f"{new_commit_hash[:7]} {message}")

    except Exception as e:
        print(f"Error during merge: {e}", file=sys.stderr)
        sys.exit(1)
