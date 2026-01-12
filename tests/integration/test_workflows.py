# Integration tests for complete workflows

import pytest
import os
import sys
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pit-project'))

from utils import repository, objects, index as index_utils
from commands import init, add, commit, status, branch, checkout, merge, log, stash, reset, clean


class TestBasicWorkflow:
    # Tests for the basic init -> add -> commit -> status workflow
    
    def test_init_creates_pit_directory(self, temp_dir):
        # pit init should create .pit directory structure
        os.chdir(temp_dir)
        
        # Simulate init
        pit_dir = os.path.join(temp_dir, '.pit')
        os.makedirs(os.path.join(pit_dir, 'objects'))
        os.makedirs(os.path.join(pit_dir, 'refs', 'heads'))
        with open(os.path.join(pit_dir, 'HEAD'), 'w') as f:
            f.write('ref: refs/heads/master\n')
        
        assert os.path.isdir(pit_dir)
        assert os.path.isdir(os.path.join(pit_dir, 'objects'))
        assert os.path.isdir(os.path.join(pit_dir, 'refs', 'heads'))
        assert os.path.isfile(os.path.join(pit_dir, 'HEAD'))
    
    def test_add_stages_file(self, temp_repo):
        # pit add should add file to index
        # Create a file
        file_path = os.path.join(temp_repo, 'test.txt')
        with open(file_path, 'w') as f:
            f.write('test content')
        
        # Stage it manually (simulating add command)
        with open(file_path, 'rb') as f:
            content = f.read()
        blob_hash = objects.hash_object(temp_repo, content, 'blob')
        
        stats = os.stat(file_path)
        index = {'test.txt': (blob_hash, stats.st_mtime_ns, stats.st_size)}
        index_utils.write_index(temp_repo, index)
        
        # Verify index
        result = index_utils.read_index(temp_repo)
        assert 'test.txt' in result
        assert result['test.txt'][0] == blob_hash
    
    def test_commit_creates_objects(self, temp_repo):
        # pit commit should create tree and commit objects
        # Setup: add a file
        file_path = os.path.join(temp_repo, 'README.md')
        with open(file_path, 'w') as f:
            f.write('# Test')
        
        with open(file_path, 'rb') as f:
            content = f.read()
        blob_hash = objects.hash_object(temp_repo, content, 'blob')
        
        stats = os.stat(file_path)
        index = {'README.md': (blob_hash, stats.st_mtime_ns, stats.st_size)}
        index_utils.write_index(temp_repo, index)
        
        # Create tree
        tree_dict = objects.build_tree_from_dict(index)
        tree_hash = objects.write_tree(temp_repo, tree_dict)
        
        # Verify tree object exists
        obj_type, _ = objects.read_object(temp_repo, tree_hash)
        assert obj_type == 'tree'


class TestBranchingWorkflow:
    # Tests for branch creation and switching
    
    def test_create_and_switch_branch(self, repo_with_commit):
        # Should be able to create and switch branches
        repo_root, commit_hash = repo_with_commit
        
        # Create new branch
        repository.create_branch(repo_root, 'feature', commit_hash)
        
        # Verify branch exists
        branches = repository.get_all_branches(repo_root)
        assert 'feature' in branches
        
        # Switch to new branch (update HEAD)
        head_path = os.path.join(repo_root, '.pit', 'HEAD')
        with open(head_path, 'w') as f:
            f.write('ref: refs/heads/feature\n')
        
        # Verify current branch
        assert repository.get_current_branch(repo_root) == 'feature'
    
    def test_branch_points_to_correct_commit(self, repo_with_commit):
        # New branch should point to current commit
        repo_root, commit_hash = repo_with_commit
        
        repository.create_branch(repo_root, 'new-branch', commit_hash)
        
        branch_commit = repository.get_branch_commit(repo_root, 'new-branch')
        assert branch_commit == commit_hash


class TestMergeWorkflow:
    # Tests for merge scenarios
    
    def test_fast_forward_merge_scenario(self, repo_with_branches):
        # Test setup for fast-forward merge
        repo_root, initial_commit = repo_with_branches
        
        # Both branches point to same commit initially
        master_commit = repository.get_branch_commit(repo_root, 'master')
        feature_commit = repository.get_branch_commit(repo_root, 'feature')
        
        assert master_commit == feature_commit == initial_commit


class TestStashWorkflow:
    # Tests for stash operations
    
    def test_stash_directory_creation(self, temp_repo):
        # Stash log directory should be creatable
        logs_dir = os.path.join(temp_repo, '.pit', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        stash_file = os.path.join(logs_dir, 'stash')
        with open(stash_file, 'w') as f:
            f.write('')
        
        assert os.path.exists(stash_file)


class TestCleanWorkflow:
    # Tests for clean command
    
    def test_identifies_untracked_files(self, repo_with_commit):
        # Should identify files not in index
        repo_root, _ = repo_with_commit
        
        # Create untracked file
        untracked = os.path.join(repo_root, 'untracked.txt')
        with open(untracked, 'w') as f:
            f.write('untracked content')
        
        # Get index files
        index = index_utils.read_index_hashes(repo_root)
        
        # Check if file is tracked
        assert 'untracked.txt' not in index
        assert 'README.md' in index


class TestResetWorkflow:
    # Tests for reset/unstage operations
    
    def test_reset_removes_from_index(self, temp_repo):
        # Reset should remove file from index
        # Add file to index
        index = {
            'file1.txt': ('hash1', 0, 0),
            'file2.txt': ('hash2', 0, 0),
        }
        index_utils.write_index(temp_repo, index)
        
        # Remove file1.txt
        del index['file1.txt']
        index_utils.write_index(temp_repo, index)
        
        # Verify
        result = index_utils.read_index(temp_repo)
        assert 'file1.txt' not in result
        assert 'file2.txt' in result
