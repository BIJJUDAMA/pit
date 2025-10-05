# What it does: Provides helper functions for comparing repository states and generating line-by-line diff reports.
# What data structure it uses: Dictionary (for states), Set (for efficient O(N) path comparisons), List (of file lines for the diffing algorithm).
import difflib

def compare_states(state1, state2): # Compares two states represented as {path: hash} dictionaries
    
    paths1 = set(state1.keys())
    paths2 = set(state2.keys())

    added = sorted(list(paths2 - paths1))
    deleted = sorted(list(paths1 - paths2))

    modified = []
    for path in sorted(list(paths1 & paths2)):
        if state1[path] != state2[path]:
            modified.append(path)

    return {'added': added, 'deleted': deleted, 'modified': modified}

def get_diff_lines(content1, content2, from_file, to_file): #Generates unified diff lines between two contents
    
    content1_lines = content1.decode(errors='ignore').splitlines()
    content2_lines = content2.decode(errors='ignore').splitlines()

    diff = difflib.unified_diff(
        content1_lines,
        content2_lines,
        fromfile=from_file,
        tofile=to_file,
        lineterm='\\n'
    )

    return list(line + '\\n' for line in diff)