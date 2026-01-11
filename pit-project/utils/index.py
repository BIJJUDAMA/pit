# What it does: Provides centralized read/write operations for the .pit/index file
# How it does: Manages the index file format (hash mtime size path) consistently across all commands
# What data structure it uses: Dictionary (mapping file paths to tuples of hash, mtime, size)

import os

def read_index(repo_root):
    """
    Reads the index file and returns a dictionary {path: (hash, mtime, size)}.
    Handles both old format (hash path) and new format (hash mtime size path).
    """
    index_path = os.path.join(repo_root, '.pit', 'index')
    index_files = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                parts = line.strip().split(' ')
                if len(parts) >= 4:
                    # New format: hash mtime size path
                    hash_val = parts[0]
                    mtime_ns = int(parts[1])
                    size = int(parts[2])
                    path = " ".join(parts[3:])
                    index_files[path] = (hash_val, mtime_ns, size)
                elif len(parts) >= 2:
                    # Old format: hash path
                    hash_val = parts[0]
                    path = " ".join(parts[1:])
                    index_files[path] = (hash_val, 0, 0)
    return index_files

def read_index_hashes(repo_root):
    full_index = read_index(repo_root)
    return {path: data[0] for path, data in full_index.items()}

def write_index(repo_root, index_dict):
    index_path = os.path.join(repo_root, '.pit', 'index')
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    
    with open(index_path, 'w') as f:
        for path in sorted(index_dict.keys()):
            value = index_dict[path]
            if isinstance(value, tuple) and len(value) >= 3:
                hash_val, mtime, size = value[0], value[1], value[2]
            else:
                hash_val = value if isinstance(value, str) else value[0]
                mtime = 0
                size = 0
            f.write(f"{hash_val} {mtime} {size} {path}\n")

def update_index_entry(repo_root, path, hash_val, mtime=0, size=0):
    index = read_index(repo_root)
    index[path] = (hash_val, mtime, size)
    write_index(repo_root, index)

def remove_index_entry(repo_root, path):
    index = read_index(repo_root)
    if path in index:
        del index[path]
        write_index(repo_root, index)
