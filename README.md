# Pit - A Simple Version Control System

Pit is a simplified version control system built from scratch in Python. It is designed as an educational project to copy version control systems like Git.

Pit draws heavy inspiration from Git and is basically a recreation of Git in Python (Pit)

Core Concepts

Pit is built on the same three fundamental ideas that power Git:

1. **Content-Addressable Storage (Blobs):** The content of every file is stored in an object called a "blob." The name of this object is not a filename, but the SHA-1 hash of its content. This means identical files are only stored once, and the integrity of the data is guaranteed if the content changes, its hash (and thus its name) will change.
2. **Hierarchical Trees (Merkle Trees):** The directory structure is captured in "tree" objects. A tree contains pointers to blobs (for files) and other trees (for subdirectories). Each tree is also identified by its SHA-1 hash, which is derived from the contents of the tree (the list of its children's hashes). This creates a Merkle tree, where a single hash at the top can verify the integrity of the entire project's file structure.
3. **Historical Snapshots (Commits):** A "commit" object represents a snapshot of the entire project at a single point in time. It contains a pointer to the root tree object, metadata (author, message, timestamp), and pointers to one or more parent commits. This chain of parent pointers forms the project's history as a Directed Acyclic Graph (DAG).

## Features

Pit implements the following core commands:

* `pit init`: Initialize a new, empty repository.
* `pit config`: Set user configuration (name and email) for commits.
* `pit add <file>`: Stage changes by hashing the file content and updating the index.
* `pit commit -m "<message>"`: Create a permanent snapshot of the staged changes.
* `pit status`: Show the status of the working directory and staging area.
* `pit log`: Display the commit history by traversing the commit graph.
* `pit branch [<name>]`: List all branches or create a new one.
* `pit checkout <branch>`: Switch the current working branch.
* `pit diff [--staged]`: Show line-by-line changes between the working directory, index, and HEAD.
* `pit merge <branch>`: Create a merge commit to join two branches (note: does not handle content conflicts).
* `pit reset <file>`: Unstage a file by removing it from the index.

## Project Structure

The project is organized into two main layers:

* `pit.py`: The main entry point and command-line argument parser/dispatcher.
* `commands/`: Each file implements the high-level logic for a user-facing command.
* `utils/`: These modules contain the core data structures and logic for managing the object database, repository state, and other fundamental operations.

## How to Run

The project is fully containerized using Docker, providing a consistent and easy-to-use environment for running the application and its test suite.

### Prerequisites

* Docker installed and running on your machine.

### 1. Build the Docker Image

Navigate to the project's root directory (where the `Dockerfile` is located) and run the following command to build the image:

```
docker build -t pit-env .
```

### 2. Run the Docker Image

**On Linux:**

```
docker run -it --rm -v "$(pwd)":/workspace pit-env
```

**On Windows:**

```
docker run -it --rm -v "${PWD}}":/workspace pit-env
```

`<i>`If you do not have docker you can always run the commands in the manner of `</i>`

```
python3 <path to pit project>/pit/pit-project/pit.py
```

# Testing

The `full_test.sh` script provides a comprehensive test that exercises all of the major features of Pit

## Run it using

```
chmod +x full_test.sh
/full_test.sh
```

## What this test covers

* **`init`** : Used in [TEST 1]
* **`config`** : Used in [TEST 1]
* **`add`** : Used in [TEST 2], [TEST 3], [TEST 4], and [TEST 5]
* **`commit`** : Used in [TEST 2], [TEST 3], and [TEST 4]
* **`log`** : Used in [TEST 2], [TEST 3], [TEST 4], and [TEST 6]
* **`branch`** : Used in [TEST 3]
* **`checkout`** : Used in [TEST 3], [TEST 4], [TEST 5], and [TEST 6]
* **`diff`** : The `--staged` version is used in [TEST 5]
* **`reset`** : Used in [TEST 5]
* **`merge`** : Used in [TEST 6]
* **`status`** : Used in [TEST 5]
