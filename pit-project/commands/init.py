# The command: pit init
# What it does: Initializes a new, empty repository by creating the hidden `.pit` directory and its internal structure
# How it does: It creates the `objects` and `refs/heads` subdirectories. It then creates the `HEAD` file and writes a symbolic reference pointing to the default 'master' branch
# What data structure it uses: Tree (the file system directory structure is a tree). It also lays the foundation for a Hash Table (the object database) and a Directed Acyclic Graph (the commit history)

import sys

def run(args):

    try:
        # Get the path for the new repository (current directory)
        repo_path = os.path.join(os.getcwd(), '.pit')
        
        if os.path.exists(repo_path):
            print(f"Reinitialized existing Pit repository in {repo_path}/")
            return

        # Create the main .pit directory and subdirectories
        os.makedirs(os.path.join(repo_path, 'objects'), exist_ok=True)
        os.makedirs(os.path.join(repo_path, 'refs', 'heads'), exist_ok=True)

        # Create the HEAD file to point to the master branch
        head_path = os.path.join(repo_path, 'HEAD')
        with open(head_path, 'w') as f:
            f.write('ref: refs/heads/master\n')
            
        # The master branch file is created but will be empty until the first commit
        master_branch_path = os.path.join(repo_path, 'refs', 'heads', 'master')
        open(master_branch_path, 'w').close()
            
        print(f"Initialized empty Pit repository in {repo_path}/")

    except Exception as e:
        print(f"Error initializing repository: {e}", file=sys.stderr)
        sys.exit(1)

