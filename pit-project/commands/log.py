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

    # Use a set to track visited commits and avoid duplicates
    visited = set()
    # Use a stack for proper DAG traversal (instead of simple linear traversal)
    stack = [commit_hash]
    
    while stack:
        current_hash = stack.pop()
        
        # Skip if we've already visited this commit
        if current_hash in visited:
            continue
        visited.add(current_hash)
        
        try:
            obj_type, content = objects.read_object(repo_root, current_hash)
        except FileNotFoundError:
            print(f"fatal: could not read commit object {current_hash}", file=sys.stderr)
            continue

        if obj_type != 'commit':
            print(f"fatal: object {current_hash} is not a commit", file=sys.stderr)
            continue

        lines = content.decode().splitlines()
        
        print(f"commit {current_hash}")

        # Find ALL parents (not just the first one)
        parents = []
        message_started = False
        message = []

        for line in lines:
            if line.startswith('parent '):
                parent_hash = line.split(' ')[1]
                parents.append(parent_hash)
            elif line.startswith('author '):
                print(f"Author: {line[7:]}")
            elif line.startswith('committer '):
                print(f"Committer: {line[10:]}")
            elif not line.strip() and not message_started:
                message_started = True
            elif message_started:
                message.append(line)
        
        # Add parents to stack in reverse order for proper traversal
        # This ensures we visit the main branch first, then feature branches
        for parent in reversed(parents):
            if parent not in visited:
                stack.append(parent)
        
        print() 
        print("\n".join(message)) 
        print()  

