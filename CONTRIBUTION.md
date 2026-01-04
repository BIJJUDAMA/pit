# Contributing to Pit

Thank you for your interest in contributing to **Pit**! To maintain the project's educational value and technical consistency, we require all contributors to follow these documentation and implementation standards.

## Command Documentation Standards

Every command implementation located in the `commands/` directory **must** include a standardized header. This header serves as both a reference for users and a technical guide for other developers.

The header must contain the following four specific fields:

### 1. `# The command`
**The exact CLI signature.**
- **Purpose:** Defines how the user interacts with the command from the terminal.
- **Example:** `# The command: pit branch [<name>]`

### 2. `# What it does`
**A high-level description of user-facing behavior.**
- **Purpose:** Explains the command's functionality in plain English.
- **Example:** `# What it does: Lists, creates, or deletes branches to manage independent lines of development.`

### 3. `# How it does`
**A technical breakdown of repository interaction.**
- **Purpose:** Details how the command reads from or writes to the `.pit` directory and the working filesystem.
- **Example:** `# How it does: It scans the 'refs/heads' directory to list branches. For branch creation, it retrieves the current HEAD hash and writes it to a new file in the refs hierarchy.`

### 4. `# What data structure it uses`
**An explicit mention of data structures and their rationale.**
- **Purpose:** Identifies the algorithmic approach (e.g., Sets, Dictionaries, Lists) and explains why that specific structure was chosen (e.g., O(1) time complexity, maintaining insertion order, or ensuring uniqueness).
- **Example:** `# What data structure it uses: Set (for efficient O(1) lookup of unique branch names) and Dictionary (to map branch names to commit hashes).`

---

## Technical Guidelines

- **Core Technology:** Use only Python standard libraries unless explicitly approved.
- **Path Handling:** To ensure cross-platform compatibility (Windows, macOS, Linux), always use:
  - `os.path.join()` for joining paths.
  - `os.path.normpath()` for path consistency.
  - `os.path.normcase()` for case-insensitive filesystem support.
- **Safety First:** Commands should be non-destructive by default. Always implement a "Dry Run" or "Force" mechanism for operations that modify or delete working tree files.
- **Code Style:** Follow clean coding practices. Avoid redundant comments within the logic, but ensure the mandatory header is exhaustive.

## Submission Process

1. **Feature Branch:** Create a dedicated branch for your feature or fix.
2. **Implementation:** Ensure your new command follows the documentation header format exactly.
3. **Verification:** Test your changes across different directory depths and OS environments if possible.
4. **Pull Request:** Provide a summary of your changes and include screenshots of the command's output in various modes (e.g., default vs. force).

We appreciate your help in making Pit a better tool for everyone!
