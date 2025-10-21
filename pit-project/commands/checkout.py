# The command: pit checkout <branch-name> | <file>...
# What it does: Switches branches OR restores files in the working directory from the index.
# How it does:
#   - If <branch-name>: Validates branch exists, overwrites `.pit/HEAD` with a symbolic ref.
#   - If <file>...: Reads the index, finds the blob hash for each file, reads the blob, overwrites the working directory file.
# What data structure it uses: List (branch validation), Dictionary (reading index), Hash Table (object store lookup).

import sys
import os
from utils import repository, objects # Import objects utility

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    targets = args.targets 
    
    # Check if the target is a single, existing branch name 
    if len(targets) == 1:
        target_name = targets[0]
        branches = repository.get_all_branches(repo_root)
        if target_name in branches:
            # It's a branch checkout 
            try:
                head_path = os.path.join(repo_root, '.pit', 'HEAD')
                ref_path = f"ref: refs/heads/{target_name}"
                # Check if already on the branch
                current_branch = repository.get_current_branch(repo_root)
                if current_branch == target_name:
                    print(f"Already on '{target_name}'")
                    return

                with open(head_path, 'w') as f:
                    f.write(f"{ref_path}\n")
                print(f"Switched to branch '{target_name}'")
                # TODO: Optionally update the working directory/index based on the new branch HEAD?
                # The original code only updated HEAD pointer.
            except Exception as e:
                print(f"Error switching branch: {e}", file=sys.stderr)
                sys.exit(1)
            return # Branch checkout successful

    # If not a single branch, assume it's one or more file paths 
    print("Restoring file(s) from index...")
    index_path = os.path.join(repo_root, '.pit', 'index')
    index_files = {} # {path: hash}
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r') as f:
                for line in f:
                    hash_val, path = line.strip().split(' ', 1)
                    index_files[path] = hash_val
        except Exception as e:
             print(f"Error reading index file: {e}", file=sys.stderr)
             sys.exit(1)

    files_restored = 0
    files_not_in_index = 0
    errors_occurred = 0

    for file_target in targets:
        # Normalize the path relative to repo_root
        # Assuming user provides paths relative to current dir or repo root
        abs_target_path = os.path.abspath(file_target)
        rel_path = os.path.relpath(abs_target_path, repo_root)

        if rel_path in index_files:
            blob_hash = index_files[rel_path]
            try:
                obj_type, content = objects.read_object(repo_root, blob_hash)
                if obj_type == 'blob':
                    # Ensure directory exists before writing
                    full_path = os.path.join(repo_root, rel_path)
                    dir_name = os.path.dirname(full_path)
                    if dir_name and not os.path.exists(dir_name):
                        os.makedirs(dir_name, exist_ok=True)

                    # Overwrite the file in the working directory
                    with open(full_path, 'wb') as f_work:
                        f_work.write(content)
                    print(f"Restored '{rel_path}'")
                    files_restored += 1
                else:
                    print(f"Error: Object for '{rel_path}' ({blob_hash[:7]}) is not a blob (type: {obj_type}).", file=sys.stderr)
                    errors_occurred += 1
            except FileNotFoundError:
                 print(f"Error: Blob object {blob_hash} for file '{rel_path}' not found in object store.", file=sys.stderr)
                 errors_occurred += 1
            except Exception as e:
                print(f"Error restoring file '{rel_path}': {e}", file=sys.stderr)
                errors_occurred += 1
        else:
            # Check if it's a branch name to give a clearer error
            branches = repository.get_all_branches(repo_root) # Re-check branches just in case
            if file_target in branches:
                 print(f"Error: Cannot checkout branch '{file_target}' and files simultaneously.", file=sys.stderr)
            else:
                 print(f"error: pathspec '{file_target}' did not match any file(s) known to pit index.", file=sys.stderr)
            files_not_in_index += 1

    if files_not_in_index > 0 or errors_occurred > 0:
        sys.exit(1) # Exit with error if any file failed
    elif files_restored == 0:
        print("No files were restored (maybe already up-to-date?).")