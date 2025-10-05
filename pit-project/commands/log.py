# The command: pit log
# What it does: Displays the commit history by starting at the current HEAD and walking backward through the parent links
# How it does: It starts with the current commit hash and enters a loop. Inside the loop, it reads the commit object, prints its information, and finds the parent hash. It then uses the parent hash for the next loop iteration, continuing until no parent is found. This is a classic depth-first traversal
# What data structure it uses: It performs a Graph Traversal (specifically, a linear traversal up the parent chain) on the Directed Acyclic Graph (DAG) formed by the commits

import sys
import os
from utils import repository, objects

def run(args): 
    repo_root = repository.find_repo_root()
    if not repo_root: #Check if inside a pit repository
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    commit_hash = repository.get_head_commit(repo_root)
    if not commit_hash: # Check if there are any commits
        current_branch = repository.get_current_branch(repo_root) or 'master'
        print(f"fatal: your current branch '{current_branch}' does not have any commits yet")
        return

    while commit_hash: # Traverse commits until there are no more parents
        try:
            obj_type, content = objects.read_object(repo_root, commit_hash)
        except FileNotFoundError:
            print(f"fatal: could not read commit object {commit_hash}", file=sys.stderr)
            break

        if obj_type != 'commit':
            print(f"fatal: object {commit_hash} is not a commit", file=sys.stderr)
            break

        lines = content.decode().splitlines()
        
        print(f"commit {commit_hash}")

        # Finding the first commit parent (if any)
        next_parent = None
        message_started = False
        message = []

        for line in lines:
            if line.startswith('parent '):
                if not next_parent:
                    next_parent = line.split(' ')[1]
            elif line.startswith('author '):
                print(line)
            elif not line.strip() and not message_started:
                message_started = True
            elif message_started:
                message.append(line)
        
        print("\n".join(message)) 
        print() 

        commit_hash = next_parent

