
# Instructions for implementing a Python module

Read the spec below and consider its feasibility: is it well defined enough to implement in a single python module? Are there any important unanswered questions? Are there any things you don't know how to do? Are any of these blockers to proceeding?

If no, Stop, and summarise why you cannot yet implement this spec as an error.

If yes, describe what we need to do to implement this module, then implement it.

The module should be created at tlc/the_night_before.py


Update the pyproject.toml file to add the new module entry point, using this format:
```python
[project.scripts]
the-night-before = "tlc.the_night_before:main"
```

This script should be sufficient to implement the module. You must only add the the_night_before.py module and edit the pyproject.toml file if needed.

# Module Specification
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

Do not update:
- GIT_COMMITTER_NAME
- GIT_COMMITTER_EMAIL
- GIT_AUTHOR_NAME
- GIT_AUTHOR_EMAIL

The env-filter must be passed as a whole string, you can do this by passing a list of arguments in to subprocess.run

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
