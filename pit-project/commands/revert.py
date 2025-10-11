# The command: pit revert <commit-hash>
# What it does: Creates a new commit that undoes the changes introduced by a specific commit
# How it does: It reads the target commit, finds its parent, computes the difference between them and applies the reverse changes to the current working directory and staging area
# What data structure it uses: DAG (for commit traversal), Hash Table (for index operations),and performs Three-Way Merge for conflict resolution

import sys
import os
from utils import repository, objects, diff as diff_utils
from commands import commit, add

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    try:
        commit_hash = args.commit_hash
        if not _is_valid_commit(repo_root, commit_hash):
            print(f"fatal: {commit_hash} is not a valid commit", file=sys.stderr)
            sys.exit(1)

        # Get the commit to revert and its parent
        commit_to_revert = _get_commit_data(repo_root, commit_hash)
        if not commit_to_revert.get('parent'):
            print(f"fatal: cannot revert initial commit", file=sys.stderr)
            sys.exit(1)

        parent_commit = _get_commit_data(repo_root, commit_to_revert['parent'])
        
        # Get current HEAD commit
        current_head = repository.get_head_commit(repo_root)
        current_commit = _get_commit_data(repo_root, current_head) if current_head else None

        # Compute changes introduced by the commit to revert
        changes = _get_commit_changes(repo_root, parent_commit, commit_to_revert)
        
        # Apply reverse changes
        _apply_reverse_changes(repo_root, changes)
        
        # Create revert commit
        message = f"Revert \"{commit_to_revert['message'].splitlines()[0]}\"\n\nThis reverts commit {commit_hash}."
        parents = [current_head] if current_head else []
        
        new_commit_hash = commit.create_commit(repo_root, message, parents)
        print(f"[{repository.get_current_branch(repo_root) or 'HEAD'} {new_commit_hash[:7]}] {message.splitlines()[0]}")
        
    except Exception as e:
        print(f"Error during revert: {e}", file=sys.stderr)
        sys.exit(1)
#Check if the given hash corresponds to a valid commit
def _is_valid_commit(repo_root, commit_hash):
    try:
        obj_type, _ = objects.read_object(repo_root, commit_hash)
        return obj_type == 'commit'
    except FileNotFoundError:
        return False
    
#Extract structured data from a commit object
def _get_commit_data(repo_root, commit_hash):
    obj_type, content = objects.read_object(repo_root, commit_hash)
    if obj_type != 'commit':
        raise ValueError(f"Object {commit_hash} is not a commit")
    
    lines = content.decode().splitlines()
    commit_data = {
        'hash': commit_hash,
        'tree': None,
        'parent': None,
        'message': ''
    }
    
    message_started = False
    message_lines = []
    
    for line in lines:
        if line.startswith('tree '):
            commit_data['tree'] = line.split(' ')[1]
        elif line.startswith('parent '):
            commit_data['parent'] = line.split(' ')[1]
        elif not line.strip() and not message_started:
            message_started = True
        elif message_started:
            message_lines.append(line)
    
    commit_data['message'] = '\n'.join(message_lines)
    return commit_data

def _get_commit_changes(repo_root, parent_commit, target_commit):
    parent_files = objects.get_commit_files(repo_root, parent_commit['hash']) if parent_commit else {}
    target_files = objects.get_commit_files(repo_root, target_commit['hash'])
    
    changes = diff_utils.compare_states(parent_files, target_files)
    return {
        'added': changes['added'],
        'deleted': changes['deleted'], 
        'modified': changes['modified'],
        'parent_files': parent_files,
        'target_files': target_files
    }
    
#Apply the reverse of the changes to working directory and staging area
def _apply_reverse_changes(repo_root, changes):
    # Read current index
    index_path = os.path.join(repo_root, '.pit', 'index')
    index_files = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                index_files[path] = hash_val

    # For files that were added in the original commit-delete them
    for path in changes['added']:
        file_path = os.path.join(repo_root, path)
        if os.path.exists(file_path):
            os.remove(file_path)
        if path in index_files:
            del index_files[path]

    # For files that were deleted in the original commit-restore them
    for path in changes['deleted']:
        if path in changes['parent_files']:
            # Restore the file content from parent commit
            blob_hash = changes['parent_files'][path]
            obj_type, content = objects.read_object(repo_root, blob_hash)
            if obj_type == 'blob':
                # Create directory if it doesn't exist
                dir_path = os.path.dirname(os.path.join(repo_root, path))
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                
                # Write file content
                with open(os.path.join(repo_root, path), 'wb') as f:
                    f.write(content)
                
                # Add to index
                index_files[path] = blob_hash

    # For files that were modified in the original commit, restore parent version
    for path in changes['modified']:
        if path in changes['parent_files']:
            blob_hash = changes['parent_files'][path]
            obj_type, content = objects.read_object(repo_root, blob_hash)
            if obj_type == 'blob':
                with open(os.path.join(repo_root, path), 'wb') as f:
                    f.write(content)
                index_files[path] = blob_hash

    # Write updated index
    with open(index_path, 'w') as f:
        for path, hash_val in sorted(index_files.items()):
            f.write(f"{hash_val} {path}\n")