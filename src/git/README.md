# Git Operations Module

This module handles Git operations required by the bot.

## Components

- `operations.py`: Functions for Git operations

## Functionality

The Git operations module:

1. Clones repositories
2. Creates and checkouts branches
3. Applies changes from diffs
4. Commits and pushes changes

## Usage

```python
from git.operations import checkout_branch, commit_changes

# Checkout a branch
repo_path = checkout_branch("https://github.com/username/repo.git", "fix/issue-123")

if repo_path:
    # Make changes to files...
    
    # Commit and push changes
    changes = {
        "app.py": "diff --git a/app.py b/app.py\n..."
    }
    success = commit_changes(
        repo_path=repo_path,
        branch_name="fix/issue-123",
        commit_message="Fix issue #123: Bug in app.py",
        changes=changes,
    )
    
    if success:
        print("Changes committed and pushed")
    else:
        print("Failed to commit changes")
```
