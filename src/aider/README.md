# Aider Integration Module

This module handles integration with Aider, an AI-powered coding assistant.

## Components

- `integration.py`: Functions for running Aider and processing its output

## Functionality

The Aider integration:

1. Prepares issue details for Aider
2. Invokes the Aider CLI with appropriate parameters
3. Processes Aider's output to extract changes
4. Handles error cases

## Usage

```python
from aider.integration import run_aider_on_issue

# Run Aider on an issue
repo_path = "/path/to/repo"
issue_details = {
    "number": 123,
    "title": "Fix bug in app.py",
    "body": "There's a bug that causes an error...",
    "file_paths": ["app.py"],
    "error_messages": ["KeyError: 'action'"],
}
repo_config = {
    "files": {
        "include": ["**"],
        "exclude": []
    }
}

success, changes = run_aider_on_issue(repo_path, issue_details, repo_config)

if success:
    print(f"Aider made changes to {len(changes)} files")
else:
    print("Aider could not fix the issue")
```
