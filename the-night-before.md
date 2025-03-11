# tlc/the_night_before.py

the-night-before is a python script which allows you to amend the time stamps in git commits as if you committed the night before, so it doesn't look like you're committing to open-source projects during work hours.

Work hours are defined as 8am-7pm by default, but should be configurable.

## Inputs

Current working directory should be a git repository.

## Outputs

No outputs, will simply update the git repository.

## Implementation

tlc/the_night_before.py will implement a main function, and we will add a script entry to the uv pyproject.toml file.

### Commands

```
the-night-before check
```

Checks if any commits authored by you are made in work hours and fails with a message to fix with `the-night-before fix` if so.

```
the-night-before install-git-hooks
```

Installs git pre-push hooks using `the-night-before check` to prevent commits being made during work hours being pushed to a remote repository.

```
the-night-before fix
```

This will list all commits authored by you which were made during work hours and amend the author and commit times for all of them to be the night before. For each commit made during work hours, the script will update the author and commit times to be a time picked between 8pm and 5am the previous night. The script will ensure it picks a time at least 10 minutes after the preceding commit (and as early as possible). If these two conditions cannot be satisfied, the script will fail.

The tool will print the source of the filter-repo script and get use confirmation before effecting the change.

```
the-night-before dry-run
```

This must print what git commands will be run by `the-night-before fix` without making any actual changes.

### Configuration

The tool should support the following configuration options:

1. Work hours definition (start and end time)
2. Weekend detection (option to skip commits made on weekends)
3. Custom time ranges for night-before timestamps

### Required Improvements

#### 1. Robust Git Date Handling

Ensure robust parsing of git date formats by:
- Supporting multiple date formats (RFC 2822, ISO 8601)
- Preserving timezone information in the original commits

#### 2. Weekend Detection

Add detection for weekends:
- Skip commits made on Saturday and Sunday regardless of time
- Make this behavior configurable

#### 3. using git filter-branch

This must print what git commands will be run by `the-night-before fix` without making any actual changes.

Use the following jinja2 template to generate the filter-branch command:

```jinja2
git filter-branch -f --env-filter \
    '{% for commit in commits_to_fix %}
    if [ $GIT_COMMIT = {{ commit.hash }} ]
     then
         export GIT_AUTHOR_DATE="{{ commit.new_date }}"
         export GIT_COMMITTER_DATE="{{ commit.new_date }}"
     fi{% endfor %}'
```
