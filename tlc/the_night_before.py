import argparse
import os
import subprocess
import sys
import random
from datetime import datetime, timedelta


def is_work_hours(timestamp):
    """Check if a timestamp is during work hours (9am-7pm Monday-Friday)."""
    dt = datetime.fromtimestamp(int(timestamp))
    is_weekday = dt.weekday() < 5  # Monday-Friday
    is_work_time = 9 <= dt.hour < 19  # 9am-7pm
    return is_weekday and is_work_time


def get_night_before_time(timestamp):
    """Generate a time from the night before (10pm-3am)."""
    dt = datetime.fromtimestamp(int(timestamp))
    
    # If it's Monday-Friday, go back to the previous night
    if dt.weekday() < 5:
        dt = dt - timedelta(days=1)
    
    # Set hour between 10pm and 3am
    hour = random.randint(22, 27) % 24  # 22, 23, 0, 1, 2, 3
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return dt.replace(hour=hour, minute=minute, second=second)


def get_work_hour_commits():
    """Get all commits made during work hours."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H %at"],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository or git command failed.")
        sys.exit(1)
    
    work_hour_commits = []
    
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
            
        parts = line.split()
        if len(parts) >= 2:
            commit_hash = parts[0]
            timestamp = parts[1]
            
            if is_work_hours(timestamp):
                work_hour_commits.append((commit_hash, int(timestamp)))
    
    return work_hour_commits


def fix_commit_times(commits, dry_run=False):
    """Fix commit times to be during non-work hours."""
    if not commits:
        print("No work-hour commits found. All good!")
        return True
    
    print(f"Found {len(commits)} commits made during work hours:")
    
    # Sort commits by timestamp (oldest first)
    commits.sort(key=lambda x: x[1])
    
    changes = []
    for commit_hash, timestamp in commits:
        dt_original = datetime.fromtimestamp(timestamp)
        dt_new = get_night_before_time(timestamp)
        
        changes.append({
            'commit_hash': commit_hash,
            'original_time': dt_original,
            'new_time': dt_new
        })
        
        print(f"  {commit_hash[:8]}: {dt_original} -> {dt_new}")
    
    if dry_run:
        print("\nDRY RUN: No changes made.")
        return True
        
    confirm = input("\nDo you want to modify these commit timestamps? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return False
    
    print("\nModifying commit timestamps...")
    
    env_filter_parts = []
    
    for change in changes:
        commit_hash = change['commit_hash']
        new_time = change['new_time'].strftime("%a %b %d %H:%M:%S %Y %z")
        
        # Format without timezone if not present
        if not "%z" in new_time:
            new_time = change['new_time'].strftime("%a %b %d %H:%M:%S %Y")
            
        env_filter_parts.append(f"if [ $GIT_COMMIT = {commit_hash} ]\nthen\n    export GIT_AUTHOR_DATE=\"{new_time}\"\n    export GIT_COMMITTER_DATE=\"{new_time}\"\nfi")
    
    env_filter = "'" + "\nelif ".join(env_filter_parts) + "'"
    
    filter_command = ["git", "filter-branch", "--env-filter", env_filter, "--force"]
    
    print(f"Running: {' '.join(filter_command)}")
    
    try:
        subprocess.run(filter_command, check=True)
        print("Commit timestamps successfully modified!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error modifying commit timestamps: {e}")
        return False


def check_commits():
    """Check if any commits are made during work hours."""
    work_hour_commits = get_work_hour_commits()
    
    if work_hour_commits:
        print(f"Error: Found {len(work_hour_commits)} commits made during work hours.")
        print("Run 'the-night-before fix' to fix these commits.")
        return False
    else:
        print("No work-hour commits found. All good!")
        return True


def install_git_hooks():
    """Install git pre-push hook."""
    hook_path = os.path.join('.git', 'hooks', 'pre-push')
    
    hook_content = """#!/bin/sh
# Pre-push hook to check for work-hour commits
the-night-before check
if [ $? -ne 0 ]; then
    echo "Error: Found commits made during work hours."
    echo "Run 'the-night-before fix' to fix these commits before pushing."
    exit 1
fi
"""
    
    try:
        # Ensure hooks directory exists
        os.makedirs(os.path.dirname(hook_path), exist_ok=True)
        
        # Create the hook file
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        
        # Make the hook executable
        os.chmod(hook_path, 0o755)
        
        print(f"Git pre-push hook installed at {hook_path}")
        return True
    except Exception as e:
        print(f"Error installing git hook: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Modify git commit timestamps to make it look like you committed during non-work hours."
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    fix_parser = subparsers.add_parser('fix', help='Fix work-hour commit timestamps')
    
    check_parser = subparsers.add_parser('check', help='Check for work-hour commits')
    
    install_parser = subparsers.add_parser('install-git-hooks', help='Install git pre-push hooks')
    
    dry_run_parser = subparsers.add_parser('dry-run', help='Show what changes would be made without making them')
    
    args = parser.parse_args()
    
    if args.command == 'fix':
        commits = get_work_hour_commits()
        success = fix_commit_times(commits)
        sys.exit(0 if success else 1)
    
    elif args.command == 'check':
        success = check_commits()
        sys.exit(0 if success else 1)
    
    elif args.command == 'install-git-hooks':
        success = install_git_hooks()
        sys.exit(0 if success else 1)
    
    elif args.command == 'dry-run':
        commits = get_work_hour_commits()
        fix_commit_times(commits, dry_run=True)
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()