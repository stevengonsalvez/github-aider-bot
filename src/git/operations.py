"""
Git operations module.
"""
import logging
import os
import re
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple

import git
from git import Repo

# Configure logging
logger = logging.getLogger(__name__)


def checkout_branch(repo_url: str, branch_name: str) -> Optional[str]:
    """
    Clone a repository and checkout a new branch.
    
    Args:
        repo_url: Repository URL
        branch_name: Branch name to create
    
    Returns:
        Path to the cloned repository if successful, None otherwise
    """
    # Create a temporary directory for the repo
    repo_dir = tempfile.mkdtemp(prefix="aider-bot-")
    
    try:
        logger.info(f"Cloning repository {repo_url} to {repo_dir}")
        
        # Clone the repo
        repo = Repo.clone_from(repo_url, repo_dir)
        
        # Create and checkout a new branch
        logger.info(f"Creating branch {branch_name}")
        repo.git.checkout('-b', branch_name)
        
        return repo_dir
    
    except Exception as e:
        logger.exception(f"Error checking out branch: {e}")
        # Clean up if we failed
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
        return None


def apply_diff(file_path: str, diff_content: str) -> bool:
    """
    Apply a diff to a file.
    
    Args:
        file_path: Path to the file
        diff_content: Diff content
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Parse the diff to extract line changes
        lines = []
        current_line = 0
        
        # Read the current file
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Extract the diff hunks
        for hunk in re.finditer(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*?)(?=\n@@ |\Z)', 
                               diff_content, re.DOTALL):
            start_line = int(hunk.group(2)) - 1  # 0-based index
            hunk_content = hunk.group(3)
            
            # Process lines in the hunk
            lines_to_add = []
            skip_lines = 0
            
            for line in hunk_content.split('\n')[1:]:  # Skip the hunk header line
                if not line:
                    continue
                
                if line.startswith('+'):
                    # Add this line
                    lines_to_add.append(line[1:])
                elif line.startswith('-'):
                    # Skip this line in the original file
                    skip_lines += 1
                else:
                    # Context line, keep both
                    lines_to_add.append(line)
            
            # Apply the changes to the file
            lines[start_line:start_line + skip_lines] = lines_to_add
        
        # Write the modified file
        with open(file_path, 'w') as f:
            f.writelines(lines)
        
        return True
    
    except Exception as e:
        logger.exception(f"Error applying diff: {e}")
        return False


def commit_changes(
    repo_path: str,
    branch_name: str,
    commit_message: str,
    changes: Dict[str, str],
) -> bool:
    """
    Commit changes to a repository.
    
    Args:
        repo_path: Path to the repository
        branch_name: Branch name
        commit_message: Commit message
        changes: Dictionary of file paths to diff content
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Committing changes to branch {branch_name}")
        
        # Open the repository
        repo = Repo(repo_path)
        
        # Apply changes to files
        for file_path, diff_content in changes.items():
            full_path = os.path.join(repo_path, file_path)
            if not os.path.exists(full_path):
                logger.warning(f"File {file_path} does not exist, skipping")
                continue
            
            # Apply the diff to the file
            apply_diff(full_path, diff_content)
        
        # Add all changes
        repo.git.add('.')
        
        # Create the commit
        repo.git.commit('-m', commit_message)
        
        # Push the changes
        repo.git.push('--set-upstream', 'origin', branch_name)
        
        logger.info(f"Changes committed and pushed to {branch_name}")
        return True
    
    except Exception as e:
        logger.exception(f"Error committing changes: {e}")
        return False
