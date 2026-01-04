# Contribution Guide

## Adding New Commands

Every new command file in `commands/` must include a header with the following four fields:

1. **# The command**: The exact CLI signature (e.g., `pit branch [<name>]`).
2. **# What it does**: A high-level description of the user-facing behavior.
3. **# How it does**: A technical breakdown of how it interacts with the `.pit` directory and the filesystem.
4. **# What data structure it uses**: An explicit mention of the data structures (Lists, Maps/Dicts, Sets) and why they were chosen.

### Example Header

```python
# The command: pit init
# What it does: Initializes a new, empty repository by creating the hidden `.pit` directory and its internal structure
# How it does: It creates the `objects` and `refs/heads` subdirectories. It then creates the `HEAD` file and writes a symbolic reference pointing to the default 'master' branch
# What data structure it uses: Tree (the file system directory structure is a tree). It also lays the foundation for a Hash Table (the object database) and a Directed Acyclic Graph (the commit history)
```
