# Pit - A Simple Version Control System

Pit is a simplified version control system built from scratch in Python. It is designed as an educational project to understand the core concepts of version control systems like Git.

## Core Concepts

Pit is built on the same three fundamental ideas that power Git:

1. **Content-Addressable Storage (Blobs)**
2. **Hierarchical Trees (Merkle Trees)**
3. **Historical Snapshots (Commits)**

## Features

### Basic Commands

- `pit init` - Initialize a new repository
- `pit config user.name "Name"` - Set user name
- `pit config user.email "email"` - Set user email
- `pit add <file>` - Stage files for commit
- `pit commit -m "message"` - Create a commit
- `pit status` - Show working directory status
- `pit log` - Show commit history
- `pit log --oneline` - Compact commit history
- `pit log --graph` - Visualize branch history

### Branching & Merging

- `pit branch` - List branches
- `pit branch <name>` - Create new branch
- `pit checkout <branch>` - Switch branches
- `pit merge <branch>` - Merge branches (three-way merge)
- `pit revert <commit>` - Revert a commit

### Comparison & Inspection

- `pit diff` - Show unstaged changes
- `pit diff --staged` - Show staged changes
- `pit reset <file>` - Unstage files
- `pit checkout <file>` - Discard changes in working directory (restore file from index)

## Example Workflow

```bash
# Initialize repository and set user
pit init
pit config user.name "Test"
pit config user.email "test@example.com"

# Create initial files and commit
echo "# My Project" > README.md
mkdir src
echo "print('hello')" > src/main.py
pit add .
pit commit -m "Initial project structure"

# Check status and view history
pit status
pit log

# Create and switch to feature branch
pit branch feature-auth
pit checkout feature-auth

# Develop feature
echo "def authenticate():" > src/auth.py
echo "    return True" >> src/auth.py
pit add src/auth.py
pit commit -m "Add authentication module"

# Switch back to main and make changes
pit checkout master
echo "Updated documentation" >> README.md
pit add README.md
pit commit -m "Update README"

# Merge feature branch
pit merge feature-auth

# View merge history
pit log --graph

# Create conflict scenario
pit branch conflict-branch
pit checkout conflict-branch
echo "conflict version A" > conflict.txt
pit add conflict.txt
pit commit -m "Add conflict file A"

pit checkout master
echo "conflict version B" > conflict.txt
pit add conflict.txt
pit commit -m "Add conflict file B"

# Attempt merge (will show conflicts)
pit merge conflict-branch

# View differences
pit diff
pit diff --staged

# Test reset command
echo "new file to reset" > reset-test.txt
pit add reset-test.txt
pit reset reset-test.txt
pit status

# Revert a commit
pit log --oneline  # find commit hash to revert
pit revert <commit-hash>
```

## Project Structure

```
pit-project/
├── pit.py                 # Main entry point
├── commands/              # Command implementations
│   ├── init.py
│   ├── add.py
│   ├── commit.py
│   ├── log.py
│   ├── status.py
│   ├── config.py
│   ├── branch.py
│   ├── checkout.py
│   ├── diff.py
│   ├── merge.py
│   ├── reset.py
│   └── revert.py
└── utils/              # Core utilities (object storage, repo state, etc.)
    ├── repository.py   # Find repo, manage HEAD/branches
    ├── objects.py      # Read/write blobs, trees, commits
    ├── config.py       # Read/write .pit/config
    ├── ignore.py       # Handle .pitignore
    └── diff.py         # State comparison and diff generation
```

## Internal Data Structures

Pit leverages several fundamental data structures internally:

- **Hash Tables / Dictionaries:** Used extensively for the object store (mapping hashes to compressed content), representing the index (mapping file paths to hashes), and managing configuration.
- **Merkle Trees:** Implicitly built by the `commit` command using nested tree objects to represent the directory structure efficiently.
- **Directed Acyclic Graph (DAG):** Formed by commits pointing to their parent(s), representing the project history. Traversed by `log` and `merge`.
- **Sets:** Used for efficient comparison of file lists in `status` and `diff`.
- **Lists / Arrays:** Used for temporary storage, like holding index lines during `reset` or branch names during listing.

---

## Advanced Features Implemented

### Three-Way Merge Algorithm

- The `pit merge` command implements a three-way merge strategy.
- It automatically finds the **best common ancestor** commit between the current branch and the branch being merged using a Breadth-First Search on the commit DAG.
- It compares the file states of the ancestor, the current branch head, and the merging branch head to determine changes.
- If both branches modified the same file differently relative to the ancestor, it  **detects and reports conflicts** .
- Successful merges result in a **merge commit** with two parents.

### Conflict Markers

- When a content conflict occurs during a merge, Pit writes conflict markers directly into the affected file in the working directory:

  ```
  <<<<<<< HEAD
  Content from the current branch (HEAD)
  =======
  Content from the branch being merged
  >>>>>>> <branch-name>
  ```

* The `pit status` command will indicate conflicted files. Manual resolution is required before committing.

### Diffing Capabilities

- `pit diff` compares the **working directory** against the  **index (staging area)** , showing unstaged changes.
- `pit diff --staged` compares the **index (staging area)** against the  **HEAD commit** , showing changes staged for the next commit.
- Uses Python's `difflib` to generate standard unified diff output.

---

## Running Pit

### Docker (Recommended)

```
docker build -t pit-env .
```

#### Linux/macOS

```
docker run -it --rm -v "$(pwd)":/workspace pit-env
```

#### Windows (PowerShell)

```
docker run -it --rm -v "${PWD}:/workspace" pit-env
```

### Direct Python

```bash
python3 pit.py <command> [arguments]
```

## Limitations

- **Local Only:** This implementation focuses on local repository operations. It does not include network protocols (`clone`, `fetch`, `pull`, `push`).
- **Basic Conflict Handling:** Merge conflicts are detected and marked, but manual resolution is always required. No merge strategies or tools are included.
- **No History Rewriting:** Commands like `rebase` or amending commits are not implemented.
- **Limited Branch Checkout:** `pit checkout <branch>` only switches the `HEAD` pointer. It **does not automatically update the index or working directory** to match the state of the target branch's commit (unlike Git, which typically performs this update). `pit checkout <file>`. correctly restores files in the working directory from the index.
- **Simplifications:** Object storage, tree format, and index format might differ slightly from Git's internal details for simplicity. Error handling might be less robust than Git's
