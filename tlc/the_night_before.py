#!/usr/bin/env python3
import os
import sys
import subprocess
import re
import argparse
import datetime
import random
from pathlib import Path
from jinja2 import Template
from typing import List, Dict, Optional, Tuple, Any


# Default configuration
DEFAULT_WORK_HOURS = (8, 19)  # 8am to 7pm
DEFAULT_NIGHT_HOURS = (20, 5)  # 8pm to 5am
DEFAULT_SKIP_WEEKENDS = True
DEFAULT_MIN_COMMIT_SPACING = 10  # minutes


class GitCommit:
    def __init__(self, hash: str, date: datetime.datetime, new_date: Optional[datetime.datetime] = None):
        self.hash = hash
        self.date = date
        self.new_date = new_date

    def __repr__(self) -> str:
        return f"GitCommit(hash='{self.hash}', date='{self.date}', new_date='{self.new_date}')"


class GitRepository:
    def __init__(self, path: str = "."):
        self.path = path
        if not self._is_git_repo():
            raise ValueError(f"Not a git repository: {path}")
        
    def _is_git_repo(self) -> bool:
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _get_user_email(self) -> str:
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return result.stdout.strip()
    
    def get_commits(self) -> List[GitCommit]:
        user_email = self._get_user_email()
        result = subprocess.run(
            ["git", "log", "--format=%H|%aI|%cI|%ae", "--date=iso-strict"],
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            parts = line.split('|')
            if len(parts) < 4:
                continue
                
            commit_hash, author_date, committer_date, author_email = parts
            
            # Only process commits by the current user
            if author_email.strip() != user_email:
                continue
                
            # Use author date for consistency
            date = parse_git_date(author_date)
            commits.append(GitCommit(commit_hash, date))
            
        return commits
    
    def install_pre_push_hook(self) -> None:
        hooks_dir = os.path.join(self.path, ".git", "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        
        hook_path = os.path.join(hooks_dir, "pre-push")
        hook_content = """#!/bin/sh
# pre-push hook to prevent pushing commits made during work hours

if ! command -v the-night-before &> /dev/null; then
    echo "the-night-before tool not found. Please install it first."
    exit 1
fi

# Check for commits during work hours
if ! the-night-before check; then
    echo "Push rejected: Commits during work hours detected."
    echo "Run 'the-night-before fix' to fix the commit times."
    exit 1
fi

exit 0
"""
        
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        
        os.chmod(hook_path, 0o755)  # Make executable
        print(f"Pre-push hook installed at {hook_path}")


def parse_git_date(date_str: str) -> datetime.datetime:
    """Parse git date strings in various formats."""
    # Try ISO 8601 format first
    try:
        return datetime.datetime.fromisoformat(date_str)
    except ValueError:
        pass
    
    # Try RFC 2822 format
    try:
        # Example: "Mon, 10 Mar 2025 16:08:59 +0000"
        import email.utils
        time_tuple = email.utils.parsedate_tz(date_str)
        if time_tuple:
            return datetime.datetime.fromtimestamp(email.utils.mktime_tz(time_tuple))
    except Exception:
        pass
    
    # Fall back to a more generic approach
    try:
        # Using datetime's parser as a last resort
        return datetime.datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
    except ValueError:
        raise ValueError(f"Unable to parse git date: {date_str}")


def is_workday(date: datetime.datetime, skip_weekends: bool = True) -> bool:
    """Check if the given date is a workday (not a weekend)."""
    if not skip_weekends:
        return True
    
    # 0 = Monday, 6 = Sunday in Python's datetime
    return date.weekday() < 5  # Monday to Friday


def is_work_hours(date: datetime.datetime, work_hours: Tuple[int, int]) -> bool:
    """Check if the given time falls within work hours."""
    work_start, work_end = work_hours
    hour = date.hour
    
    # Handle work hours spanning midnight
    if work_start < work_end:
        return work_start <= hour < work_end
    else:
        return hour >= work_start or hour < work_end


def get_commits_during_work_hours(
    commits: List[GitCommit], 
    work_hours: Tuple[int, int] = DEFAULT_WORK_HOURS,
    skip_weekends: bool = DEFAULT_SKIP_WEEKENDS
) -> List[GitCommit]:
    """Filter commits made during work hours."""
    work_hour_commits = []
    
    for commit in commits:
        if is_workday(commit.date, skip_weekends) and is_work_hours(commit.date, work_hours):
            work_hour_commits.append(commit)
    
    return work_hour_commits


def generate_night_before_time(
    commit_date: datetime.datetime,
    night_hours: Tuple[int, int] = DEFAULT_NIGHT_HOURS,
    min_spacing: int = DEFAULT_MIN_COMMIT_SPACING,
    previous_date: Optional[datetime.datetime] = None
) -> datetime.datetime:
    """
    Generate a timestamp for the night before the commit.
    
    Args:
        commit_date: Original commit datetime
        night_hours: Tuple of (start_hour, end_hour) for night hours
        min_spacing: Minimum minutes between commits
        previous_date: Previous commit's adjusted date (if any)
        
    Returns:
        New datetime for the commit
    """
    night_start, night_end = night_hours
    
    # Get the day before
    day_before = commit_date.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=1)
    
    # Set the start time to night_start on the day before
    start_time = day_before.replace(hour=night_start, minute=0, second=0, microsecond=0)
    
    # Handle night hours spanning midnight
    if night_end < night_start:
        end_time = day_before.replace(hour=night_end, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    else:
        end_time = day_before.replace(hour=night_end, minute=0, second=0, microsecond=0)
    
    # Adjust start_time if we have a previous commit's adjusted date
    if previous_date:
        min_start_time = previous_date + datetime.timedelta(minutes=min_spacing)
        if min_start_time > start_time:
            if min_start_time >= end_time:
                raise ValueError(
                    f"Cannot satisfy minimum spacing constraint of {min_spacing} minutes between commits. "
                    f"Previous commit at {previous_date}, cannot find suitable time before {end_time}."
                )
            start_time = min_start_time
    
    # Calculate available minutes between start and end time
    available_minutes = int((end_time - start_time).total_seconds() / 60)
    
    if available_minutes <= 0:
        raise ValueError(
            f"No available time in night hours ({night_start}:00-{night_end}:00) for commit. "
            f"Start time: {start_time}, End time: {end_time}"
        )
    
    # Pick a random minute within the available range, preserving original timezone
    random_minutes = random.randint(0, available_minutes)
    new_date = start_time + datetime.timedelta(minutes=random_minutes)
    
    # Preserve the original timezone
    if commit_date.tzinfo:
        new_date = new_date.replace(tzinfo=commit_date.tzinfo)
        
    return new_date


def assign_night_before_dates(
    commits: List[GitCommit],
    night_hours: Tuple[int, int] = DEFAULT_NIGHT_HOURS,
    min_spacing: int = DEFAULT_MIN_COMMIT_SPACING
) -> List[GitCommit]:
    """
    Assign night-before timestamps to the commits, ensuring minimum spacing.
    
    Args:
        commits: List of commits to fix
        night_hours: Tuple of (start_hour, end_hour) for night hours
        min_spacing: Minimum minutes between commits
        
    Returns:
        List of commits with new_date fields assigned
    """
    # Sort commits by date, oldest first
    sorted_commits = sorted(commits, key=lambda c: c.date)
    
    # Clone the list to avoid modifying the input
    result_commits = []
    previous_date = None
    
    for commit in sorted_commits:
        new_date = generate_night_before_time(
            commit.date, 
            night_hours, 
            min_spacing,
            previous_date
        )
        
        result_commits.append(GitCommit(commit.hash, commit.date, new_date))
        previous_date = new_date
        
    return result_commits


def format_git_date(dt: datetime.datetime) -> str:
    """Format a datetime in the ISO 8601 format that Git expects."""
    if not dt.tzinfo:
        # Use local timezone if none provided
        dt = dt.astimezone()
    return dt.isoformat()


def generate_filter_branch_command(commits: List[GitCommit]) -> str:
    """
    Generate the git filter-branch command to update commit timestamps.
    
    Args:
        commits: List of commits with new_date fields assigned
        
    Returns:
        The git filter-branch command as a string
    """
    template_str = """git filter-branch -f --env-filter \\
    '{% for commit in commits_to_fix %}
    if [ $GIT_COMMIT = {{ commit.hash }} ]
     then
         export GIT_AUTHOR_DATE="{{ commit.new_date }}"
         export GIT_COMMITTER_DATE="{{ commit.new_date }}"
     fi{% endfor %}'"""
    
    template = Template(template_str)
    
    # Format the dates for the template
    commits_to_fix = []
    for commit in commits:
        if commit.new_date:
            commits_to_fix.append({
                'hash': commit.hash,
                'new_date': format_git_date(commit.new_date)
            })
    
    return template.render(commits_to_fix=commits_to_fix)


def check_command(args: argparse.Namespace) -> int:
    """Check if there are commits during work hours."""
    try:
        repo = GitRepository(args.repo_path)
        commits = repo.get_commits()
        work_hour_commits = get_commits_during_work_hours(
            commits, 
            args.work_hours,
            args.skip_weekends
        )
        
        if work_hour_commits:
            print(f"Found commits during work hours ({args.work_hours[0]}am-{args.work_hours[1]}pm):")
            for commit in work_hour_commits:
                print(f"  {commit.hash[:8]} - {commit.date.strftime('%Y-%m-%d %H:%M:%S')}")
            print("\nUse 'the-night-before fix' to update these commit times.")
            return 1
        else:
            print("No commits during work hours found.")
            return 0
    except Exception as e:
        print(f"Error in check command: {e}")
        return 1


def install_git_hooks_command(args: argparse.Namespace) -> int:
    """Install git pre-push hooks."""
    try:
        repo = GitRepository(args.repo_path)
        repo.install_pre_push_hook()
        return 0
    except Exception as e:
        print(f"Error installing git hooks: {e}")
        return 1


def dry_run_command(args: argparse.Namespace) -> int:
    """Perform a dry run of the fix command."""
    try:
        repo = GitRepository(args.repo_path)
        commits = repo.get_commits()
        work_hour_commits = get_commits_during_work_hours(
            commits, 
            args.work_hours,
            args.skip_weekends
        )
        
        if not work_hour_commits:
            print("No commits during work hours found.")
            return 0
        
        print(f"Found {len(work_hour_commits)} commits during work hours.")
        print("Dry run - would fix these commits:")
        
        fixed_commits = assign_night_before_dates(
            work_hour_commits,
            args.night_hours,
            args.min_spacing
        )
        
        for commit in fixed_commits:
            print(f"  {commit.hash[:8]} - Original: {commit.date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"             -> New date: {commit.new_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\nCommand that would be run:")
        command = generate_filter_branch_command(fixed_commits)
        print(command)
        
        return 0
    except Exception as e:
        print(f"Error in dry run: {e}")
        return 1


def fix_command(args: argparse.Namespace) -> int:
    """Fix commit timestamps to be outside work hours."""
    try:
        repo = GitRepository(args.repo_path)
        commits = repo.get_commits()
        work_hour_commits = get_commits_during_work_hours(
            commits, 
            args.work_hours,
            args.skip_weekends
        )
        
        if not work_hour_commits:
            print("No commits during work hours found.")
            return 0
        
        print(f"Found {len(work_hour_commits)} commits during work hours.")
        
        fixed_commits = assign_night_before_dates(
            work_hour_commits,
            args.night_hours,
            args.min_spacing
        )
        
        for commit in fixed_commits:
            print(f"  {commit.hash[:8]} - Original: {commit.date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"             -> New date: {commit.new_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        command = generate_filter_branch_command(fixed_commits)
        print("\nThe following command will be executed:")
        print(command)
        
        if not args.yes:
            confirmation = input("\nProceed with rewriting history? (y/N): ")
            if confirmation.lower() != 'y':
                print("Operation cancelled.")
                return 0
        
        # Execute the command
        print("\nExecuting filter-branch command...")
        result = subprocess.run(
            command,
            cwd=repo.path,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error executing filter-branch command: {result.stderr}")
            return 1
        
        print("Successfully updated commit timestamps.")
        print("NOTE: You may need to force push your changes with 'git push -f'")
        return 0
    except Exception as e:
        print(f"Error fixing commits: {e}")
        return 1


def parse_hour_range(value: str) -> Tuple[int, int]:
    """Parse a range of hours as 'start-end'."""
    try:
        start, end = map(int, value.split('-'))
        return (start, end)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid hour range: {value}. Expected format: 'start-end'")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Modify git commit timestamps to appear as if you worked outside business hours."
    )
    
    # Common arguments
    parser.add_argument(
        '--repo-path', 
        type=str, 
        default=".", 
        help="Path to the git repository (default: current directory)"
    )
    parser.add_argument(
        '--work-hours', 
        type=parse_hour_range, 
        default=f"{DEFAULT_WORK_HOURS[0]}-{DEFAULT_WORK_HOURS[1]}", 
        help=f"Work hours as 'start-end' in 24h format (default: {DEFAULT_WORK_HOURS[0]}-{DEFAULT_WORK_HOURS[1]})"
    )
    parser.add_argument(
        '--night-hours', 
        type=parse_hour_range, 
        default=f"{DEFAULT_NIGHT_HOURS[0]}-{DEFAULT_NIGHT_HOURS[1]}", 
        help=f"Night hours as 'start-end' in 24h format (default: {DEFAULT_NIGHT_HOURS[0]}-{DEFAULT_NIGHT_HOURS[1]})"
    )
    parser.add_argument(
        '--skip-weekends', 
        action='store_true', 
        default=DEFAULT_SKIP_WEEKENDS,
        help="Skip checking commits made on weekends (default: True)"
    )
    parser.add_argument(
        '--no-skip-weekends', 
        action='store_false', 
        dest='skip_weekends',
        help="Check commits made on weekends"
    )
    parser.add_argument(
        '--min-spacing', 
        type=int, 
        default=DEFAULT_MIN_COMMIT_SPACING,
        help=f"Minimum spacing between commits in minutes (default: {DEFAULT_MIN_COMMIT_SPACING})"
    )
    parser.add_argument(
        '-y', '--yes', 
        action='store_true', 
        help="Skip confirmation prompt"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check for commits during work hours')
    
    # Install git hooks command
    hooks_parser = subparsers.add_parser('install-git-hooks', help='Install git pre-push hooks')
    
    # Fix command
    fix_parser = subparsers.add_parser('fix', help='Fix commit timestamps to be outside work hours')
    
    # Dry run command
    dry_run_parser = subparsers.add_parser('dry-run', help='Show what would be done without making changes')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Convert string arguments to proper types when needed
    if isinstance(args.work_hours, str):
        args.work_hours = parse_hour_range(args.work_hours)
    if isinstance(args.night_hours, str):
        args.night_hours = parse_hour_range(args.night_hours)
    
    # Execute the appropriate command
    if args.command == 'check':
        return check_command(args)
    elif args.command == 'install-git-hooks':
        return install_git_hooks_command(args)
    elif args.command == 'fix':
        return fix_command(args)
    elif args.command == 'dry-run':
        return dry_run_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())