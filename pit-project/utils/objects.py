# What it does: Manages the low-level object database, handling the storage and retrieval of all blobs, trees, and commits
# How it does: It implements a content-addressed storage system. `hash_object` saves content and returns its hash. `read_object` retrieves content using its hash. It also contains the logic to build and read the hierarchical tree structure
# What data structure it uses: Hash Table / Dictionary (the entire object store is a content-addressed dictionary where the SHA-1 hash is the key).
# It now explicitly builds and reads a Merkle Tree to represent the project's file structure, using recursion to do so


import os
import hashlib
import zlib
import sys

def hash_object(repo_root, content, obj_type, write=True): #Hashes content and optionally writes it as an object of the given type ('blob', 'tree', 'commit')
    header = f'{obj_type} {len(content)}\0'.encode()
    data = header + content
    
    sha1 = hashlib.sha1(data).hexdigest()
    
    if write:
        object_dir = os.path.join(repo_root, '.pit', 'objects', sha1[:2])
        os.makedirs(object_dir, exist_ok=True)
        object_path = os.path.join(object_dir, sha1[2:])
        
        with open(object_path, 'wb') as f:
            f.write(zlib.compress(data))
            
    return sha1

def read_object(repo_root, sha1): #Reads an object by its SHA-1 hash and returns its type and content
    
    object_path = os.path.join(repo_root, '.pit', 'objects', sha1[:2], sha1[2:])
    
    if not os.path.exists(object_path):
        raise FileNotFoundError(f"Object not found: {sha1}")
        
    with open(object_path, 'rb') as f:
        compressed_data = f.read()
        
    data = zlib.decompress(compressed_data)
    
    null_byte_index = data.find(b'\0')
    header = data[:null_byte_index].decode()
    content = data[null_byte_index + 1:]
    
    obj_type, _ = header.split(' ')
    
    return obj_type, content

def build_tree_from_index(repo_root): # Builds a nested dictionary representing the tree structure from the index file
    index_path = os.path.join(repo_root, '.pit', 'index')
    tree = {}
    if os.path.exists(index_path):
        with open(index_path, 'r') as f:
            for line in f:
                parts = line.strip().split(' ')
                if len(parts) >= 4:
                     # New format: hash mtime size path
                    hash_val = parts[0]
                    path = " ".join(parts[3:])
                else:
                    # Old format: hash path
                    hash_val, path = line.strip().split(' ', 1)
                
                parts = path.split(os.sep)
                current_level = tree
                for part in parts[:-1]:
                    current_level = current_level.setdefault(part, {})
                current_level[parts[-1]] = hash_val
    return tree

def write_tree(repo_root, tree_dict): #Recursively writes a tree object from a nested dictionary and returns its hash

    entries = []
    for name, value in sorted(tree_dict.items()):
        if isinstance(value, dict):
            # It's a subdirectory, recurse
            subtree_hash = write_tree(repo_root, value)
            mode = '040000'  # Directory mode
            entry_type = 'tree'
            sha1 = subtree_hash
        else:
            # It's a file blob
            mode = '100644'  # Regular file mode
            entry_type = 'blob'
            sha1 = value
        
        # Format is: <mode> <type> <hash>\t<name>
        entries.append(f"{mode} {entry_type} {sha1}\t{name}".encode())

    tree_content = b'\n'.join(entries)
    return hash_object(repo_root, tree_content, 'tree')

def get_commit_tree_hash(repo_root, commit_hash): # Retrieves the tree hash from a commit object
    if not commit_hash:
        return None
    obj_type, content = read_object(repo_root, commit_hash)
    if obj_type != 'commit':
        raise TypeError(f"Object {commit_hash} is not a commit")
    lines = content.decode().splitlines()
    for line in lines:
        if line.startswith('tree '):
            return line.split(' ')[1]
    return None

def get_commit_files(repo_root, commit_hash): #Retrieves all files and their hashes from a commit by reading its tree recursively

    if not commit_hash:
        return {}
        
    tree_hash = get_commit_tree_hash(repo_root, commit_hash)
    if not tree_hash:
        return {}
    
    files = {}
    
    def read_tree_recursive(tree_sha, path_prefix=""):
        obj_type, content = read_object(repo_root, tree_sha)
        if obj_type != 'tree':
            raise TypeError(f"Object {tree_sha} is not a tree")
        
        for line in content.decode().splitlines():
            # Line format: <mode> <type> <hash>\t<name>
            _, entry_type, sha1, name = line.replace('\t', ' ').split(' ', 3)
            current_path = os.path.join(path_prefix, name)
            
            if entry_type == 'blob':
                files[current_path] = sha1
            elif entry_type == 'tree':
                read_tree_recursive(sha1, current_path)

    read_tree_recursive(tree_hash)
    return files