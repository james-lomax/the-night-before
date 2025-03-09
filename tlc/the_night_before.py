#!/usr/bin/env python3

import argparse
import datetime
import os
import random
import re
import subprocess
import sys
from typing import List, Tuple


def is_git_repo() -> bool:
    """Check if the current directory is a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_commits_during_work_hours() -> List[Tuple[str, datetime.datetime]]:
    """
    Get all commits that were made during work hours (9am to 7pm Monday to Friday).
    Returns a list of tuples (commit_hash, commit_datetime).
    """
    commits = []
    
    # Get all commits with their timestamp
    result = subprocess.run(
        ["git", "log", "--format=%H %ad", "--date=iso"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
            
        parts = line.split(" ")
        commit_hash = parts[0]
        
        # Parse the date
        date_str = " ".join(parts[1:])
        # Handle the timezone part
        date_str = re.sub(r' [+-]\d{4}$', '', date_str)
        commit_date = datetime.datetime.fromisoformat(date_str)
        
        # Check if the commit was during work hours (9am to 7pm) on a weekday (Monday=0, Friday=4)
        if (
            0 <= commit_date.weekday() <= 4 and  # Monday to Friday
            9 <= commit_date.hour < 19  # 9am to 7pm
        ):
            commits.append((commit_hash, commit_date))
    
    return commits


def generate_night_before_time(original_time: datetime.datetime) -> datetime.datetime:
    """
    Generate a time the night before between 10pm and 3am.
    If the original commit was on Monday-Friday, use the previous evening.
    If it was on a weekend, keep the same day but change the time.
    """
    weekday = original_time.weekday()
    
    # If the commit was made on Monday to Friday, move it to the previous evening
    if 0 <= weekday <= 4:  # Monday to Friday
        # Get the day before
        new_date = original_time - datetime.timedelta(days=1)
    else:
        # For weekend commits, keep the same day
        new_date = original_time
    
    # Set a random time between 10pm and 3am
    hour = random.randint(22, 27) % 24  # 22, 23, 0, 1, 2, 3
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return new_date.replace(hour=hour, minute=minute, second=second)


def format_git_date(dt: datetime.datetime) -> str:
    """Format a datetime object as a git date string."""
    # Format: "Fri Jan 2 21:38:53 2009 -0800"
    # Get timezone offset
    offset = dt.strftime("%z")
    offset_hours = offset[:3]
    offset_minutes = offset[3:]
    formatted_offset = f"{offset_hours}{offset_minutes}"
    
    return dt.strftime(f"%a %b %-d %H:%M:%S %Y {formatted_offset}")


def generate_filter_branch_command(commits_to_fix: List[Tuple[str, datetime.datetime, datetime.datetime]]) -> str:
    """
    Generate the git filter-branch command to fix the commit timestamps.
    
    Args:
        commits_to_fix: List of tuples (commit_hash, original_datetime, new_datetime)
    
    Returns:
        The git filter-branch command as a string
    """
    env_filter = 'export GIT_COMMITTER_NAME="$GIT_COMMITTER_NAME"\n'
    env_filter += 'export GIT_COMMITTER_EMAIL="$GIT_COMMITTER_EMAIL"\n'
    env_filter += 'export GIT_AUTHOR_NAME="$GIT_AUTHOR_NAME"\n'
    env_filter += 'export GIT_AUTHOR_EMAIL="$GIT_AUTHOR_EMAIL"\n\n'
    
    for commit_hash, _, new_time in commits_to_fix:
        new_date_str = format_git_date(new_time)
        env_filter += f'if [ $GIT_COMMIT = {commit_hash} ]\nthen\n'
        env_filter += f'    export GIT_AUTHOR_DATE="{new_date_str}"\n'
        env_filter += f'    export GIT_COMMITTER_DATE="{new_date_str}"\n'
        env_filter += 'fi\n\n'
    
    command = [
        "git", "filter-branch", "--force", "--env-filter", env_filter, "--", "--all"
    ]
    
    return " ".join(command)


def fix_commit_times(dry_run: bool = False) -> None:
    """
    Fix commit times by changing work-hour commits to night-before times.
    
    Args:
        dry_run: If True, only print what would be done without making changes
    """
    if not is_git_repo():
        print("Error: Current directory is not a git repository")
        sys.exit(1)
    
    # Get all commits during work hours
    work_hour_commits = get_commits_during_work_hours()
    
    if not work_hour_commits:
        print("No commits found during work hours (9am-7pm, Monday-Friday).")
        return
    
    print(f"Found {len(work_hour_commits)} commits during work hours:")
    
    # Generate new times for each commit
    commits_to_fix = []
    for commit_hash, original_time in work_hour_commits:
        new_time = generate_night_before_time(original_time)
        commits_to_fix.append((commit_hash, original_time, new_time))
        
        # Get the commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%s", commit_hash],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        commit_msg = result.stdout.strip()
        
        print(f"  {commit_hash[:8]} - '{commit_msg}'")
        print(f"    From: {original_time.strftime('%a %b %d %H:%M:%S %Y')}")
        print(f"    To:   {new_time.strftime('%a %b %d %H:%M:%S %Y')}")
        print()
    
    # Generate the git filter-branch command
    filter_branch_command = generate_filter_branch_command(commits_to_fix)
    
    if dry_run:
        print("Dry run: The following command would be executed:")
        print(filter_branch_command)
        return
    
    # Ask for confirmation
    print("WARNING: This will rewrite git history. It's not recommended on public repositories.")
    response = input("Do you want to proceed? [y/N] ").strip().lower()
    
    if response != 'y':
        print("Operation cancelled.")
        return
    
    # Execute the command
    print("Updating commit timestamps...")
    
    try:
        # Run the filter-branch command
        subprocess.run(
            filter_branch_command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print("Commit timestamps updated successfully!")
        print("Note: You may need to force push to update remote repositories.")
    except subprocess.CalledProcessError as e:
        print(f"Error updating commit timestamps: {e}")
        print(f"Error details: {e.stderr}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Modify git commit timestamps to make it look like you worked outside business hours."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Fix commit timestamps")
    
    # Dry-run command
    dry_run_parser = subparsers.add_parser(
        "dry-run", help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    if args.command == "fix":
        fix_commit_times(dry_run=False)
    elif args.command == "dry-run":
        fix_commit_times(dry_run=True)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()