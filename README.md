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

In your git repository you will see an error if you try to push commits with timestamps during work hours:

```bash
% git push -f
Found commits during work hours (8am-7pm):
  affe5ed3 - 2025-03-10 16:08:59

Use 'the-night-before fix' to update these commit times.
Push rejected: Commits during work hours detected.
Run 'the-night-before fix' to fix the commit times.
```

Fix the commits by modifying the author and commit timestamps for all the commits in the last 24 hours to be between 10pm and 3am:

```bash
the-night-before fix
```

## Warning

This tool dangerously rewrites git history. Use with caution, especially on public repositories or branches that others may have pulled from. After running this tool, you may need to force push your changes.

## Development

This tool was built with [the-last-compiler](https://github.com/james-lomax/the-last-compiler).

To recompile:

```bash
tlc compile the-night-before.md
```
