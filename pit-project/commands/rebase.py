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

    # Load state
    next_commit = _read_next_commit(repo_root)
    if not next_commit:
        print("No commits left to apply? finishing...", file=sys.stderr)
        _finish_rebase(repo_root)
        return

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
        # If it's a merge commit or complex history, parent selection is tricky.
        # But for rebase, we simplify: we are rebasing onto new base.
        # The 'base' needed for 3-way merge is the commit's ORIGINAL parent.
        
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
    # 1. Reachable from HEAD (Set A)
    head_reachable = _get_reachable_commits(repo_root, head)
    # 2. Reachable from Upstream (Set B)
    upstream_reachable = _get_reachable_commits(repo_root, upstream)
    
    # 3. Difference (A - B) -> Commits unique to feature branch
    to_replay_set = head_reachable - upstream_reachable
    
    if not to_replay_set:
        return []
        
    # 4. Topological Sort (Kahn's Algorithm)
    # We want to order them such that parents come before children.
    # In topological sort terms, if A is parent of B, A -> B dependency.
    
    # Filter out merge commits (linearize history)
    linear_set = set()
    for c in to_replay_set:
        if len(_get_parents(repo_root, c)) <= 1:
            linear_set.add(c)
            
    return _topological_sort(repo_root, linear_set)

def _get_reachable_commits(repo_root, start_commit):
    from collections import deque
    if not start_commit:
        return set()
        
    reachable = set()
    queue = deque([start_commit])
    
    while queue:
        curr = queue.popleft() # O(1)
        if curr in reachable:
            continue
        reachable.add(curr)
        
        parents = _get_parents(repo_root, curr)
        for p in parents:
            if p not in reachable:
                queue.append(p)
                
    return reachable

def _topological_sort(repo_root, commit_set):
    # Build adjacency list: parent -> [children] (within set)
    adj = {c: [] for c in commit_set}
    in_degree = {c: 0 for c in commit_set}
    
    # Populate graph
    from collections import deque
    
    for commit in commit_set:
        parents = _get_parents(repo_root, commit)
        for p in parents:
            if p in commit_set:
                adj[p].append(commit) # p is parent of commit
                in_degree[commit] += 1
                
    # Queue for Kahn's (commits with 0 in-degree: no parents in set -> oldest)
    queue = deque([c for c in commit_set if in_degree[c] == 0])
    sorted_result = []
    
    while queue:
        node = queue.popleft()
        sorted_result.append(node)
        
        for child in adj[node]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)
                
    # If len(sorted_result) != len(commit_set), we have a cycle or issue
    # For Git DAG, cycles shouldn't exist.
    return sorted_result


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
    except Exception:
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
