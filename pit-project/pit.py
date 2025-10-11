import argparse
from commands import (
    init, add, commit, log, status, config,
    branch, checkout, diff, merge, reset, revert  
)
# The main entry point for the Pit version control system
def main():
    # The main parser
    parser = argparse.ArgumentParser(description="Pit: A simple version control system.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Command: init
    init_parser = subparsers.add_parser("init", help="Initialize a new, empty repository.")
    init_parser.set_defaults(func=init.run)

    # Command: add
    add_parser = subparsers.add_parser("add", help="Add file contents to the index.")
    add_parser.add_argument("files", nargs="+", help="Files to add.")
    add_parser.set_defaults(func=add.run)

    # Command: commit
    commit_parser = subparsers.add_parser("commit", help="Record changes to the repository.")
    commit_parser.add_argument("-m", "--message", required=True, help="Commit message.")
    commit_parser.set_defaults(func=commit.run)

    # Command: log
    log_parser = subparsers.add_parser("log", help="Show commit logs.")
    log_parser.set_defaults(func=log.run)

    # Command: status
    status_parser = subparsers.add_parser("status", help="Show the working tree status.")
    status_parser.set_defaults(func=status.run)
    
    # Command: config
    config_parser = subparsers.add_parser("config", help="Set user name and email.")
    config_parser.add_argument("key", help="The configuration key (e.g., user.name).")
    config_parser.add_argument("value", help="The configuration value.")
    config_parser.set_defaults(func=config.run)

    # Command: branch
    branch_parser = subparsers.add_parser("branch", help="List or create branches.")
    branch_parser.add_argument("name", nargs="?", help="The name of the branch to create.")
    branch_parser.set_defaults(func=branch.run)
    
    # Command: checkout
    checkout_parser = subparsers.add_parser("checkout", help="Switch branches.")
    checkout_parser.add_argument("branch_name", help="The name of the branch to switch to.")
    checkout_parser.set_defaults(func=checkout.run)

    # Command: diff
    diff_parser = subparsers.add_parser("diff", help="Show changes between index and working tree.")
    diff_parser.add_argument("--staged", action="store_true", help="Show changes between the index and the last commit.")
    diff_parser.set_defaults(func=diff.run)

    # Command: merge
    merge_parser = subparsers.add_parser("merge", help="Merge a branch into the current branch.")
    merge_parser.add_argument("branch", help="The branch to merge.")
    merge_parser.set_defaults(func=merge.run)
    
    # Command: reset
    reset_parser = subparsers.add_parser("reset", help="Unstage files.")
    reset_parser.add_argument("files", nargs="+", help="Files to unstage from the index.")
    reset_parser.set_defaults(func=reset.run)

    # Command: revert
    revert_parser = subparsers.add_parser("revert", help="Revert an existing commit.")
    revert_parser.add_argument("commit_hash", help="The commit hash to revert.")
    revert_parser.set_defaults(func=revert.run)
    # Parse the arguments
    args = parser.parse_args()

    # If a command was specified, run its function
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

