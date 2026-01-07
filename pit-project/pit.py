import argparse
import sys
import shlex
from utils.config import read_config

from commands import (
    init, add, commit, log, status, config,
    branch, checkout, diff, merge, reset,
    revert, clean, stash, tag
    # remote, push, pull, clone
)

# The main entry point for the Pit version control system
def main():
    # Handle aliases
    if len(sys.argv) > 1:
        potential_alias = sys.argv[1]
        # Skip if it's a known command to avoid overhead/conflict, OR just always check config
        # The prompt says: "check the [alias] section of the config before parsing standard commands."
        # If I check config first, I can override standard commands maybe? 
        # Usually aliases shouldn't shadow commands, but checking config first is what was asked.
        # However, checking if it is NOT a known command first is safer to prevent accidental shadowing?
        # Prompt: "If the first argument is not a known command, check .pit/options (or config dictionary) for alias.<cmd>."
        
        # known commands list from the subparsers? subparsers are defined later.
        # I can list them manually or just try to load config.
        # Let's list known commands.
        known_commands = {
            "init", "add", "commit", "log", "status", "config",
            "branch", "checkout", "diff", "merge", "reset",
            "revert", "clean", "stash", "tag"
        }
        
        if potential_alias not in known_commands:
            cfg = read_config()
            if cfg.has_option('alias', potential_alias):
                alias_value = cfg.get('alias', potential_alias)
                # Split the alias value (e.g., "log --oneline")
                alias_args = shlex.split(alias_value)
                # Replace the alias in sys.argv
                sys.argv[1:2] = alias_args
                # sys.argv will be used by parse_args() automatically

    # The main parser
    parser = argparse.ArgumentParser(description="Pit: A simple version control system.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Command: init
    init_parser = subparsers.add_parser("init", help="Initialize a new, empty repository.")
    init_parser.set_defaults(func=init.run)

    # Command: add
    add_parser = subparsers.add_parser("add", help="Add file contents to the index.")
    add_parser.add_argument("files", nargs="*", help="Files to add.")
    add_parser.add_argument("-A", "--all", action="store_true", help="Add all files in the repository.")
    add_parser.set_defaults(func=add.run)

    # Command: commit
    commit_parser = subparsers.add_parser("commit", help="Record changes to the repository.")
    commit_parser.add_argument("-m", "--message", required=True, help="Commit message.")
    commit_parser.set_defaults(func=commit.run)

    # Command: log
    log_parser = subparsers.add_parser("log", help="Show commit logs.")
    log_parser.add_argument("--oneline", action="store_true", help="Show one commit per line.")
    log_parser.add_argument("--graph", action="store_true", help="Show ASCII graph of commit history.")
    log_parser.add_argument("--since", help="Show commits more recent than specific date.")
    log_parser.add_argument("--grep", help="Filter commits by message pattern.")
    log_parser.add_argument("--patch", "-p", action="store_true", help="Show patch for specified file.")
    log_parser.add_argument("file", nargs="?", help="Show only commits affecting specific file.")
    log_parser.add_argument("-n", "--max-count", type=int, help="Limit number of commits to show.")
    log_parser.set_defaults(func=log.run)

    # Command: status
    status_parser = subparsers.add_parser("status", help="Show the working tree status.")
    status_parser.set_defaults(func=status.run)

    # Command: config
    config_parser = subparsers.add_parser("config", help="Set configuration options (e.g., user.name, github.token).")
    config_parser.add_argument("key", help="The configuration key (e.g., user.name or github.token).")
    config_parser.add_argument("value", help="The configuration value.")
    config_parser.set_defaults(func=config.run)

    # Command: branch
    branch_parser = subparsers.add_parser("branch", help="List or create branches.")
    branch_parser.add_argument("name", nargs="?", help="The name of the branch to create.")
    branch_parser.set_defaults(func=branch.run)

    #Command: checkout
    checkout_parser = subparsers.add_parser("checkout", help="Switch branches or restore working tree files.")
    checkout_parser.add_argument("targets", nargs="+", help="Branch name to switch to, or file(s) to restore from index.")
    checkout_parser.add_argument("-b", "--branch", action="store_true", help="Create a new branch and switch to it.")
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

    # Command: clean
    clean_parser = subparsers.add_parser("clean", help="Remove untracked files from the working tree.")
    clean_parser.add_argument("-n", "--dry-run", action="store_true", dest="n", help="Show what would be removed.")
    clean_parser.add_argument("-f", "--force", action="store_true", dest="f", help="Force deletion of untracked files.")
    clean_parser.add_argument("-d", action="store_true", help="Remove untracked directories as well.")
    clean_parser.set_defaults(func=clean.run)

    # Command: stash
    stash_parser = subparsers.add_parser("stash", help="Stash the changes in a dirty working directory away.")
    stash_parser.add_argument("action", nargs="?", choices=["push", "list", "pop", "show", "drop", "clear"], default="push", help="The action to perform (push, list, pop, show, drop, clear)")
    stash_parser.add_argument("stash_arg", nargs="?", help="Stash index (e.g. stash@{0}) or message for push")
    stash_parser.set_defaults(func=stash.run)

    # # Command: remote
    # remote_parser = subparsers.add_parser("remote", help="Manage remote repositories (HTTPS only)")
    # remote_parser.add_argument("subcommand", help="Subcommand: add, remove, list, set-url")
    # remote_parser.add_argument("name", nargs="?", help="Remote name")
    # remote_parser.add_argument("url", nargs="?", help="HTTPS URL (e.g., https://github.com/user/repo.git)")
    # remote_parser.set_defaults(func=remote.run)

    # # Command: push
    # push_parser = subparsers.add_parser("push", help="Push to remote repository via HTTPS")
    # push_parser.add_argument("remote", help="Remote name")
    # push_parser.add_argument("branch", help="Branch to push")
    # push_parser.add_argument("-u", "--set-upstream", action="store_true",
    #                         help="Set upstream branch tracking")
    # push_parser.add_argument("-f", "--force", action="store_true",
    #                         help="Force push (overwrite remote)")
    # push_parser.set_defaults(func=push.run)

    # # Command: pull
    # pull_parser = subparsers.add_parser("pull", help="Fetch and integrate changes from remote")
    # pull_parser.add_argument("remote", help="Remote name")
    # pull_parser.add_argument("branch", help="Branch to pull")
    # pull_parser.set_defaults(func=pull.run)

    # # Command: clone
    # clone_parser = subparsers.add_parser("clone", help="Clone a repository into a new directory.")
    # clone_parser.add_argument("repository_url", help="The HTTPS URL of the repository to clone.")
    # clone_parser.add_argument("directory", nargs="?", help="The name of the directory to clone into.")
    # clone_parser.set_defaults(func=clone.run)

    # Command: tag
    tag_parser = subparsers.add_parser("tag", help="Create, list, delete or verify a tag object signed with GPG.")
    tag_parser.add_argument("name", nargs="?", help="The name of the tag to create.")
    tag_parser.set_defaults(func=tag.run)

    # Parse the arguments
    args = parser.parse_args()

    # If a command was specified, run its function
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()