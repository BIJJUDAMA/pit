# Unit tests for utils/index.py

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pit-project'))

from utils import index as index_utils


class TestReadIndex:
    """Tests for index_utils.read_index()"""
    
    def test_read_empty_index(self, temp_repo):
        """Should return empty dict when no index exists."""
        result = index_utils.read_index(temp_repo)
        assert result == {}
    
    def test_read_new_format_index(self, temp_repo):
        """Should correctly parse new format: hash mtime size path"""
        index_path = os.path.join(temp_repo, '.pit', 'index')
        with open(index_path, 'w') as f:
            f.write("abc123 1234567890 100 test.txt\n")
            f.write("def456 9876543210 200 src/main.py\n")
        
        result = index_utils.read_index(temp_repo)
        
        assert 'test.txt' in result
        assert result['test.txt'] == ('abc123', 1234567890, 100)
        assert 'src/main.py' in result
        assert result['src/main.py'] == ('def456', 9876543210, 200)
    
    def test_read_old_format_index(self, temp_repo):
        """Should handle old format: hash path (backwards compatibility)"""
        index_path = os.path.join(temp_repo, '.pit', 'index')
        with open(index_path, 'w') as f:
            f.write("abc123 old_file.txt\n")
        
        result = index_utils.read_index(temp_repo)
        
        assert 'old_file.txt' in result
        assert result['old_file.txt'] == ('abc123', 0, 0)  # Default mtime/size


class TestReadIndexHashes:
    """Tests for index_utils.read_index_hashes()"""
    
    def test_returns_only_hashes(self, temp_repo):
        """Should return dict of {path: hash} only."""
        index_path = os.path.join(temp_repo, '.pit', 'index')
        with open(index_path, 'w') as f:
            f.write("abc123 1234567890 100 test.txt\n")
        
        result = index_utils.read_index_hashes(temp_repo)
        
        assert result == {'test.txt': 'abc123'}


class TestWriteIndex:
    """Tests for index_utils.write_index()"""
    
    def test_write_tuple_format(self, temp_repo):
        """Should write index with tuple values (hash, mtime, size)."""
        index = {
            'file1.txt': ('hash1', 12345, 100),
            'file2.txt': ('hash2', 67890, 200),
        }
        
        index_utils.write_index(temp_repo, index)
        
        # Read back and verify
        index_path = os.path.join(temp_repo, '.pit', 'index')
        with open(index_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        assert 'hash1 12345 100 file1.txt\n' in lines
        assert 'hash2 67890 200 file2.txt\n' in lines
    
    def test_write_string_format(self, temp_repo):
        """Should handle string values (just hash, defaults mtime/size to 0)."""
        index = {
            'test.txt': 'hashonly',
        }
        
        index_utils.write_index(temp_repo, index)
        
        result = index_utils.read_index(temp_repo)
        assert result['test.txt'] == ('hashonly', 0, 0)
    
    def test_sorted_output(self, temp_repo):
        """Should write entries in sorted order."""
        index = {
            'z_last.txt': ('hash3', 0, 0),
            'a_first.txt': ('hash1', 0, 0),
            'm_middle.txt': ('hash2', 0, 0),
        }
        
        index_utils.write_index(temp_repo, index)
        
        index_path = os.path.join(temp_repo, '.pit', 'index')
        with open(index_path, 'r') as f:
            lines = f.readlines()
        
        assert 'a_first.txt' in lines[0]
        assert 'm_middle.txt' in lines[1]
        assert 'z_last.txt' in lines[2]
