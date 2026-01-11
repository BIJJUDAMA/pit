# The command: pit log
# What it does: Displays the commit history by starting at the current HEAD and walking backward through the parent links
# How it does: It starts with the current commit hash and enters a loop. Inside the loop, it reads the commit object, prints its information, and finds the parent hash. It then uses the parent hash for the next loop iteration, continuing until no parent is found. This is a classic depth-first traversal
# What data structure it uses: It performs a Graph Traversal (specifically, a linear traversal up the parent chain) on the Directed Acyclic Graph (DAG) formed by the commits
import sys
import os
import time
from datetime import datetime, timedelta
from utils import repository, objects
import fnmatch

def run(args): 
    repo_root = repository.find_repo_root()
    if not repo_root: #Check if inside a pit repository
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)

    commit_hash = repository.get_head_commit(repo_root)
    if not commit_hash: # Check if there are any commits
        current_branch = repository.get_current_branch(repo_root) or 'master'
        print(f"fatal: your current branch '{current_branch}' does not have any commits yet")
        return

    # Handle different log formats
    if args.oneline:
        _show_oneline_log(repo_root, commit_hash, args)
    elif args.graph:
        _show_graph_log(repo_root, commit_hash, args)
    else:
        _show_standard_log(repo_root, commit_hash, args)
        
#Standard detailed log output with DAG traversa
def _show_standard_log(repo_root, start_commit, args):
   
    visited = set()
    stack = [start_commit]
    commit_count = 0
    
    while stack and (args.max_count is None or commit_count < args.max_count):
        current_hash = stack.pop()
        if current_hash in visited:
            continue
        visited.add(current_hash)
        
        try:
            commit_data = _get_commit_data(repo_root, current_hash)
            
            # Apply filters
            if args.since and not _is_commit_after_date(commit_data, args.since):
                continue
                
            if args.grep and not _commit_matches_grep(commit_data, args.grep):
                continue
                
            if args.file and not _commit_affects_file(repo_root, commit_data, args.file):
                continue
            
            _print_commit_details(repo_root, commit_data, args)
            commit_count += 1
            
            # Add parents to stack in reverse order for proper DAG traversal
            for parent in reversed(commit_data['parents']):
                if parent not in visited:
                    stack.append(parent)
                    
        except Exception as e:
            print(f"Warning: {e}", file=sys.stderr)
            continue
        
def _show_oneline_log(repo_root, start_commit, args):
    visited = set()
    stack = [start_commit]
    commit_count = 0
    
    while stack and (args.max_count is None or commit_count < args.max_count):
        current_hash = stack.pop()
        if current_hash in visited:
            continue
        visited.add(current_hash)
        
        try:
            commit_data = _get_commit_data(repo_root, current_hash)
            
            # Apply filters
            if args.since and not _is_commit_after_date(commit_data, args.since):
                continue
                
            if args.grep and not _commit_matches_grep(commit_data, args.grep):
                continue
                
            if args.file and not _commit_affects_file(repo_root, commit_data, args.file):
                continue
            
            # One-line format: <short-hash> <message>
            short_hash = current_hash[:7]
            first_line = commit_data['message'].split('\n')[0]
            print(f"{short_hash} {first_line}")
            commit_count += 1
            
            # Add parents to stack in reverse order for proper DAG traversal
            for parent in reversed(commit_data['parents']):
                if parent not in visited:
                    stack.append(parent)
                    
        except Exception as e:
            continue
#ASCII graph representation of commit history 
def _show_graph_log(repo_root, start_commit, args):
    print("Graph visualization:")
    print("")
    
    visited = set()
    stack = [start_commit]
    commit_count = 0
    
    while stack and (args.max_count is None or commit_count < args.max_count):
        current_hash = stack.pop()
        if current_hash in visited:
            continue
        visited.add(current_hash)
        
        try:
            commit_data = _get_commit_data(repo_root, current_hash)
            
            # Apply filters
            if args.since and not _is_commit_after_date(commit_data, args.since):
                continue
                
            if args.grep and not _commit_matches_grep(commit_data, args.grep):
                continue
                
            if args.file and not _commit_affects_file(repo_root, commit_data, args.file):
                continue
            
            # Graph indicators based on commit type
            branch_indicator = ""
            if len(commit_data['parents']) > 1:
                branch_indicator = " (merge)"
            elif len(commit_data['parents']) == 0:
                branch_indicator = " (root)"
                
            short_hash = current_hash[:7]
            first_line = commit_data['message'].split('\n')[0]
            
            #ASCII graph lines
            graph_line = _generate_graph_line(repo_root, current_hash, commit_data['parents'])
            print(f"{graph_line} {short_hash}{branch_indicator} {first_line}")
            
            commit_count += 1
            
            # Add parents to stack in reverse order
            for parent in reversed(commit_data['parents']):
                if parent not in visited:
                    stack.append(parent)
                    
        except Exception as e:
            continue

#Simple ASCII graph line indicating branch structure
def _generate_graph_line(repo_root, commit_hash, parents):
    if len(parents) == 0:
        return "*"  # Root commit
    elif len(parents) == 1:
        return "| *"  # Normal commit
    else:
        return "|\\ *"  # Merge commit
    
# Getting structured commit data
def _get_commit_data(repo_root, commit_hash):
    obj_type, content = objects.read_object(repo_root, commit_hash)
    if obj_type != 'commit':
        raise ValueError(f"Object {commit_hash} is not a commit")
    
    lines = content.decode().splitlines()
    commit_data = {
        'hash': commit_hash,
        'tree': None,
        'parents': [],
        'author': {},
        'committer': {},
        'message': ''
    }
    
    message_started = False
    message_lines = []
    
    for line in lines:
        if line.startswith('tree '):
            commit_data['tree'] = line.split(' ')[1]
        elif line.startswith('parent '):
            parent_hash = line.split(' ')[1]
            commit_data['parents'].append(parent_hash)
        elif line.startswith('author '):
            commit_data['author'] = _parse_author_line(line[7:])
        elif line.startswith('committer '):
            commit_data['committer'] = _parse_author_line(line[10:])
        elif not line.strip() and not message_started:
            message_started = True
        elif message_started:
            message_lines.append(line)
    
    commit_data['message'] = '\n'.join(message_lines)
    return commit_data

def _parse_author_line(line):
    # Format: "Name <email> timestamp timezone"
    parts = line.split(' ')
    if len(parts) >= 4:
        # Extract name and email
        name_email = ' '.join(parts[:-2])
        email_start = name_email.find('<')
        email_end = name_email.find('>')
        
        if email_start != -1 and email_end != -1:
            name = name_email[:email_start].strip()
            email = name_email[email_start+1:email_end]
            timestamp = int(parts[-2])
            timezone = parts[-1]
            
            return {
                'name': name,
                'email': email,
                'timestamp': timestamp,
                'timezone': timezone,
                'date': datetime.fromtimestamp(timestamp)
            }
    
    return {'name': line, 'email': '', 'timestamp': 0, 'timezone': '', 'date': datetime.now()}

def _is_commit_after_date(commit_data, since_str):
    if not commit_data['author'].get('date'):
        return True
        
    commit_date = commit_data['author']['date']
    since_str = since_str.strip('"\'')  # Remove quotes
    
    # Parse relative time strings
    since_lower = since_str.lower()
    if 'ago' in since_lower:
        return _is_within_relative_time(commit_date, since_str)
    else:
        # Handle absolute dates
        try:
            since_date = datetime.fromisoformat(since_str)
            return commit_date >= since_date
        except:
            # If date parsing fails, show all commits
            return True

def _is_within_relative_time(commit_date, time_str):
    time_str = time_str.lower().replace('"', '').replace("'", "")
    words = time_str.split()
    if len(words) < 2:
        return True
        
    try:
        number = int(words[0])
        unit = words[1]
        
        if 'week' in unit:
            cutoff = datetime.now() - timedelta(weeks=number)
        elif 'day' in unit:
            cutoff = datetime.now() - timedelta(days=number)
        elif 'month' in unit:
            cutoff = datetime.now() - timedelta(days=number*30)
        elif 'year' in unit:
            cutoff = datetime.now() - timedelta(days=number*365)
        elif 'hour' in unit:
            cutoff = datetime.now() - timedelta(hours=number)
        else:
            return True
            
        return commit_date >= cutoff
    except:
        return True
    
# Check if commit message matches grep pattern
def _commit_matches_grep(commit_data, pattern):
    if not pattern:
        return True
    return pattern.lower() in commit_data['message'].lower()

# Check if commit affects a specific file
def _commit_affects_file(repo_root, commit_data, file_pattern):
    try:
        commit_files = objects.get_commit_files(repo_root, commit_data['hash'])
        
        # Wildcard support using fnmatch
        if '*' in file_pattern or '?' in file_pattern or '[' in file_pattern:
            for file_path in commit_files.keys():
                if fnmatch.fnmatch(file_path, file_pattern):
                    return True
            return False
        else:
            # Exact match for normal file paths
            return file_pattern in commit_files
            
    except Exception as e:
        print(f"Debug: Error checking files in commit {commit_data['hash'][:7]}: {e}", file=sys.stderr)
        return False

def _print_commit_details(repo_root, commit_data, args):
    print(f"commit {commit_data['hash']}")    
    # Show merge parents if it's a merge commit
    if len(commit_data['parents']) > 1:
        parent_short = [p[:7] for p in commit_data['parents']]
        print(f"Merge: {' '.join(parent_short)}")
    
    author = commit_data['author']
    if author.get('name'):
        print(f"Author: {author['name']} <{author.get('email', '')}>")
        if author.get('date'):
            print(f"Date:   {author['date'].strftime('%a %b %d %H:%M:%S %Y %z')}")
    
    print()
    print(commit_data['message'])
    print()
    
    if getattr(args, 'patch', False) and getattr(args, 'file', None):
        _show_file_patch(repo_root, commit_data, args.file)

def _show_file_patch(repo_root, commit_data, file_path):
    try:
        # Get current file content from commit
        commit_files = objects.get_commit_files(repo_root, commit_data['hash'])
        if file_path not in commit_files:
            return
            
        # Get parent file content for comparison (use first parent)
        parent_files = {}
        if commit_data['parents']:
            parent_files = objects.get_commit_files(repo_root, commit_data['parents'][0])
        
        current_hash = commit_files[file_path]
        parent_hash = parent_files.get(file_path)
        
        current_content = b''
        parent_content = b''
        
        if current_hash:
            obj_type, content = objects.read_object(repo_root, current_hash)
            if obj_type == 'blob':
                current_content = content
                
        if parent_hash:
            obj_type, content = objects.read_object(repo_root, parent_hash)
            if obj_type == 'blob':
                parent_content = content
        
        # Simple diff output
        print(f"diff --pit a/{file_path} b/{file_path}")
        print(f"--- a/{file_path}")
        print(f"+++ b/{file_path}")
        
        current_lines = current_content.decode('utf-8', errors='ignore').splitlines()
        parent_lines = parent_content.decode('utf-8', errors='ignore').splitlines()
        
        # Simple line-by-line comparison
        max_lines = max(len(current_lines), len(parent_lines))
        for i in range(max_lines):
            current_line = current_lines[i] if i < len(current_lines) else None
            parent_line = parent_lines[i] if i < len(parent_lines) else None
            
            if current_line != parent_line:
                if parent_line is not None:
                    print(f"-{parent_line}")
                if current_line is not None:
                    print(f"+{current_line}")
            
        print()
        
    except Exception as e:
        # Skip patch if there's an error
        pass