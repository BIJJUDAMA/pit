import sys
import os
import shutil
from utils import repository, objects, config
from commands import merge, commit, checkout

REBASE_DIR = 'rebase-apply'

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    # Handle --abort
    if args.abort:
        _handle_abort(repo_root)
        return

    # Handle --continue
    if args.cont:
        _handle_continue(repo_root)
        return

    if not args.upstream:
        print("fatal: upstream branch required", file=sys.stderr)
        sys.exit(1)

    # Start new rebase
    _start_rebase(repo_root, args.upstream)


def _start_rebase(repo_root, upstream_name):
    # 1. Validation
    if not checkout.is_clean(repo_root):
        print("error: cannot rebase: you have unstaged changes.", file=sys.stderr)
        sys.exit(1)

    current_branch = repository.get_current_branch(repo_root)
    if not current_branch:
        print("fatal: You are not currently on a branch.", file=sys.stderr)
        sys.exit(1)

    upstream_commit = repository.get_branch_commit(repo_root, upstream_name)
    if not upstream_commit:
        if _is_valid_commit(repo_root, upstream_name):
            upstream_commit = upstream_name
        else:
            print(f"fatal: valid upstream '{upstream_name}' not found", file=sys.stderr)
            sys.exit(1)
            
    head_commit = repository.get_head_commit(repo_root)
    if not head_commit:
        print("fatal: no commits yet", file=sys.stderr)
        sys.exit(1)

    if current_branch == upstream_name:
        print(f"Current branch {current_branch} is up to date.", file=sys.stderr)
        sys.exit(0)

    # 2. Collect Commits (Set Difference)
    commits_to_replay = _collect_commits_to_replay(repo_root, head_commit, upstream_commit)
    
    if not commits_to_replay:
        print(f"Current branch {current_branch} is up to date with {upstream_name}.", file=sys.stderr)
        # Fast-forward check could be here, but for now we just say up to date or do nothing if already contained
        sys.exit(0)

    print(f"First, rewinding head to replay your work on top of it...")
    
    # 3. Detach HEAD to Upstream
    # Save state first in case we crash
    _save_rebase_state(repo_root, current_branch, commits_to_replay)

    # Hard reset logic (update files + index)
    upstream_files = objects.get_commit_files(repo_root, upstream_commit)
    current_files = objects.get_commit_files(repo_root, head_commit)
    
    checkout.update_working_directory(repo_root, current_files, upstream_files)
    checkout.update_index(repo_root, upstream_files)
    
    # Detach HEAD: Write the hash directly to .pit/HEAD
    _write_detached_head(repo_root, upstream_commit)
    
    # 4. Start Replay Loop
    _replay_loop(repo_root)


def _handle_continue(repo_root):
    rebase_dir = os.path.join(repo_root, '.pit', REBASE_DIR)
    if not os.path.exists(rebase_dir):
        print("fatal: No rebase in progress?", file=sys.stderr)
        sys.exit(1)

    # Verify conflict is resolved (simplified: check if index clean-ish or MERGE_HEAD gone?)
    # Usually we check if user staged the changes.
    # Assuming user ran 'pit add'.
    
    # We need to commit the current changes (the resolved conflict)
    # But wait, 'pit commit' creates a commit. If user ran 'pit commit', they created a commit.
    # If they just ran 'pit add', we need to create the commit for them using the original message.
    
    # Load state to get the commit message we were trying to play
    next_commit = _read_next_commit(repo_root)
    if not next_commit:
        print("No commits left to apply? finishing...", file=sys.stderr)
        _finish_rebase(repo_root)
        return

    # Check if we need to synthesize a commit
    # If HEAD has moved since we stopped, maybe user committed?
    # Simple logic: We assume user `added` files and we need to `commit` now.
    
    commit_data = _get_commit_data(repo_root, next_commit)
    
    # Create the commit for the resolved conflict
    try:
        current_head = repository.get_head_commit(repo_root)
        parents = [current_head] if current_head else []
        new_commit_params = commit.create_commit(repo_root, commit_data['message'], parents)
    except Exception as e:
        print(f"Error creating commit (did you 'pit add' your changes?): {e}", file=sys.stderr)
        sys.exit(1)
        
    # Advance state
    _pop_commit_from_state(repo_root)
    
    # Resume loop
    _replay_loop(repo_root)


def _handle_abort(repo_root):
    rebase_dir = os.path.join(repo_root, '.pit', REBASE_DIR)
    if not os.path.exists(rebase_dir):
        print("fatal: No rebase in progress?", file=sys.stderr)
        sys.exit(1)
        
    # Read original head
    orig_head_path = os.path.join(rebase_dir, 'orig-head')
    orig_branch_path = os.path.join(rebase_dir, 'head-name')
    
    if os.path.exists(orig_head_path):
        with open(orig_head_path, 'r') as f:
            orig_hash = f.read().strip()
        
        # Hard reset to orig_hash
        current_head = repository.get_head_commit(repo_root)
        current_files = objects.get_commit_files(repo_root, current_head) if current_head else {}
        target_files = objects.get_commit_files(repo_root, orig_hash)
        
        checkout.update_working_directory(repo_root, current_files, target_files)
        checkout.update_index(repo_root, target_files)
        
        # Restore HEAD ref
        if os.path.exists(orig_branch_path):
            with open(orig_branch_path, 'r') as f:
                branch_name = f.read().strip()
            
            # Point HEAD back to branch
            head_path = os.path.join(repo_root, '.pit', 'HEAD')
            with open(head_path, 'w') as f:
                f.write(f"ref: refs/heads/{branch_name}\n")
        else:
            # Detached
            _write_detached_head(repo_root, orig_hash)
            
    print("Rebase aborted.")
    shutil.rmtree(rebase_dir)


def _replay_loop(repo_root):
    commits = _load_remaining_commits(repo_root)
    
    while commits:
        commit_hash = commits[0]
        commit_data = _get_commit_data(repo_root, commit_hash)
        msg_title = commit_data['message'].splitlines()[0]
        print(f"Applying: {msg_title}")
        
        base_hash = commit_data['parent']
        current_head = repository.get_head_commit(repo_root)
        
        # Perform 3-way merge
        success = merge._perform_three_way_merge(repo_root, base_hash, current_head, commit_hash)
        
        if not success:
            print(f"Conflict while applying {commit_hash[:7]}.")
            print("Resolve conflicts, then run 'pit add <files>' and 'pit rebase --continue'.")
            print("To stop, run 'pit rebase --abort'.")
            sys.exit(1) # Exit to let user fix
            
        # Commit success
        parents = [current_head] if current_head else []
        commit.create_commit(repo_root, commit_data['message'], parents)
        
        # Remove from state
        _pop_commit_from_state(repo_root)
        commits = _load_remaining_commits(repo_root)
        
    _finish_rebase(repo_root)


def _finish_rebase(repo_root):
    # Move original branch ref to current HEAD
    rebase_dir = os.path.join(repo_root, '.pit', REBASE_DIR)
    branch_name_path = os.path.join(rebase_dir, 'head-name')
    
    if os.path.exists(branch_name_path):
        with open(branch_name_path, 'r') as f:
            branch_name = f.read().strip()
            
        current_head = repository.get_head_commit(repo_root)
        
        # Update branch ref
        branch_ref_path = os.path.join(repo_root, '.pit', 'refs', 'heads', branch_name)
        with open(branch_ref_path, 'w') as f:
            f.write(f"{current_head}\n")
            
        # Re-attach HEAD
        head_path = os.path.join(repo_root, '.pit', 'HEAD')
        with open(head_path, 'w') as f:
            f.write(f"ref: refs/heads/{branch_name}\n")
            
        print(f"Successfully rebased {branch_name} to {current_head[:7]}.")
    
    if os.path.exists(rebase_dir):
        shutil.rmtree(rebase_dir)


def _collect_commits_to_replay(repo_root, head, upstream):
    # Reachable from HEAD
    head_reachable = _get_reachable_commits(repo_root, head)
    # Reachable from Upstream
    upstream_reachable = _get_reachable_commits(repo_root, upstream)
    
    # Difference (A - B)
    to_replay = head_reachable - upstream_reachable
    
    # Sort by commit time or topology?
    # Simple topology sort: List parents before children.
    # Since we have the hashes, we can reconstruct the order.
    # Or just walk back from HEAD and filter.
    
    ordered_commits = []
    curr = head
    while curr:
        if curr in to_replay:
            ordered_commits.append(curr)
        
        parents = _get_parents(repo_root, curr)
        if not parents:
            break
        curr = parents[0] # Simplification for linear sort of verify
        
        # Better: Since to_replay is a set, we want the subset of history.
        # But 'commits_to_replay' needs correct order.
        # If we just reverse the list of (HEAD..LCA), it works for linear.
        # For non-linear, rebase linearizes it anyway.
    
    ordered_commits.reverse()
    return ordered_commits


def _get_reachable_commits(repo_root, start_commit):
    reachable = set()
    queue = [start_commit]
    while queue:
        curr = queue.pop(0)
        if curr in reachable:
            continue
        reachable.add(curr)
        parents = _get_parents(repo_root, curr)
        queue.extend(parents)
    return reachable


def _save_rebase_state(repo_root, branch_name, commits):
    rebase_dir = os.path.join(repo_root, '.pit', REBASE_DIR)
    os.makedirs(rebase_dir, exist_ok=True)
    
    with open(os.path.join(rebase_dir, 'head-name'), 'w') as f:
        f.write(branch_name)
        
    head_commit = repository.get_head_commit(repo_root)
    with open(os.path.join(rebase_dir, 'orig-head'), 'w') as f:
        f.write(head_commit)
        
    with open(os.path.join(rebase_dir, 'commits'), 'w') as f:
        for c in commits:
            f.write(f"{c}\n")

def _load_remaining_commits(repo_root):
    path = os.path.join(repo_root, '.pit', REBASE_DIR, 'commits')
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return [l.strip() for l in f.readlines() if l.strip()]

def _pop_commit_from_state(repo_root):
    commits = _load_remaining_commits(repo_root)
    if commits:
        commits.pop(0)
        path = os.path.join(repo_root, '.pit', REBASE_DIR, 'commits')
        with open(path, 'w') as f:
            for c in commits:
                f.write(f"{c}\n")

def _read_next_commit(repo_root):
    commits = _load_remaining_commits(repo_root)
    return commits[0] if commits else None

def _write_detached_head(repo_root, commit_hash):
    head_path = os.path.join(repo_root, '.pit', 'HEAD')
    with open(head_path, 'w') as f:
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
