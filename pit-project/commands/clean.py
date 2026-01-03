import os
import sys
import shutil
from utils import repository, ignore

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    index_path = os.path.join(repo_root, '.pit', 'index')
    index_files = set()
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                parts = line.strip().split(' ', 1)
                if len(parts) == 2:
                    index_files.add(parts[1])

    ignore_patterns = ignore.get_ignored_patterns(repo_root)
    
    tracked_dirs = set()
    for f in index_files:
        path_parts = f.split(os.sep)
        for i in range(1, len(path_parts)):
            tracked_dirs.add(os.sep.join(path_parts[:i]))

    untracked_files = []
    untracked_dirs = []

    for root, dirs, files in os.walk(repo_root):
        if '.pit' in dirs:
            dirs.remove('.pit')
        
        rel_root = os.path.relpath(root, repo_root)
        if rel_root == '.':
            rel_root = ""

        for d in list(dirs):
            d_rel_path = os.path.join(rel_root, d).lstrip(os.sep)
            
            if ignore.is_ignored(d_rel_path, ignore_patterns):
                dirs.remove(d)
                continue
            
            if getattr(args, 'd', False):
                if d_rel_path not in tracked_dirs:
                    untracked_dirs.append(d_rel_path)
                    dirs.remove(d)

        for f in files:
            f_rel_path = os.path.join(rel_root, f).lstrip(os.sep)
            if f_rel_path not in index_files and not ignore.is_ignored(f_rel_path, ignore_patterns):
                untracked_files.append(f_rel_path)

    items_to_clean = sorted(untracked_files + untracked_dirs)

    if not items_to_clean:
        return

    force = getattr(args, 'f', False)
    dry_run = getattr(args, 'n', False)

    if not force and not dry_run:
        print("Would remove:")
        for item in items_to_clean:
            if item in untracked_dirs:
                print(f"  {item}/")
            else:
                print(f"  {item}")
        print("\nUse 'pit clean -f' to delete them.")
        return

    if dry_run:
        for item in items_to_clean:
            if item in untracked_dirs:
                print(f"Would remove {item}/")
            else:
                print(f"Would remove {item}")
        return

    for item in items_to_clean:
        item_path = os.path.join(repo_root, item)
        if os.path.isdir(item_path):
            print(f"Removing {item}/")
            shutil.rmtree(item_path)
        elif os.path.exists(item_path):
            print(f"Removing {item}")
            os.remove(item_path)
