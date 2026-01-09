# The command: pit commit -m "<message>"
# What it does: Creates a permanent, uniquely identified snapshot (a commit object) of the currently staged changes.
# How it does: It builds a hierarchical Merkle Tree from the flat index to get a single root hash for the project's state. It then finds the parent commit, gathers metadata (author, message), and hashes them all into a new "commit" object. Finally, it updates the current branch file to point to this new commit's hash.
# What data structure it uses: Merkle Tree (to represent the project's file structure), Directed Acyclic Graph (DAG) (as each commit links to its parents, forming the history graph), Hash Table / Dictionary (the underlying object store)

import os
import sys
import time
from utils import repository, objects, config

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)
    
    parent_commit = repository.get_head_commit(repo_root) # Get the current HEAD commit hash
    parents = [parent_commit] if parent_commit else [] # List of parent commits (empty for initial commit)
    
    try:
        create_commit(repo_root, args.message, parents)
    except Exception as e:
        print(f"Error during commit: {e}", file=sys.stderr)
        sys.exit(1)

def create_commit(repo_root, message, parents): # Creates a commit object and updates the current branch
    index_path = os.path.join(repo_root, '.pit', 'index')
    if not os.path.exists(index_path) or os.path.getsize(index_path) == 0:
        raise Exception("nothing to commit, working tree clean")

    # Build the tree from the index and write it as a tree object
    tree_dict = objects.build_tree_from_index(repo_root)
    tree_hash = objects.write_tree(repo_root, tree_dict)

    user_name, user_email = config.get_user_config(repo_root)
    if not user_name or not user_email:
        raise Exception("Author identity unknown...")

    timestamp = int(time.time())
    timezone = time.strftime('%z', time.gmtime())
    author = f"{user_name} <{user_email}> {timestamp} {timezone}"
    
    lines = [f'tree {tree_hash}']
    for parent in parents:
        if parent:
            lines.append(f'parent {parent}')
    lines.append(f'author {author}')
    lines.append(f'committer {author}')
    lines.append('')
    lines.append(message)
    
    commit_content = '\n'.join(lines).encode()
    commit_hash = objects.hash_object(repo_root, commit_content, 'commit')
    
    current_branch = repository.get_current_branch(repo_root)
    if current_branch:
        branch_ref_path = os.path.join(repo_root, '.pit', 'refs', 'heads', current_branch)
        with open(branch_ref_path, 'w') as f:
            f.write(f"{commit_hash}\n")
    else:
        # Detached HEAD - update HEAD file directly
        head_path = os.path.join(repo_root, '.pit', 'HEAD')
        with open(head_path, 'w') as f:
            f.write(f"{commit_hash}\n")
        
    print(f"[{current_branch} {commit_hash[:7]}] {message.splitlines()[0]}")
    
    return commit_hash