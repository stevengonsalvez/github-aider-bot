"""
GitHub issues handling module.
"""
import logging
import re
from typing import Dict, Any, List, Tuple, Optional

from github import Github
from github.Issue import Issue
from github.Repository import Repository

from config import config
from github.app import get_installation_client, get_repo_config
from analysis.issue_analyzer import analyze_issue
from aider.integration import run_aider_on_issue
from git.operations import checkout_branch, commit_changes
from github.pr import create_pull_request

# Configure logging
logger = logging.getLogger(__name__)


def should_process_issue(issue: Issue, repo_config: Dict[str, Any]) -> bool:
    """
    Determine if an issue should be processed by the bot.
    
    Args:
        issue: GitHub issue
        repo_config: Repository configuration
        
    Returns:
        True if the issue should be processed, False otherwise
    """
    # Check for process labels
    process_labels = repo_config.get("labels", {}).get("process", [])
    ignore_labels = repo_config.get("labels", {}).get("ignore", [])
    
    # Get issue labels
    issue_labels = [label.name for label in issue.labels]
    
    # If the issue has any ignore labels, don't process it
    if any(label in issue_labels for label in ignore_labels):
        logger.info(f"Issue {issue.number} has ignore label, skipping")
        return False
    
    # If process labels are specified, only process issues with those labels
    if process_labels and not any(label in issue_labels for label in process_labels):
        logger.info(f"Issue {issue.number} doesn't have any process labels, skipping")
        return False
    
    return True


def extract_issue_details(
    issue: Issue,
    repo_config: Dict[str, Any]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Extract details from an issue for processing.
    
    Args:
        issue: GitHub issue
        repo_config: Repository configuration
        
    Returns:
        Tuple of (should_process, issue_details)
    """
    # Check if we should process this issue
    if not should_process_issue(issue, repo_config):
        return False, {}
    
    # Extract issue details
    issue_details = {
        "title": issue.title,
        "body": issue.body or "",
        "number": issue.number,
        "url": issue.html_url,
        "user": issue.user.login,
        "created_at": issue.created_at.isoformat(),
        "updated_at": issue.updated_at.isoformat(),
        "labels": [label.name for label in issue.labels],
    }
    
    # Analyze the issue to determine if it's actionable
    analysis_result = analyze_issue(issue_details["body"])
    
    # Combine issue details with analysis result
    issue_details.update(analysis_result)
    
    return True, issue_details


def process_issue_event(payload: Dict[str, Any]) -> None:
    """
    Process an issue event from GitHub.
    
    Args:
        payload: Webhook payload
    """
    try:
        # Extract repository and issue information
        repo_name = payload["repository"]["full_name"]
        owner, repo = repo_name.split("/")
        issue_number = payload["issue"]["number"]
        
        logger.info(f"Processing issue #{issue_number} from {repo_name}")
        
        # Get GitHub client for the installation
        client = get_installation_client(owner, repo)
        if not client:
            logger.error(f"Failed to get GitHub client for {repo_name}")
            return
        
        # Get repository and issue objects
        repository = client.get_repo(repo_name)
        issue = repository.get_issue(issue_number)
        
        # Get repository configuration
        repo_config = get_repo_config(owner, repo, client)
        
        # Check if we should process this issue
        should_process, issue_details = extract_issue_details(issue, repo_config)
        if not should_process:
            logger.info(f"Skipping issue #{issue_number}")
            return
        
        # Add a comment that we're working on it
        comment = issue.create_comment(
            f"🤖 I'm analyzing this issue to see if I can help fix it automatically. I'll update you shortly."
        )
        
        # Create a branch name based on the issue
        branch_name = f"fix/issue-{issue_number}"
        safe_branch_name = re.sub(r'[^a-zA-Z0-9/_-]', '-', branch_name)
        
        # Run the fix workflow
        fix_issue(
            repository=repository,
            issue=issue,
            issue_details=issue_details,
            branch_name=safe_branch_name,
            repo_config=repo_config,
        )
    
    except Exception as e:
        logger.exception(f"Error processing issue event: {e}")


def fix_issue(
    repository: Repository,
    issue: Issue,
    issue_details: Dict[str, Any],
    branch_name: str,
    repo_config: Dict[str, Any],
) -> None:
    """
    Fix an issue using Aider.
    
    Args:
        repository: GitHub repository
        issue: GitHub issue
        issue_details: Extracted issue details
        branch_name: Branch name to create
        repo_config: Repository configuration
    """
    try:
        # Notify that we're attempting a fix
        issue.create_comment(
            f"🔍 I'm attempting to fix this issue. I'll create a branch `{branch_name}` and open a PR if successful."
        )
        
        # Clone the repository and checkout a new branch
        repo_path = checkout_branch(repository.clone_url, branch_name)
        if not repo_path:
            issue.create_comment(
                "❌ Failed to checkout a new branch. Unable to proceed with automated fix."
            )
            return
        
        # Run Aider on the issue
        success, changes = run_aider_on_issue(
            repo_path=repo_path,
            issue_details=issue_details,
            repo_config=repo_config,
        )
        
        if not success or not changes:
            issue.create_comment(
                "❌ I was unable to automatically fix this issue. A human developer will need to take a look."
            )
            return
        
        # Commit the changes
        commit_result = commit_changes(
            repo_path=repo_path,
            branch_name=branch_name,
            commit_message=f"Fix issue #{issue_details['number']}: {issue_details['title']}",
            changes=changes,
        )
        
        if not commit_result:
            issue.create_comment(
                "❌ Failed to commit changes. Unable to proceed with automated fix."
            )
            return
        
        # Create a pull request
        pr_url = create_pull_request(
            repository=repository,
            branch_name=branch_name,
            issue_number=issue_details["number"],
            title=f"Fix issue #{issue_details['number']}: {issue_details['title']}",
            body=f"This PR was automatically generated to fix issue #{issue_details['number']}.\n\n{issue_details.get('solution_description', '')}",
            repo_config=repo_config,
        )
        
        if not pr_url:
            issue.create_comment(
                "❌ Failed to create a pull request. Changes have been committed to the branch `{branch_name}`."
            )
            return
        
        # Update the issue with the PR link
        issue.create_comment(
            f"✅ I've created a pull request with a potential fix: {pr_url}\n\n"
            f"Please review the changes and provide feedback. If the fix looks good, "
            f"you can merge the PR to resolve this issue."
        )
        
    except Exception as e:
        logger.exception(f"Error fixing issue: {e}")
        issue.create_comment(
            f"❌ An error occurred while trying to fix this issue: {str(e)}\n\n"
            f"A human developer will need to take a look."
        )
