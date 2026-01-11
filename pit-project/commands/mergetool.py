
# The command: pit mergetool
# What it does: Runs an external merge tool to resolve merge conflicts.
# How it does: It identifies conflicted files, extracts BASE, LOCAL, and REMOTE versions of the file to temporary locations, and launches a configured external editor. Once the tool exits, it checks if the file was modified and stages it.
# What data structure it uses: Sets (for tracking conflicts).

import sys
import os
import shutil
import subprocess
import tempfile
import platform
from utils import repository, objects, config
from commands import merge, add

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    # 1. Identify Conflicts
    conflicted_files = _find_conflicted_files(repo_root)
    
    if not conflicted_files:
        print("No files need merging.")
        return

    # 2. Get Merge Context (HEAD, REMOTE, BASE)
    head_commit = repository.get_head_commit(repo_root)
    # Extract REMOTE from .pit/MERGE_HEAD
    merge_head_path = os.path.join(repo_root, '.pit', 'MERGE_HEAD')
    if not os.path.exists(merge_head_path):
        print("fatal: MERGE_HEAD not found. Are you currently merging?", file=sys.stderr)
        sys.exit(1)
        
    with open(merge_head_path, 'r') as f:
        remote_commit = f.read().strip()
        
    base_commit = merge._find_common_ancestor(repo_root, head_commit, remote_commit)
    
    # 3. Get Tool Configuration
    cfg = config.read_config()
    tool_command = cfg.get('merge', 'tool', fallback='code --wait --merge $LOCAL $REMOTE $BASE $MERGED')
    
    print(f"Merging {len(conflicted_files)} files using '{tool_command}'")
    
    for file_path in conflicted_files:
        print(f"Merging {file_path}...")
        _process_file(repo_root, file_path, base_commit, head_commit, remote_commit, tool_command)

def _find_conflicted_files(repo_root):
    conflicts = []
    for root, _, files in os.walk(repo_root):
        if '.pit' in root: continue
        for file in files:
            full_path = os.path.join(root, file)
            try:
                with open(full_path, 'rb') as f:
                    content = f.read()
                    if b'<<<<<<< HEAD' in content and b'=======' in content and b'>>>>>>>' in content:
                         conflicts.append(os.path.relpath(full_path, repo_root))
            except:
                pass 
    return conflicts

def _process_file(repo_root, file_path, base_commit, head_commit, remote_commit, tool_command):
    # Extract versions
    base_files = objects.get_commit_files(repo_root, base_commit)
    head_files = objects.get_commit_files(repo_root, head_commit)
    remote_files = objects.get_commit_files(repo_root, remote_commit)
    
    base_hash = base_files.get(file_path)
    head_hash = head_files.get(file_path)
    remote_hash = remote_files.get(file_path)
    
    # Create temp files
    def write_temp(hash_val, suffix):
        if not hash_val:
            return None 
        obj_type, content = objects.read_object(repo_root, hash_val)
        fd, path = tempfile.mkstemp(suffix=f"_{suffix}_{os.path.basename(file_path)}")
        os.write(fd, content)
        os.close(fd)
        return path

    local_tmp = write_temp(head_hash, "LOCAL")
    remote_tmp = write_temp(remote_hash, "REMOTE")
    base_tmp = write_temp(base_hash, "BASE")
    merged_path = os.path.join(repo_root, file_path) # In-place edit
    
    # Prepare command with cross-platform null device
    null_path = "NUL" if platform.system() == "Windows" else "/dev/null"
    cmd = tool_command
    cmd = cmd.replace('$LOCAL', local_tmp or null_path)
    cmd = cmd.replace('$REMOTE', remote_tmp or null_path)
    cmd = cmd.replace('$BASE', base_tmp or null_path)
    cmd = cmd.replace('$MERGED', merged_path)
    
    # Run
    try:
        subprocess.check_call(cmd, shell=True)
        # Check if markers still exist (simple check)
        with open(merged_path, 'rb') as f:
            if b'<<<<<<< HEAD' not in f.read():
                # Conflict resolved?
                # Autostage
                try:
                    subprocess.check_call([sys.executable, sys.argv[0], 'add', file_path])
                    print(f"{file_path} merged and staged.")
                except subprocess.CalledProcessError:
                    print(f"Failed to stage {file_path}")
            else:
                print(f"Warning: {file_path} still contains conflict markers.")
    except subprocess.CalledProcessError:
        print(f"Merge tool failed for {file_path}")
    finally:
        # Cleanup
        for p in [local_tmp, remote_tmp, base_tmp]:
            if p and os.path.exists(p):
                os.remove(p)
