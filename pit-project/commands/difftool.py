
# The command: pit difftool [--staged]
# What it does: Runs an external diff tool to visualize changes.
# How it does: It identifies modified files involves comparing the working directory with the index (or HEAD if --staged). It extracts the baseline version of the file to a temporary location and launches a configured external diff tool (defaulting to 'code --wait --diff').
# What data structure it uses: Dictionaries and Sets (reused from diff command logic).

import sys
import os
import subprocess
import tempfile
from utils import repository, objects, config, diff as diff_utils
from commands import diff

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)
        
    # Get Tool Configuration
    cfg = config.read_config()
    tool_command = cfg.get('diff', 'tool', fallback='code --wait --diff $LOCAL $REMOTE')
    
    # Reuse diff logic to find changes
    if args.staged:
        head_commit = repository.get_head_commit(repo_root)
        files1 = objects.get_commit_files(repo_root, head_commit) if head_commit else {}
        index_full = diff._get_index_files(repo_root)
        files2 = {path: data[0] for path, data in index_full.items()}
    else:
        index_full = diff._get_index_files(repo_root)
        files1 = {path: data[0] for path, data in index_full.items()}
        files2 = diff._get_working_dir_files(repo_root, index_full)

    changes = diff_utils.compare_states(files1, files2)
    
    modified_files = changes['modified']
    if not modified_files:
        print("No changes to visualize.")
        return

    print(f"Opening {len(modified_files)} files using '{tool_command}'")
    
    for path in modified_files:
        _launch_diff_tool(repo_root, path, files1, files2, args.staged, tool_command)

def _launch_diff_tool(repo_root, path, files1, files2, is_staged, tool_command):
    # LOCAL (Left side / Before)
    hash_val = files1.get(path)
    local_tmp = None
    if hash_val:
        obj_type, content = objects.read_object(repo_root, hash_val)
        fd, local_tmp = tempfile.mkstemp(suffix=f"_BASE_{os.path.basename(path)}")
        os.write(fd, content)
        os.close(fd)
    else:
        # File didn't exist before, create empty
         fd, local_tmp = tempfile.mkstemp(suffix=f"_BASE_{os.path.basename(path)}")
         os.close(fd)

    # REMOTE (Right side / After)
    remote_path = None
    remote_tmp = None
    
    if is_staged:
        # After is in Index (blob)
        hash_val = files2.get(path)
        if hash_val:
            obj_type, content = objects.read_object(repo_root, hash_val)
            fd, remote_tmp = tempfile.mkstemp(suffix=f"_STAGED_{os.path.basename(path)}")
            os.write(fd, content)
            os.close(fd)
            remote_path = remote_tmp
    else:
        # After is in Working Directory
        remote_path = os.path.join(repo_root, path)

    # Prepare command
    cmd = tool_command
    cmd = cmd.replace('$LOCAL', local_tmp)
    cmd = cmd.replace('$REMOTE', remote_path)
    
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError:
         print(f"Diff tool failed for {path}")
    finally:
        # Cleanup temps
        if local_tmp and os.path.exists(local_tmp):
            os.remove(local_tmp)
        if remote_tmp and os.path.exists(remote_tmp):
            os.remove(remote_tmp)
