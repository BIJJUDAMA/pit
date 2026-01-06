# The command: pit tag [<name>]
# What it does: Creates a lightweight tag ref pointing to the current HEAD, or lists existing tags.
# How it does: To create a tag, it gets the HEAD commit hash and writes it to a file in `.pit/refs/tags/<name>`. To list, it reads that directory.
# What data structure it uses: Files references (similar to branches).

import os
import sys
from utils import repository

def run(args):
    repo_root = repository.find_repo_root()
    if not repo_root:
        print("fatal: not a pit repository", file=sys.stderr)
        sys.exit(1)
        
    if args.name:
        create_tag(repo_root, args.name)
    else:
        list_tags(repo_root)

def create_tag(repo_root, name):
    # Validate tag name? (Simple check for now)
    if not name or '/' in name or '\\' in name or name.startswith('.'):
         print(f"fatal: Invalid tag name '{name}'", file=sys.stderr)
         sys.exit(1)
         
    head_commit = repository.get_head_commit(repo_root)
    if not head_commit:
        print("fatal: Failed to resolve 'HEAD' as a valid revision.", file=sys.stderr)
        sys.exit(1)
        
    tags_dir = os.path.join(repo_root, '.pit', 'refs', 'tags')
    os.makedirs(tags_dir, exist_ok=True)
    
    tag_path = os.path.join(tags_dir, name)
    if os.path.exists(tag_path):
        print(f"fatal: tag '{name}' already exists", file=sys.stderr)
        sys.exit(1)
        
    with open(tag_path, 'w') as f:
        f.write(head_commit)
        
    print(f"Created tag '{name}' at {head_commit[:7]}")

def list_tags(repo_root):
    tags = repository.get_all_tags(repo_root)
    if not tags:
        return
        
    for tag in sorted(tags):
        print(tag)
