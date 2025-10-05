# The command: pit diff [--staged]
# What it does: Shows line-by-line changes between repository states (working directory vs. index, or index vs. HEAD)
# How it does: It gathers two dictionaries of {path: hash} for the "before" and "after" states. It identifies modified files by comparing hashes, fetches the two versions of the content, and passes them to a helper function that generates the standard diff text
# What data structure it uses: Hash Table / Dictionary (to represent the file states for quick lookups), Sets (for efficient comparison of file lists to find additions/deletions), List / Array (of file lines passed to the diffing algorithm)

import os
import sys
from utils import repository, objects, diff as diff_utils

def run(args):
# Shows differences between working directory and index (if --staged is not used)
# Shows differences between index and HEAD (if --staged is used)

    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    if args.staged:
        # Diff between HEAD commit and index
        head_commit = repository.get_head_commit(repo_root)
        files1 = objects.get_commit_files(repo_root, head_commit) if head_commit else {}
        files2 = _get_index_files(repo_root)
        from_prefix, to_prefix = "a/", "b/"
    else:
        # Diff between index and working directory
        files1 = _get_index_files(repo_root)
        files2 = _get_working_dir_files(repo_root)
        from_prefix, to_prefix = "a/", "b/"

    changes = diff_utils.compare_states(files1, files2)

    # Print diff for modified files
    for path in changes['modified']:
        content1 = objects.read_object(repo_root, files1[path])[1] if path in files1 else b''
        
        # For working directory diff, read the actual file
        if not args.staged and path in files2:
            content2 = open(os.path.join(repo_root, path), 'rb').read()
        # For staged diff, the "after" state is in the index
        elif args.staged and path in files2:
            content2 = objects.read_object(repo_root, files2[path])[1]
        else:
            content2 = b''

        diff_lines = diff_utils.get_diff_lines(content1, content2, from_prefix + path, to_prefix + path)
        sys.stdout.writelines(diff_lines)

def _get_index_files(repo_root):
    index_path = os.path.join(repo_root, '.pit', 'index')
    index_files = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                hash_val, path = line.strip().split(' ', 1)
                index_files[path] = hash_val
    return index_files

def _get_working_dir_files(repo_root):
    from utils import ignore  # Local import to avoid cycles
    working_files = {}
    ignore_patterns = ignore.get_ignored_patterns(repo_root)
    for root, dirs, files in os.walk(repo_root):
        if '.pit' in dirs:
            dirs.remove('.pit')
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_root)
            if not ignore.is_ignored(rel_path, ignore_patterns):
                with open(file_path, 'rb') as f:
                    content = f.read()
                working_files[rel_path] = objects.hash_object(repo_root, content, 'blob', write=False)
    return working_files

