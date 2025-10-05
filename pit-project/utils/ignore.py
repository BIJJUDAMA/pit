# What it does: Implements the `.pitignore` functionality
# What data structure it uses: Set (to store the ignore patterns for efficient, near O(1) average time complexity lookups)

import os
from fnmatch import fnmatch

def get_ignored_patterns(repo_root):
    """
    Reads the .pitignore file and returns a set of glob patterns.
    """
    ignore_file = os.path.join(repo_root, '.pitignore')
    patterns = {'.pit', '.pit/*', '*.pyc', '__pycache__'} # Always ignore these
    
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.add(line)
    return patterns

def is_ignored(path, ignore_patterns): # Returns True if the path matches any ignore pattern
    for pattern in ignore_patterns:
        if fnmatch(path, pattern) or any(fnmatch(part, pattern) for part in path.split(os.sep)):
            return True
    return False
