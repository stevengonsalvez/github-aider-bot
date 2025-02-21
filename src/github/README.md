# GitHub Integration Module

This module handles all GitHub-related functionality including:

- GitHub App authentication
- Webhook event handling
- Issue management
- Pull request creation and management

## Components

- `app.py`: GitHub App setup and authentication
- `issues.py`: Issue handling and processing
- `pr.py`: Pull request creation and updates

## Usage

Import and use the functions as needed:

```python
from github.app import get_installation_client
from github.issues import process_issue_event
from github.pr import create_pull_request

# Get a GitHub client for a repository
client = get_installation_client(owner, repo)

# Process an issue event
process_issue_event(webhook_payload)

# Create a pull request
pr_url = create_pull_request(repository, branch_name, issue_number, title, body, repo_config)
```
