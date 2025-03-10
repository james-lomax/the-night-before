# The Night Before

A tool that modifies git commit timestamps to make it appear as if you worked outside business hours. This is useful for open-source contributions that you may have made during work hours.

## Installation

```bash
# Install the-night-before with uvx
uv tool install .

# Install the pre-push hook to prevent commits during work hours being pushed to a remote repository
the-night-before install-git-hooks
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

To modify the timestamps of all commits from the last 24 hours to be the night before:

```bash
the-night-before fix
```

This will:
1. List all commits from the last 24 hours
2. Show you the original and new timestamps 
3. Ask for confirmation before making changes
4. Modify the commit timestamps to a random times between 10pm and 3am the night before

## Warning

This tool rewrites git history. Use with caution, especially on public repositories or branches that others may have pulled from. After running this tool, you may need to force push your changes.

## Development

This tool was built with [the-last-compiler](https://github.com/james-lomax/the-last-compiler).

To recompile:

```bash
tlc compile the-night-before.md
```
