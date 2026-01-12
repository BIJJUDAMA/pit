# Unit tests for utils/repository.py

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pit-project'))

from utils import repository


class TestFindRepoRoot:
    # Tests for repository.find_repo_root()
    
    def test_finds_repo_in_current_dir(self, temp_repo):
        # Should find repo when in root directory
        result = repository.find_repo_root(temp_repo)
        assert result == temp_repo
    
    def test_finds_repo_in_subdirectory(self, temp_repo):
        # Should find repo when in a subdirectory
        subdir = os.path.join(temp_repo, 'src', 'deep', 'nested')
        os.makedirs(subdir)
        os.chdir(subdir)
        
        result = repository.find_repo_root()
        # Use realpath to resolve symlinks 
        assert os.path.realpath(result) == os.path.realpath(temp_repo)
    
    def test_returns_none_when_not_in_repo(self, temp_dir):
        # Should return None when not in a repository
        result = repository.find_repo_root(temp_dir)
        assert result is None


class TestGetHeadCommit:
    # Tests for repository.get_head_commit()
    
    def test_returns_none_for_empty_repo(self, temp_repo):
        # Should return None when no commits exist
        result = repository.get_head_commit(temp_repo)
        assert result is None
    
    def test_returns_commit_hash(self, repo_with_commit):
        # Should return the commit hash when commits exist
        repo_root, commit_hash = repo_with_commit
        result = repository.get_head_commit(repo_root)
        assert result == commit_hash
    
    def test_handles_detached_head(self, repo_with_commit):
        # Should return hash when HEAD is detached
        repo_root, commit_hash = repo_with_commit
        
        # Detach HEAD
        head_path = os.path.join(repo_root, '.pit', 'HEAD')
        with open(head_path, 'w') as f:
            f.write(commit_hash)
        
        result = repository.get_head_commit(repo_root)
        assert result == commit_hash


class TestGetCurrentBranch:
    # Tests for repository.get_current_branch()
    
    def test_returns_branch_name(self, temp_repo):
        # Should return current branch name
        result = repository.get_current_branch(temp_repo)
        assert result == 'master'
    
    def test_returns_none_when_detached(self, repo_with_commit):
        # Should return None when HEAD is detached
        repo_root, commit_hash = repo_with_commit
        
        # Detach HEAD
        head_path = os.path.join(repo_root, '.pit', 'HEAD')
        with open(head_path, 'w') as f:
            f.write(commit_hash)
        
        result = repository.get_current_branch(repo_root)
        assert result is None


class TestGetHeadStatus:
    # Tests for repository.get_head_status()
    
    def test_on_branch(self, temp_repo):
        # Should return 'On branch X' when on a branch
        result = repository.get_head_status(temp_repo)
        assert result == "On branch master"
    
    def test_detached_head(self, repo_with_commit):
        # Should return detached message when HEAD is detached
        repo_root, commit_hash = repo_with_commit
        
        # Detach HEAD
        head_path = os.path.join(repo_root, '.pit', 'HEAD')
        with open(head_path, 'w') as f:
            f.write(commit_hash)
        
        result = repository.get_head_status(repo_root)
        assert f"HEAD detached at {commit_hash[:7]}" == result


class TestGetAllBranches:
    # Tests for repository.get_all_branches()
    
    def test_lists_all_branches(self, repo_with_branches):
        # Should list all branches
        repo_root, _ = repo_with_branches
        result = repository.get_all_branches(repo_root)
        
        assert 'master' in result
        assert 'feature' in result
        assert len(result) == 2


class TestCreateBranch:
    # Tests for repository.create_branch()
    
    def test_creates_branch_file(self, repo_with_commit):
        # Should create a new branch file
        repo_root, commit_hash = repo_with_commit
        
        repository.create_branch(repo_root, 'new-branch', commit_hash)
        
        branch_path = os.path.join(repo_root, '.pit', 'refs', 'heads', 'new-branch')
        assert os.path.exists(branch_path)
        
        with open(branch_path, 'r') as f:
            assert f.read().strip() == commit_hash
