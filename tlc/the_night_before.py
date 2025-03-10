#!/usr/bin/env python3

import argparse
import datetime
import os
import random
import subprocess
import sys
from typing import List, Dict, Any, Optional

from jinja2 import Template

def run_git_command(command: List[str]) -> str:
    """Run a git command and return its output."""
    try:
        result = subprocess.run(
            ["git"] + command,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

def is_git_repository() -> bool:
    """Check if the current directory is a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False

def get_commits_last_24h() -> List[Dict[str, Any]]:
    """Get all commits from the last 24 hours."""
    since_time = datetime.datetime.now() - datetime.timedelta(days=1)
    since_str = since_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Get the commit hashes
    commit_hashes = run_git_command(["log", "--since", since_str, "--format=%H"]).splitlines()
    
    commits = []
    for commit_hash in commit_hashes:
        # Get the commit timestamp
        timestamp_str = run_git_command(["show", "-s", "--format=%at", commit_hash])
        timestamp = int(timestamp_str)
        commit_time = datetime.datetime.fromtimestamp(timestamp)
        
        commits.append({
            "hash": commit_hash,
            "time": commit_time,
            "timestamp": timestamp,
        })
    
    # Sort by timestamp
    commits.sort(key=lambda x: x["timestamp"])
    
    return commits

def is_work_hours(dt: datetime.datetime) -> bool:
    """Check if a datetime is during work hours (8am-7pm)."""
    return 8 <= dt.hour < 19

def find_commits_in_work_hours() -> List[Dict[str, Any]]:
    """Find all commits made during work hours in the last 24 hours."""
    commits = get_commits_last_24h()
    return [commit for commit in commits if is_work_hours(commit["time"])]

def generate_new_timestamps(commits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate new timestamps for commits, maintaining chronological order."""
    if not commits:
        return []
    
    # Find the night before
    now = datetime.datetime.now()
    night_start = datetime.datetime(
        now.year, now.month, now.day - 1, 22, 0, 0
    )  # 10pm last night
    night_end = datetime.datetime(
        now.year, now.month, now.day, 3, 0, 0
    )  # 3am this morning
    
    # Calculate available time in seconds
    total_seconds = (night_end - night_start).total_seconds()
    
    # Divide the time into chunks
    chunk_size = total_seconds / len(commits)
    
    # Update each commit with a new timestamp
    result = []
    for i, commit in enumerate(commits):
        # Define the chunk boundaries
        chunk_start = night_start + datetime.timedelta(seconds=i * chunk_size)
        chunk_end = night_start + datetime.timedelta(seconds=(i + 1) * chunk_size)
        
        # Choose a random time within the chunk, normally distributed around the middle
        chunk_middle = chunk_start + (chunk_end - chunk_start) / 2
        # Standard deviation of 1/6 of chunk size to keep most times within the chunk
        std_dev = chunk_size / 6
        
        # Generate random time
        random_seconds = random.normalvariate(
            (chunk_middle - chunk_start).total_seconds(), 
            std_dev
        )
        # Ensure we stay within the chunk
        random_seconds = max(0, min(random_seconds, chunk_size))
        
        new_time = chunk_start + datetime.timedelta(seconds=random_seconds)
        
        # Format for git (e.g., "Fri Jan 2 21:38:53 2009 -0800")
        timezone = datetime.datetime.now().astimezone().strftime("%z")
        timezone_formatted = f"{timezone[:3]}:{timezone[3:]}"
        new_date = new_time.strftime("%a %b %-d %H:%M:%S %Y ") + timezone_formatted
        
        result.append({
            **commit,
            "new_date": new_date,
            "new_time": new_time,
        })
    
    return result

def format_filter_branch_command(commits: List[Dict[str, Any]]) -> str:
    """Format the git filter-branch command using the jinja2 template."""
    template_str = """git filter-branch -f --env-filter \\
    '{% for commit in commits_to_fix %}
    if [ $GIT_COMMIT = {{ commit.hash }} ]
     then
         export GIT_AUTHOR_DATE="{{ commit.new_date }}"
         export GIT_COMMITTER_DATE="{{ commit.new_date }}"
     fi{% endfor %}'"""
    
    template = Template(template_str)
    return template.render(commits_to_fix=commits)

def cmd_check() -> bool:
    """Check if any commits are made in work hours."""
    work_hour_commits = find_commits_in_work_hours()
    
    if work_hour_commits:
        print("Found commits during work hours (8am-7pm):")
        for commit in work_hour_commits:
            hash_short = commit["hash"][:8]
            time_str = commit["time"].strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {hash_short} - {time_str}")
        print("\nUse 'the-night-before fix' to update these commit times.")
        return False
    else:
        print("No commits found during work hours.")
        return True

def cmd_install_git_hooks():
    """Install git pre-push hooks."""
    hooks_dir = ".git/hooks"
    
    # Ensure the hooks directory exists
    if not os.path.exists(hooks_dir):
        os.makedirs(hooks_dir)
    
    pre_push_path = os.path.join(hooks_dir, "pre-push")
    hook_content = """#!/bin/sh
# Pre-push hook to check for commits during work hours

the-night-before check
if [ $? -ne 0 ]; then
    echo "Push rejected: Commits during work hours detected."
    echo "Run 'the-night-before fix' to fix the commit times."
    exit 1
fi
"""
    
    with open(pre_push_path, "w") as f:
        f.write(hook_content)
    
    # Make the hook executable
    os.chmod(pre_push_path, 0o755)
    
    print("Git pre-push hook installed successfully.")

def cmd_fix(dry_run: bool = False):
    """Fix commits made during work hours."""
    all_commits = get_commits_last_24h()
    if not all_commits:
        print("No commits found in the last 24 hours.")
        return
    
    # Always fix all commits from the last 24 hours to maintain chronological order
    updated_commits = generate_new_timestamps(all_commits)
    
    print("Commits to update:")
    for commit in updated_commits:
        hash_short = commit["hash"][:8]
        old_time = commit["time"].strftime("%Y-%m-%d %H:%M:%S")
        new_time = commit["new_time"].strftime("%Y-%m-%d %H:%M:%S")
        
        if is_work_hours(commit["time"]):
            print(f"  {hash_short} - {old_time} => {new_time} (work hours fixed)")
        else:
            print(f"  {hash_short} - {old_time} => {new_time} (keeping chronological order)")
    
    filter_branch_cmd = format_filter_branch_command(updated_commits)
    
    print("\nCommand that will be executed:")
    print(filter_branch_cmd)
    
    if dry_run:
        print("\nDry run - no changes made.")
        return
    
    confirmation = input("\nProceed with these changes? (y/n): ").strip().lower()
    if confirmation == "y":
        # Execute the command
        try:
            subprocess.run(filter_branch_cmd, shell=True, check=True)
            print("Commit times updated successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error updating commit times: {e}")
            print("If you get an error about a previous filter-branch operation,")
            print("try running: git filter-branch -f")
    else:
        print("Operation cancelled.")

def main():
    """Main entry point for the script."""
    if not is_git_repository():
        print("Error: Current directory is not a git repository.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(
        description="Modify git commit timestamps to make them look like they were committed outside work hours."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # check command
    subparsers.add_parser("check", help="Check for commits during work hours")
    
    # install-git-hooks command
    subparsers.add_parser("install-git-hooks", help="Install git pre-push hooks")
    
    # fix command
    subparsers.add_parser("fix", help="Fix commit timestamps")
    
    # dry-run command
    subparsers.add_parser("dry-run", help="Show what would be changed without making changes")
    
    args = parser.parse_args()
    
    if args.command == "check":
        success = cmd_check()
        if not success:
            sys.exit(1)
    elif args.command == "install-git-hooks":
        cmd_install_git_hooks()
    elif args.command == "fix":
        cmd_fix()
    elif args.command == "dry-run":
        cmd_fix(dry_run=True)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()