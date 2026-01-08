import sys
import os
from utils import repository, objects
from commands import merge, commit, checkout

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    upstream_branch = args.upstream
    current_branch = repository.get_current_branch(repo_root)
    
    if not current_branch:
        print("fatal: You are not currently on a branch.", file=sys.stderr)
        sys.exit(1)

    if current_branch == upstream_branch:
        print(f"Current branch {current_branch} is up to date.", file=sys.stderr)
        sys.exit(0)

    # Validate upstream
    upstream_commit = repository.get_branch_commit(repo_root, upstream_branch)
    if not upstream_commit:
        # Try if it's a commit hash
        if _is_valid_commit(repo_root, upstream_branch):
            upstream_commit = upstream_branch
        else:
            print(f"fatal: valid upstream '{upstream_branch}' not found", file=sys.stderr)
            sys.exit(1)
            
    head_commit = repository.get_head_commit(repo_root)
    if not head_commit:
        print("fatal: no commits yet", file=sys.stderr)
        sys.exit(1)

    # Find Common Ancestor
    # common_ancestor = merge._find_common_ancestor(repo_root, head_commit, upstream_commit)
    # Actually, for rebase, we want the point where our branch diverged from upstream.
    # Logic: Walk HEAD parents until we find a commit reachable from upstream? 
    # Or just use LCA. 
    # Commits to replay = (LCA..HEAD]
    
    lca = merge._find_common_ancestor(repo_root, head_commit, upstream_commit)
    if not lca:
        print("fatal: no common ancestor found", file=sys.stderr)
        sys.exit(1)

    # Collect commits to replay
    commits_to_replay = []
    curr = head_commit
    while curr != lca and curr:
        commits_to_replay.append(curr)
        # Assuming linear history for the branch being rebased for simplicity
        # If it's a merge commit, we usually take the first parent that leads to LCA
        parents = _get_parents(repo_root, curr)
        if not parents:
            break
        # Heuristic: pick first parent. 
        # Standard rebase flattens history.
        curr = parents[0]
    
    commits_to_replay.reverse()
    
    if not commits_to_replay:
        print(f"Current branch {current_branch} is up to date with {upstream_branch}.", file=sys.stderr)
        sys.exit(0)

    print(f"First, rewinding head to replay your work on top of it...")
    
    # Reset HEAD, Index, Working Dir to upstream
    # 1. Update Working Directory & Index
    upstream_files = objects.get_commit_files(repo_root, upstream_commit)
    current_files = objects.get_commit_files(repo_root, head_commit)
    
    # We must ensure working directory is clean before rebase (simplification)
    if not checkout.is_clean(repo_root):
        print("error: cannot rebase: you have unstaged changes.", file=sys.stderr)
        sys.exit(1)

    # Perform Hard Reset to Upstream
    checkout.update_working_directory(repo_root, current_files, upstream_files)
    checkout.update_index(repo_root, upstream_files)
    
    # Update HEAD ref (keep branch name, update hash)
    _update_ref(repo_root, current_branch, upstream_commit)
    
    # Replay commits
    for i, commit_hash in enumerate(commits_to_replay):
        commit_data = _get_commit_data(repo_root, commit_hash)
        msg_title = commit_data['message'].splitlines()[0]
        print(f"Applying: {msg_title}")
        
        # 3-way Merge
        # Base: Parent of the commit being replayed (original state)
        # Ours: Current HEAD (new base + previous replayed commits)
        # Theirs: The commit being replayed
        
        base_hash = commit_data['parent']
        # If commit had multiple parents (merge), rebase typically skips or flattens.
        # We use the first parent as 'base' context.
        
        current_head = repository.get_head_commit(repo_root)
        
        # We reuse merge logic. 
        # _perform_three_way_merge(repo_root, ancestor, head, merge)
        # ancestor = base_hash
        # head = current_head
        # merge = commit_hash
        
        success = merge._perform_three_way_merge(repo_root, base_hash, current_head, commit_hash)
        
        if not success:
            print(f"error: could not apply {commit_hash[:7]} {msg_title}")
            print("Resolve conflicts manually and run 'pit commit', but continuing rebase is not implemented.")
            sys.exit(1)
            
        # Create new commit
        # Re-read message to capture full message
        parents = [current_head]
        new_commit_params = commit.create_commit(repo_root, commit_data['message'], parents)
        
        # update_ref is handled by commit.create_commit usually?
        # commit.create_commit updates HEAD. Since HEAD points to branch ref, branch ref is updated.
        
def _update_ref(repo_root, branch_name, commit_hash):
    branch_path = os.path.join(repo_root, '.pit', 'refs', 'heads', branch_name)
    with open(branch_path, 'w') as f:
        f.write(f"{commit_hash}\n")

def _is_valid_commit(repo_root, commit_hash):
    try:
        obj_type, _ = objects.read_object(repo_root, commit_hash)
        return obj_type == 'commit'
    except:
        return False

def _get_parents(repo_root, commit_hash):
    obj_type, content = objects.read_object(repo_root, commit_hash)
    lines = content.decode().splitlines()
    parents = []
    for line in lines:
        if line.startswith('parent '):
            parents.append(line.split(' ')[1])
    return parents

def _get_commit_data(repo_root, commit_hash):
    # Simplified version, similar to revert.py
    obj_type, content = objects.read_object(repo_root, commit_hash)
    lines = content.decode().splitlines()
    data = {'hash': commit_hash, 'message': '', 'parent': None}
    msg_started = False
    msg_lines = []
    for line in lines:
        if line.startswith('parent '):
            if not data['parent']:
                data['parent'] = line.split(' ')[1]
        elif not line.strip() and not msg_started:
            msg_started = True
        elif msg_started:
            msg_lines.append(line)
    data['message'] = '\n'.join(msg_lines)
    return data
