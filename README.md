# Pit - A Simple Version Control System

Pit is a simplified version control system built from scratch in Python. It is designed as an educational project to understand the core concepts of version control systems like Git.

## Core Concepts

Pit is built on the same three fundamental ideas that power Git:

1. **Content-Addressable Storage (Blobs)**
2. **Hierarchical Trees (Merkle Trees)**
3. **Historical Snapshots (Commits)**

## Features

### Basic Commands

| Command | Description |
|---------|-------------|
| `pit init` | Initialize a new repository |
| `pit config user.name "Name"` | Set user name |
| `pit config user.email "email"` | Set user email |
| `pit add <file>` | Stage files for commit |
| `pit add .` | Stage all files in current directory |
| `pit commit -m "message"` | Create a commit |
| `pit status` | Show working directory status |
| `pit log` | Show commit history |
| `pit log --oneline` | Compact commit history |
| `pit log --graph` | Visualize branch history |
| `pit log --grep "pattern"` | Filter commits by message |
| `pit log --since "2 days ago"` | Filter commits by date |
| `pit log --patch <file>` | Show file changes in commits |

### Branching & Merging

| Command | Description |
|---------|-------------|
| `pit branch` | List all branches |
| `pit branch <name>` | Create new branch |
| `pit checkout <branch>` | Switch branches |
| `pit checkout -b <branch>` | Create and switch to new branch |
| `pit merge <branch>` | Merge branches (three-way merge) |
| `pit rebase <upstream>` | Reapply commits on new base |
| `pit rebase --continue` | Continue after conflict resolution |
| `pit rebase --abort` | Abort rebase and restore state |
| `pit revert <commit>` | Create commit that undoes changes |

### Stash

| Command | Description |
|---------|-------------|
| `pit stash` | Save working directory state |
| `pit stash push -m "message"` | Save with message |
| `pit stash pop` | Restore most recent stash |
| `pit stash list` | List all stashes |
| `pit stash clear` | Remove all stashes |

### Comparison & Inspection

| Command | Description |
|---------|-------------|
| `pit diff` | Show unstaged changes |
| `pit diff --staged` | Show staged changes |
| `pit difftool` | Open external diff tool |
| `pit difftool --staged` | Diff staged changes in external tool |

### Workspace Management

| Command | Description |
|---------|-------------|
| `pit reset <file>` | Unstage files |
| `pit checkout <file>` | Restore file from index |
| `pit clean` | Preview untracked files to remove |
| `pit clean -n` | Dry-run (show what would be removed) |
| `pit clean -f` | Force delete untracked files |
| `pit clean -d` | Also remove untracked directories |

### Conflict Resolution

| Command | Description |
|---------|-------------|
| `pit mergetool` | Open external merge tool for conflicts |

## Example Workflow

```bash
# Initialize a new repository
pit init

# Configure user identity
pit config user.name "Developer"
pit config user.email "dev@example.com"

# Create initial files
echo "# My Project" > README.md
mkdir src
echo "print('hello')" > src/main.py

# Stage all files
pit add .

# Check what's staged
pit status

# Commit changes
pit commit -m "Initial project structure"

# View commit history
pit log
pit log --oneline
pit log --graph

# List branches
pit branch

# Create a new branch
pit branch feature-auth

# Switch to the new branch
pit checkout feature-auth

# Or create and switch in one command
pit checkout -b feature-login

# Make changes to a file
echo "def login(): pass" > src/auth.py

# View unstaged changes
pit diff

# Stage the file
pit add src/auth.py

# View staged changes
pit diff --staged

# Commit
pit commit -m "Add authentication module"

# Make a change and stage it
echo "temporary" > temp.txt
pit add temp.txt

# Unstage the file (keep working directory)
pit reset temp.txt

# Restore file from index (discard changes)
pit checkout temp.txt

# Switch back to master
pit checkout master

# Make changes on master
echo "Updated docs" >> README.md
pit add README.md
pit commit -m "Update README"

# Merge feature branch
pit merge feature-auth

# View merge history
pit log --graph

# Create conflicting changes
pit branch conflict-test
pit checkout conflict-test
echo "version A" > conflict.txt
pit add conflict.txt
pit commit -m "Add conflict file A"

pit checkout master
echo "version B" > conflict.txt
pit add conflict.txt
pit commit -m "Add conflict file B"

# Attempt merge (will show conflicts)
pit merge conflict-test

# Open merge tool to resolve
pit mergetool

# After resolving, commit the merge
pit add conflict.txt
pit commit -m "Resolve merge conflict"

# Make changes but don't commit yet
echo "work in progress" > wip.txt
pit add wip.txt

# Stash changes to switch context
pit stash push -m "Saving WIP feature"

# List stashes
pit stash list

# Do other work...
pit checkout master

# Return and restore stash
pit checkout feature-auth
pit stash pop

# Create a feature branch from old commit
pit checkout -b feature-rebase
echo "new feature" > feature.txt
pit add feature.txt
pit commit -m "Add new feature"

# Rebase onto latest master
pit rebase master

# If conflicts occur:
# pit mergetool          # resolve conflicts
# pit add <file>         # stage resolved files
# pit rebase --continue  # continue rebase

# Or abort if needed:
# pit rebase --abort

# View history to find commit to revert
pit log --oneline

# Revert a specific commit (creates new commit)
pit revert <commit-hash>

# Create some untracked files
echo "junk" > temp1.txt
echo "junk" > temp2.txt
mkdir temp_dir

# Preview what would be removed
pit clean -n

# Preview including directories
pit clean -n -d

# Force delete untracked files
pit clean -f

# Force delete files and directories
pit clean -f -d

# Compare using external diff tool
pit difftool

# Compare staged changes
pit difftool --staged

# Search commit messages
pit log --grep "feature"

# Show commits since date
pit log --since "1 week ago"

# Show patch for specific file
pit log --patch src/main.py

# Limit number of commits
pit log -n 5
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
│   ├── difftool.py
│   ├── merge.py
│   ├── mergetool.py
│   ├── reset.py
│   ├── revert.py
│   ├── rebase.py
│   ├── stash.py
│   └── clean.py
└── utils/                 # Core utilities
    ├── repository.py      # Find repo, manage HEAD/branches
    ├── objects.py         # Read/write blobs, trees, commits
    ├── index.py           # Centralized index operations
    ├── config.py          # Read/write .pit/config
    ├── ignore.py          # Handle .pitignore
    └── diff.py            # State comparison and diff generation
```

## Internal Data Structures

Pit leverages several fundamental data structures internally:

| Data Structure | Usage |
|---------------|-------|
| **Hash Tables / Dictionaries** | Object store (hash → content), index (path → hash), configuration |
| **Merkle Trees** | Directory structure representation via nested tree objects |
| **Directed Acyclic Graph (DAG)** | Commit history with parent pointers |
| **Sets** | Efficient file list comparison in `status` and `diff` |
| **Stacks** | Stash implementation via reflog |

---

## Advanced Features

### Three-Way Merge Algorithm

- The `pit merge` command implements a three-way merge strategy
- Automatically finds the **best common ancestor** using BFS on the commit DAG
- Compares file states of ancestor, current HEAD, and merging branch
- **Detects and reports conflicts** when both branches modify the same file differently
- Creates a **merge commit** with two parents on success

### Conflict Markers

When a content conflict occurs, Pit writes markers into the file:

```
<<<<<<< HEAD
Content from the current branch (HEAD)
=======
Content from the branch being merged
>>>>>>> <branch-name>
```

Use `pit mergetool` to open an external tool for conflict resolution.

### Rebase

- `pit rebase <upstream>` replays commits on top of another base
- Supports `--continue` after resolving conflicts
- Supports `--abort` to cancel and restore original state

### Stash

- Saves both index and working directory state
- Creates internal commit objects to persist state
- Stack-based (LIFO) storage in `.pit/logs/stash`

### Diffing Capabilities

- `pit diff` compares **working directory** vs **index** (unstaged changes)
- `pit diff --staged` compares **index** vs **HEAD** (staged changes)
- Uses Python's `difflib` for unified diff output
- External tool support via `pit difftool`

### Command Aliases

Configure aliases in `.pit/config`:

```ini
[alias]
st = status
co = checkout
br = branch
ci = commit
```

---

## Running Pit

### Docker (Recommended)

```bash
docker build -t pit-env .
```

#### Linux/macOS

```bash
docker run -it --rm -v "$(pwd)":/workspace pit-env
```

#### Windows (PowerShell)

```powershell
docker run -it --rm -v "${PWD}:/workspace" pit-env
```

### Direct Python

```bash
python3 pit.py <command> [arguments]
```

---

## Testing

### Running Tests Locally

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage report
pytest --cov=pit-project --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests for utility functions
│   ├── test_index.py
│   └── test_repository.py
└── integration/             # Workflow integration tests
    └── test_workflows.py
```

### GitHub Actions CI

Tests run automatically on push/PR to `main` or `master`:
- **Multi-platform**: Ubuntu, Windows, macOS
- **Multi-version**: Python 3.10, 3.11, 3.12
- **Coverage**: Reports uploaded to Codecov

See `.github/workflows/test.yml` for configuration.

---

## Limitations

| Limitation | Description |
|------------|-------------|
| **Local Only** | No network operations (`clone`, `fetch`, `pull`, `push`) |
| **Basic Conflict Handling** | Conflicts require manual resolution |
| **Cross-Platform** | Fully supports Windows, macOS, and Linux |

---

## Configuration

### User Configuration

```bash
pit config user.name "Your Name"
pit config user.email "your@email.com"
```

### External Tools

Configure in `.pit/config`:

```ini
[diff]
tool = code --wait --diff $LOCAL $REMOTE

[merge]
tool = code --wait --merge $LOCAL $REMOTE $BASE $MERGED
```

---

## .pitignore

Create a `.pitignore` file to exclude files from tracking:

```
# Ignore build artifacts
*.pyc
__pycache__/
build/
dist/

# Ignore IDE files
.vscode/
.idea/
```

Default ignored patterns: `.pit`, `.pit/*`, `*.pyc`, `__pycache__`
