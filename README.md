# The Night Before

A tool that modifies git commit timestamps to make it appear as if you worked outside business hours. This is useful for open-source contributions that you may have made during work hours.

## Installation

```bash
uv tool install .
```

## Usage

First, navigate to your git repository:

```bash
cd /path/to/your/repo
```

### List commits made during work hours

To see what commits would be modified and preview the changes without making them:

```bash
the-night-before dry-run
```

### Fix commit timestamps

To modify the timestamps of commits made during work hours (9am-7pm, Monday-Friday):

```bash
the-night-before fix
```

This will:
1. Identify all commits made during work hours
2. Show you the original and new timestamps 
3. Ask for confirmation before making changes
4. Modify the commit timestamps to a random time between 10pm and 3am the night before

## Warning

This tool rewrites git history. Use with caution, especially on public repositories or branches that others may have pulled from. After running this tool, you may need to force push your changes.