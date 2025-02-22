"""
Aider integration module.
"""
import logging
import os
import subprocess
import tempfile
import json
from typing import Dict, Any, List, Tuple, Optional
import asyncio

from src.config import config

# Configure logging
logger = logging.getLogger(__name__)


def prepare_aider_input(issue_details: Dict[str, Any]) -> str:
    """
    Prepare an input prompt for Aider based on the issue details.
    
    Args:
        issue_details: Issue details
    
    Returns:
        Prompt text for Aider
    """
    prompt = f"# Issue #{issue_details['number']}: {issue_details['title']}\n\n"
    
    # Add issue description
    prompt += "## Description\n"
    prompt += issue_details['body']
    prompt += "\n\n"
    
    # Add additional context
    prompt += "## Analysis\n"
    
    if issue_details.get('file_paths'):
        prompt += "### Affected files\n"
        for file_path in issue_details['file_paths']:
            prompt += f"- {file_path}\n"
        prompt += "\n"
    
    if issue_details.get('error_messages'):
        prompt += "### Error messages\n"
        for error in issue_details['error_messages']:
            prompt += f"```\n{error}\n```\n"
        prompt += "\n"
    
    # Add instructions for Aider
    prompt += "## Instructions\n"
    prompt += "Please fix this issue based on the description and analysis above. "
    prompt += "Implement the minimal changes needed to resolve the problem. "
    prompt += "After making changes, explain what you did and why.\n"
    
    return prompt


def parse_aider_output(output: str) -> Tuple[Dict[str, str], str]:
    """
    Parse the output from Aider to get the changes made.
    
    Args:
        output: Aider output text
    
    Returns:
        Tuple of (changes_dict, solution_description)
    """
    logger.info("Parsing Aider output")
    
    # Initialize return values
    changes = {}
    solution_description = ""
    
    # Look for file changes in Aider output
    # Aider typically reports changes like:
    # 
    # Edited 'file/path.py':
    # --- a/file/path.py
    # +++ b/file/path.py
    # @@ ... @@
    # ...

    # Extract edited files sections
    edit_sections = re.finditer(r"Edited '([^']+)':\n---.*?\n(.*?)(?:\n(?:Edited|$)|\Z)", 
                               output, re.DOTALL)
    
    for match in edit_sections:
        file_path = match.group(1)
        edit_content = match.group(2)
        
        if file_path and edit_content:
            changes[file_path] = edit_content
    
    # Extract solution description - typically found after all edits
    description_match = re.search(r"(?:^|\n)(?:Solution|Changes|I made the following changes):(.*?)(?:\n\n|\Z)", 
                                 output, re.DOTALL | re.IGNORECASE)
    
    if description_match:
        solution_description = description_match.group(1).strip()
    
    # If no explicit description found, use the whole output as fallback
    if not solution_description:
        solution_description = output
    
    return changes, solution_description


async def run_aider(input_file: str, files: List[str]) -> Tuple[int, str, str]:
    """Run aider with the given input file and files to edit."""
    cmd = [
        config.aider.binary_path,
        "--model", config.aider.model,
        "--no-git",  # Don't use git features since we handle that
        "--message-file", input_file,  # Use message-file instead of input-file
        "--no-interactive",  # Run in non-interactive mode
        *files  # Files to edit
    ]

    if config.aider.api_key:
        cmd.extend(["--openai-api-key", config.aider.api_key])

    logger.info(f"Running aider command: {' '.join(cmd)}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return (
            process.returncode,
            stdout.decode() if stdout else "",
            stderr.decode() if stderr else ""
        )
    except Exception as e:
        logger.exception("Failed to run aider")
        return 1, "", str(e)


def run_aider_on_issue(
    repo_path: str,
    issue_details: Dict[str, Any],
    repo_config: Dict[str, Any],
) -> Tuple[bool, Dict[str, str]]:
    """
    Run Aider on an issue to generate fixes.
    
    Args:
        repo_path: Path to the repository
        issue_details: Issue details
        repo_config: Repository configuration
    
    Returns:
        Tuple of (success, changes)
    """
    import re
    
    logger.info(f"Running Aider on issue #{issue_details['number']}")
    
    # Prepare the input prompt
    prompt = prepare_aider_input(issue_details)
    
    # Create a temp file for the prompt
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        prompt_file = f.name
        f.write(prompt)
    
    try:
        # Set up environment variables
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = config.aider.api_key
        
        # Build the Aider command
        cmd = [
            config.aider.binary_path,
            "--model", config.aider.model,
            "--input-file", prompt_file,
            "--yes",  # Auto-apply changes
            "--no-git",  # Don't make git commits
            "--no-interactive",  # Non-interactive mode
            repo_path,
        ]
        
        # Add file path filters if available
        file_includes = repo_config.get("files", {}).get("include", [])
        file_excludes = repo_config.get("files", {}).get("exclude", [])
        
        if issue_details.get('file_paths'):
            # If we have specific file paths from the issue, use those
            for file_path in issue_details['file_paths']:
                if os.path.exists(os.path.join(repo_path, file_path)):
                    cmd.append(file_path)
        elif file_includes:
            # Otherwise use the repo config includes
            for pattern in file_includes:
                cmd.append(pattern)
        
        # Run Aider
        logger.info(f"Running Aider command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            cwd=repo_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # Get output with timeout
        stdout, stderr = process.communicate(timeout=600)  # 10 minutes timeout
        
        # Check if Aider succeeded
        if process.returncode != 0:
            logger.error(f"Aider failed with exit code {process.returncode}")
            logger.error(f"Stderr: {stderr}")
            return False, {}
        
        # Parse the output
        changes, solution_description = parse_aider_output(stdout)
        
        # Store the solution description in the issue details
        issue_details["solution_description"] = solution_description
        
        return bool(changes), changes
    
    except Exception as e:
        logger.exception(f"Error running Aider: {e}")
        return False, {}
    
    finally:
        # Clean up the temp file
        if os.path.exists(prompt_file):
            os.unlink(prompt_file)
