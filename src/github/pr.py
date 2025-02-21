"""
GitHub pull request handling module.
"""
import logging
from typing import Dict, Any, List, Optional

from github.Repository import Repository

# Configure logging
logger = logging.getLogger(__name__)


def create_pull_request(
    repository: Repository,
    branch_name: str,
    issue_number: int,
    title: str,
    body: str,
    repo_config: Dict[str, Any],
) -> Optional[str]:
    """
    Create a pull request for a branch.
    
    Args:
        repository: GitHub repository
        branch_name: Branch name
        issue_number: Related issue number
        title: PR title
        body: PR body
        repo_config: Repository configuration
        
    Returns:
        PR URL if successful, None otherwise
    """
    try:
        # Get default branch
        default_branch = repository.default_branch
        
        # Get PR configuration
        pr_config = repo_config.get("pr", {})
        draft = pr_config.get("draft", False)
        
        # Create the pull request
        pr = repository.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=default_branch,
            draft=draft,
        )
        
        # Link PR to issue
        if issue_number:
            pr.as_issue().edit(body=f"{body}\n\nCloses #{issue_number}")
        
        # Add reviewers if specified
        reviewers = pr_config.get("reviewers", [])
        if reviewers:
            try:
                pr.create_review_request(reviewers=reviewers)
            except Exception as e:
                logger.warning(f"Failed to add reviewers: {e}")
        
        # Add labels if specified
        labels = pr_config.get("labels", [])
        if labels:
            try:
                pr.add_to_labels(*labels)
            except Exception as e:
                logger.warning(f"Failed to add labels: {e}")
        
        logger.info(f"Created PR #{pr.number}: {pr.html_url}")
        return pr.html_url
    
    except Exception as e:
        logger.error(f"Failed to create PR: {e}")
        return None


def update_pull_request(
    repository: Repository,
    pr_number: int,
    state: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
) -> bool:
    """
    Update an existing pull request.
    
    Args:
        repository: GitHub repository
        pr_number: PR number
        state: New state ("open" or "closed")
        title: New title
        body: New body
        
    Returns:
        True if successful, False otherwise
    """
    try:
        pr = repository.get_pull(pr_number)
        
        update_args = {}
        if state:
            update_args["state"] = state
        if title:
            update_args["title"] = title
        if body:
            update_args["body"] = body
        
        if update_args:
            pr.edit(**update_args)
            logger.info(f"Updated PR #{pr_number}")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Failed to update PR: {e}")
        return False
