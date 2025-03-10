# the_night_before.py

## Inputs

Current working directory should be a git repository.

## Outputs

No outputs, will simply update the git repository.

## Implementation

the-night-before is a python script which allows you to amend the time stamps in git commits as if you committed the night before, so it doesn't look like you're committing to open-source projects during work hours (8am-7pm).

### Commands

```
the-night-before check
```

Checks if any commits are made in work hours (8am-7pm) and fails with a message to fix with `the-night-before fix` if so.

```
the-night-before install-git-hooks
```

Installs git pre-push hooks using `the-night-before check` to prevent commits being made during work hours being pushed to a remote repository.

```
the-night-before fix
```

This will list all commits from the past 24 hours, and amend the author and commit times for all of them to be the night before in the hours between 10pm and 3am.

The tool will print what changes it will make and get user confirmation before making them.

```
the-night-before dry-run
```

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

When working out the new timestamps, we must ensure chronological order is maintained. To do this, the script should:

- collect all commits from the last 24 hours (including ones already outside of working hours) sorted by date
- divide the available target time (10pm-3am last night) into equal chunks
- for each commit, pick a random time in its chunk, normally distributed around the middle of the chunk

The script only works on commits from the last day.

### Ammending commit times

Use a command formatted like this one to ammend each commit

```
git filter-branch --env-filter \
    'if [ $GIT_COMMIT = 119f9ecf58069b265ab22f1f97d2b648faf932e0 ]
     then
         export GIT_AUTHOR_DATE="Fri Jan 2 21:38:53 2009 -0800"
         export GIT_COMMITTER_DATE="Sat May 19 01:01:01 2007 -0700"
     fi'
```
