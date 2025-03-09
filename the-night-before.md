# the_night_before.py

## Inputs

Current working directory should be a git repository.

## Outputs

No outputs, will simply update the git repository.

## Implementation

the-night-before is a python script which allows you to amend the time stamps in git commits as if you committed the night before, so it doesn't look like you're committing to open-source projects during work hours.

Provides a tool that lets you run:

```
the-night-before fix
```

This will list all commits that are listed as being during 9am to 7pm Monday to Friday, and will pick a time the night before (10pm-3am) to ammend it to so that the commit times are roughly spaced.

The tool will print what changes it will make and get user confirmation before making them.

Also supports:

```
the-night-before dry-run
```

This will print what git commands will be run without making any actual changes.

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
