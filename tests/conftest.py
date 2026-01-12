# Shared pytest fixtures for Pit VCS tests

import pytest
import os
import sys
import shutil
import tempfile

# Add pit-project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pit-project'))

from commands import init, add, commit, status, branch, checkout, merge, log, stash, reset, revert, clean, rebase
from utils import repository, objects, config, index as index_utils, ignore


@pytest.fixture
def temp_dir():
    # Creates a temporary directory that is cleaned up after the test
    # Also saves/restores cwd to prevent issues when tests change directories
    original_dir = os.getcwd()
    tmp = tempfile.mkdtemp()
    yield tmp
    os.chdir(original_dir)  
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def temp_repo(temp_dir):
    # Creates an initialized Pit repository in a temporary directory
    original_dir = os.getcwd()
    os.chdir(temp_dir)
    
    # Initialize repository
    pit_dir = os.path.join(temp_dir, '.pit')
    os.makedirs(os.path.join(pit_dir, 'objects'))
    os.makedirs(os.path.join(pit_dir, 'refs', 'heads'))
    with open(os.path.join(pit_dir, 'HEAD'), 'w') as f:
        f.write('ref: refs/heads/master\n')
    
    # Set up config
    config_path = os.path.join(pit_dir, 'config')
    with open(config_path, 'w') as f:
        f.write('[user]\n')
        f.write('name = Test User\n')
        f.write('email = test@example.com\n')
    
    yield temp_dir
    
    os.chdir(original_dir)


@pytest.fixture
def repo_with_file(temp_repo):
    # Creates a repo with a single file (not committed)
    file_path = os.path.join(temp_repo, 'test.txt')
    with open(file_path, 'w') as f:
        f.write('Hello, World!')
    return temp_repo


@pytest.fixture
def repo_with_commit(temp_repo):
    # Creates a repo with one committed file
    # Create and add a file
    file_path = os.path.join(temp_repo, 'README.md')
    with open(file_path, 'w') as f:
        f.write('# Test Project\n')
    
    # Stage the file
    with open(file_path, 'rb') as f:
        content = f.read()
    blob_hash = objects.hash_object(temp_repo, content, 'blob')
    
    stats = os.stat(file_path)
    index = {'README.md': (blob_hash, stats.st_mtime_ns, stats.st_size)}
    index_utils.write_index(temp_repo, index)
    
    # Create commit
    tree_dict = objects.build_tree_from_dict(index)
    tree_hash = objects.write_tree(temp_repo, tree_dict)
    
    import time
    timestamp = int(time.time())
    author = f"Test User <test@example.com> {timestamp} +0000"
    
    commit_content = f"tree {tree_hash}\nauthor {author}\ncommitter {author}\n\nInitial commit"
    commit_hash = objects.hash_object(temp_repo, commit_content.encode(), 'commit')
    
    # Update master branch
    branch_path = os.path.join(temp_repo, '.pit', 'refs', 'heads', 'master')
    with open(branch_path, 'w') as f:
        f.write(commit_hash)
    
    return temp_repo, commit_hash


@pytest.fixture
def repo_with_branches(repo_with_commit):
    # Creates a repo with master and a feature branch
    repo_root, initial_commit = repo_with_commit
    
    # Create feature branch
    feature_branch_path = os.path.join(repo_root, '.pit', 'refs', 'heads', 'feature')
    with open(feature_branch_path, 'w') as f:
        f.write(initial_commit)
    
    return repo_root, initial_commit


# Mock args object for command functions
class MockArgs:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
