"""
GitHub issues handling module.
"""
import logging
import re
import os
import tempfile
from typing import Dict, Any, List, Tuple, Optional

from github import Github
from github.Issue import Issue
from github.Repository import Repository
from gidgethub.aiohttp import GitHubAPI
from git import Repo

from src.config import config
from src.github.app import get_installation_client, get_repo_config
from src.analysis.issue_analyzer import analyze_issue
from src.aider.integration import run_aider_on_issue
from src.git.operations import checkout_branch, commit_changes
from src.github.pr import create_pull_request

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


async def process_issue_event(payload: Dict[str, Any]):
    """Process an issue event."""
    try:
        # Extract repository and issue information
        repo_name = payload["repository"]["full_name"]
        owner, repo = repo_name.split("/")
        issue_number = payload["issue"]["number"]
        
        logger.info(f"Processing issue #{issue_number} from {repo_name}")
        
        # Get GitHub client and token for the installation
        gh, access_token = await get_installation_client(owner, repo)
        if not gh or not access_token:
            logger.error(f"Failed to get GitHub client for {repo_name}")
            return
            
        # Get repository and issue objects
        repository = gh.get_repo(repo_name)
        issue = repository.get_issue(issue_number)
        
        # Create a temporary directory for the repository
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Cloning repository to {temp_dir}")
            
            # Get the clone URL with auth token
            clone_url = repository.clone_url.replace(
                "https://",
                f"https://x-access-token:{access_token}@"
            )
            
            logger.debug(f"Using clone URL (redacted): {clone_url.replace(access_token, 'TOKEN')}")
            
            # Clone the repository
            repo = Repo.clone_from(
                clone_url,
                temp_dir,
                branch=repository.default_branch
            )
            
            logger.info(f"Successfully cloned repository to {temp_dir}")
            
            # Extract file paths from issue body
            file_paths = []
            if "package.json" in payload["issue"]["body"].lower():
                file_paths.append("package.json")
            
            # Add issue details with file paths
            issue_details = {
                **payload["issue"],
                "file_paths": file_paths or ["package.json"]  # Default to package.json if no files found
            }
            
            # Add a comment that we're working on it
            issue.create_comment(
                "🤖 I'm analyzing this issue to see if I can help fix it automatically. I'll update you shortly."
            )
            
            # Run Aider on the issue
            success, changes, solution_description = await run_aider_on_issue(
                repo_path=temp_dir,
                issue_details=issue_details,
                repo_config={}
            )

            if success and changes:
                # Create a branch name from issue
                branch_name = f"fix/issue-{issue_number}"
                base_branch = repository.default_branch
                
                # Create branch from default branch
                base_ref = repository.get_git_ref(f"heads/{base_branch}")
                repository.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=base_ref.object.sha
                )
                
                # Create/update the files
                for file_path, content in changes.items():
                    try:
                        # Try to get existing file
                        file = repository.get_contents(file_path, ref=branch_name)
                        repository.update_file(
                            file_path,
                            f"Update {file_path} for issue #{issue_number}",
                            content,
                            file.sha,
                            branch=branch_name
                        )
                    except:
                        # File doesn't exist, create it
                        repository.create_file(
                            file_path,
                            f"Create {file_path} for issue #{issue_number}",
                            content,
                            branch=branch_name
                        )
                
                # Create the pull request
                pr = repository.create_pull(
                    title=f"Fix #{issue_number}: {payload['issue']['title']}",
                    body=solution_description,
                    head=branch_name,
                    base=base_branch
                )
                
                # Add comment to issue
                issue.create_comment(
                    f"I've created PR #{pr.number} with a fix for this issue.\n\n{solution_description}"
                )
                
            else:
                # Add comment that no changes were made
                issue.create_comment(
                    "I analyzed the issue but couldn't automatically fix it. A human review may be needed."
                )

    except Exception as e:
        logger.exception(f"Error processing issue: {e}")
        # Add error comment to issue
        try:
            issue = repository.get_issue(issue_number)
            issue.create_comment(
                f"Sorry, I encountered an error while trying to fix this issue:\n```\n{str(e)}\n```"
            )
        except Exception as comment_error:
            logger.exception("Failed to post error comment", exc_info=comment_error)
