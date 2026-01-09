# The command: pit cherry-pick <commit>
# What it does: Applies the changes from a specific commit to the current branch as a new commit
# How it does: 
#   1. Resolves the target commit (handling tags, branches, or hashes).
#   2. Identifies the parent of the target commit.
#   3. Performs a three-way merge between the parent (as ancestor), current HEAD, and the target commit.
#   4. If conflicts occur, it reports them and stops.
#   5. If successful, it automatically creates a new commit with the same message as the target commit.
# What data structure it uses: Directed Acyclic Graph (DAG) for commit/parent relationship, 
# and the three-way merge algorithm (reused from merge.py).

import sys
import os
from utils import repository, objects
from commands import commit
# Import internal three-way merge logic from merge.py
from commands.merge import _perform_three_way_merge, _get_commit_parents

def run(args):
    # Ensure we are in a pit repository
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    try:
        target_ref = args.commit
        
        # 1)Resolve target reference (branch, tag, or hash) to a commit hash
        target_commit_hash = _resolve_ref(repo_root, target_ref)
        if not target_commit_hash:
            print(f"fatal: bad revision '{target_ref}'", file=sys.stderr)
            sys.exit(1)

        #verify it's actually a commit object
        try:
            obj_type, _ = objects.read_object(repo_root, target_commit_hash)
            if obj_type != 'commit':
                print(f"fatal: '{target_ref}' is not a commit", file=sys.stderr)
                sys.exit(1)
        except Exception:
            print(f"fatal: could not read object '{target_commit_hash}'", file=sys.stderr)
            sys.exit(1)

        # 2(Identify the parent of the target commit
        # We use the first parent for the diff calculation (standard cherry-pick behavior)
        parents = _get_commit_parents(repo_root, target_commit_hash)
        if len(parents) > 1:
            # For merge commits, cherry-pick usually needs a -m flag. 
            # We'll follow Git's strictness and bail if it's a merge commit.
            print(f"error: commit {target_commit_hash[:7]} is a merge but no -m option was given.", file=sys.stderr)
            sys.exit(1)
        
        parent_hash = parents[0] if parents else None
        
        #3)dentify current HEAD
        head_hash = repository.get_head_commit(repo_root)
        if not head_hash:
            # Likely an empty repository
            print("fatal: cannot cherry-pick - no commits found in current branch", file=sys.stderr)
            sys.exit(1)

        print(f"Cherry-picking {target_commit_hash[:7]} onto HEAD")

        # 4) Perform Three-Way Merge
        #To cherry-pick, we want the changes from 'parent' to 'target' applied to 'HEAD'.
        #This is represented by a three-way merge where:
        #   base = parent_hash
        #   side1 = head_hash (current branch)
        #   side2 = target_commit_hash (changes to apply)
        merge_successful = _perform_three_way_merge(repo_root, parent_hash, head_hash, target_commit_hash)
        
        if not merge_successful:
            #_perform_three_way_merge already printed conflict info
            print("Automatic cherry-pick failed. Resolve conflicts and commit the result manually.")
            sys.exit(1)

        # 5)Automatically commit the result
        #retrieve the original commit's message
        commit_data = _get_commit_metadata(repo_root, target_commit_hash)
        original_message = commit_data.get('message', f"Cherry-picked commit {target_commit_hash}")
        
        #new commit has current HEAD as parent
        new_commit_hash = commit.create_commit(repo_root, original_message, [head_hash])
        
        print(f"Successfully cherry-picked {target_commit_hash[:7]}")

    except Exception as e:
        print(f"Error during cherry-pick: {e}", file=sys.stderr)
        sys.exit(1)

def _resolve_ref(repo_root, ref):
    """Resolves a reference (branch, tag, or hash) to a 40-char commit hash."""
    # Check if it's HEAD
    if ref.upper() == "HEAD":
        return repository.get_head_commit(repo_root)

    #ccheck if it's a branch name
    branch_hash = repository.get_branch_commit(repo_root, ref)
    if branch_hash:
        return branch_hash

    # Check if it's a tag name (stored in .pit/refs/tags/)
    tag_path = os.path.join(repo_root, '.pit', 'refs', 'tags', ref)
    if os.path.exists(tag_path):
        with open(tag_path, 'r') as f:
            return f.read().strip()

    #check if it looks like a full SHA-1 hash
    if len(ref) == 40 and all(c in '0123456789abcdefABCDEF' for c in ref):
        return ref.lower()

    #check if it's a short hash by searching objects?
    #for now, we return it and let read_object fail if not found.
    #a more robust implementation would scan .pit/objects/
    if 4 <= len(ref) < 40 and all(c in '0123456789abcdefABCDEF' for c in ref):
        # We try to see if any object starts with this
        matches = []
        obj_prefix_dir = ref[:2].lower()
        obj_prefix_file = ref[2:].lower()
        objects_dir = os.path.join(repo_root, '.pit', 'objects')
        
        if os.path.isdir(os.path.join(objects_dir, obj_prefix_dir)):
            for filename in os.listdir(os.path.join(objects_dir, obj_prefix_dir)):
                if filename.startswith(obj_prefix_file):
                    matches.append(obj_prefix_dir + filename)
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"error: short SHA-1 {ref} is ambiguous", file=sys.stderr)
            sys.exit(1)

    return None

def _get_commit_metadata(repo_root, commit_hash):
    """Extracts metadata (like message) from a commit object."""
    obj_type, content = objects.read_object(repo_root, commit_hash)
    if obj_type != 'commit':
        return {}
    
    lines = content.decode().splitlines()
    data = {'message': ''}
    
    msg_started = False
    msg_lines = []
    
    for line in lines:
        if not line.strip() and not msg_started:
            msg_started = True
            continue
        if msg_started:
            msg_lines.append(line)
            
    data['message'] = '\n'.join(msg_lines)
    return data
