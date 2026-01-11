# What it does: Provides high-level functions for interacting with the repository structure, like finding the repo root and managing branch pointers
# How it does: It reads/writes to files like `HEAD` and those in `refs/heads` to manage the repository's current state and branch locations. `find_repo_root` walks up the directory tree to locate the `.pit` directory
# What data structure it uses: Uses recursion (specifically, linear recursion) to find the repo root. Conceptually, it manages pointers (the `HEAD` file and branch files), which are fundamental components of data structures like Graphs and Linked Lists

import os

def find_repo_root(path='.'): # Recursively searches for the .pit directory to find the repository root
    path = os.path.abspath(path)
    pit_dir = os.path.join(path, '.pit')
    if os.path.isdir(pit_dir):
        return path
    parent_path = os.path.dirname(path)
    if parent_path == path:
        return None
    return find_repo_root(parent_path)

def get_head_commit(repo_root): # Retrieves the commit hash that HEAD points to, or None if there are no commits
    head_path = os.path.join(repo_root, '.pit', 'HEAD')
    if not os.path.exists(head_path):
        return None
    with open(head_path, 'r') as f:
        head_content = f.read().strip()
    if head_content.startswith('ref: '):
        ref_path = head_content.split(' ', 1)[1]
        # Convert forward slashes to OS-specific separator for file path
        ref_path_normalized = ref_path.replace('/', os.sep)
        branch_path = os.path.join(repo_root, '.pit', ref_path_normalized)
        if not os.path.exists(branch_path) or os.path.getsize(branch_path) == 0:
            return None
        with open(branch_path, 'r') as f:
            return f.read().strip()
    else:
        return head_content.strip()

def get_current_branch(repo_root): # Retrieves the name of the current branch HEAD points to, or None if in detached HEAD state
    head_path = os.path.join(repo_root, '.pit', 'HEAD')
    with open(head_path, 'r') as f:
        head_content = f.read().strip()
    if head_content.startswith('ref: refs/heads/'):
        return head_content.split('/')[-1].strip()
    return None

def get_all_branches(repo_root): # Lists all branch names by reading the refs/heads directory
    branches_dir = os.path.join(repo_root, '.pit', 'refs', 'heads')
    if not os.path.isdir(branches_dir):
        return []
    return [name for name in os.listdir(branches_dir)]

def create_branch(repo_root, branch_name, commit_hash): # Creates a new branch pointing to the given commit hash
    if not commit_hash:
        print("fatal: Not a valid object name: 'HEAD'. Cannot create branch.", file=sys.stderr)
        sys.exit(1)
    branch_path = os.path.join(repo_root, '.pit', 'refs', 'heads', branch_name)
    if os.path.exists(branch_path):
        print(f"fatal: A branch named '{branch_name}' already exists.", file=sys.stderr)
        sys.exit(1)
    with open(branch_path, 'w') as f:
        f.write(f"{commit_hash}\n")

def get_branch_commit(repo_root, branch_name): # Retrieves the commit hash that a given branch points to, or None if the branch doesn't exist
    branch_path = os.path.join(repo_root, '.pit', 'refs', 'heads', branch_name)
    if not os.path.exists(branch_path):
        return None
    with open(branch_path, 'r') as f:
        return f.read().strip()

def get_head_status(repo_root): # Returns a user-friendly string describing HEAD state
    current_branch = get_current_branch(repo_root)
    if current_branch:
        return f"On branch {current_branch}"
    else:
        head_commit = get_head_commit(repo_root)
        if head_commit:
            return f"HEAD detached at {head_commit[:7]}"
        else:
            return "HEAD detached (no commits yet)"