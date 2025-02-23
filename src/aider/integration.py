"""
Aider integration module.
"""
import logging
import os
import subprocess
import tempfile
import json
import re
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
    # First log the model configuration
    logger.info(f"Aider configuration:")
    logger.info(f"  Model: {config.aider.model}")
    logger.info(f"  API Key configured: {'Yes' if config.aider.api_key else 'No'}")
    logger.info(f"  Provider: {'OpenAI' if config.aider.api_key else 'Unknown'}")
    
    # Read the input file content
    with open(input_file, 'r') as f:
        message = f.read()
    
    cmd = [
        config.aider.binary_path,
        "--model", config.aider.model,
        "--no-git",  # Don't use git features since we handle that
        "--message", message,  # Use --message instead of --message-file
        "--yes",  # Auto-confirm changes
    ]

    # Add API key in the correct format
    if config.aider.api_key:
        cmd.extend(["--api-key", f"openai={config.aider.api_key}"])

    # Add files at the end
    cmd.extend(files)

    logger.info(f"Running aider command: {' '.join(cmd)}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Log any model information from stderr
        if stderr:
            stderr_text = stderr.decode()
            if "Using model:" in stderr_text:
                logger.info(f"Aider reported: {stderr_text.split('Using model:')[1].strip()}")
        
        return (
            process.returncode,
            stdout.decode() if stdout else "",
            stderr.decode() if stderr else ""
        )
    except Exception as e:
        logger.exception("Failed to run aider")
        return 1, "", str(e)


async def run_aider_on_issue(
    repo_path: str,
    issue_details: Dict[str, Any],
    repo_config: Dict[str, Any],
) -> Tuple[bool, Dict[str, str], Optional[str]]:
    """
    Run Aider on an issue to generate fixes.
    Returns (success, changes, solution_description)
    """
    logger.info(f"Running Aider on issue #{issue_details['number']}")
    logger.info(f"Repository path: {repo_path}")
    
    # Verify repo path exists and is a directory
    if not os.path.isdir(repo_path):
        logger.error(f"Repository path does not exist or is not a directory: {repo_path}")
        return False, {}, None
        
    # Verify it's a git repository
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        logger.error(f"Path is not a git repository: {repo_path}")
        return False, {}, None
        
    logger.info(f"Repository verified at {repo_path}")
    
    # Get target files
    target_files = []
    
    # First try files mentioned in the issue
    if issue_details.get('file_paths'):
        for file_path in issue_details['file_paths']:
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                target_files.append(file_path)
                logger.info(f"Adding target file from issue: {file_path}")
    
    # If no files found, try repo config
    if not target_files and repo_config.get("files", {}).get("include", []):
        target_files.extend(repo_config["files"]["include"])
        logger.info(f"Using include patterns from config: {target_files}")
    
    # If still no files, use defaults
    if not target_files:
        default_files = ["package.json"]  # Add more defaults as needed
        for file_path in default_files:
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                target_files.append(file_path)
                logger.info(f"Using default file: {file_path}")
    
    if not target_files:
        logger.error("No target files found in repository")
        return False, {}, None
    
    logger.info(f"Will process these files: {target_files}")
    
    # Prepare the input prompt
    prompt = prepare_aider_input(issue_details)
    
    # Create a temp file for the prompt
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        prompt_file = f.name
        f.write(prompt)
        logger.info(f"Created prompt file: {prompt_file}")
    
    try:
        # Read the prompt content
        with open(prompt_file, 'r') as f:
            prompt_content = f.read()
            logger.debug(f"Prompt content:\n{prompt_content}")
        
        # Build the Aider command
        cmd = [
            config.aider.binary_path,
            "--model", config.aider.model,
            "--message", prompt_content,
            "--yes",  # Auto-apply changes
            "--no-git",  # Don't make git commits
        ]
        
        # Add API key in the correct format
        if config.aider.api_key:
            cmd.extend(["--api-key", f"openai={config.aider.api_key}"])
        else:
            logger.warning("No OpenAI API key configured")
        
        # Add files at the end
        cmd.extend(target_files)
        
        # Run Aider
        logger.info(f"Running Aider command: {' '.join(cmd)}")
        logger.info(f"Working directory: {repo_path}")
        
        process = subprocess.Popen(
            cmd,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()  # Ensure we pass through environment variables
        )
        
        # Get output with timeout
        stdout, stderr = process.communicate(timeout=600)  # 10 minutes timeout
        
        # Log all output
        if stdout:
            logger.info(f"Aider stdout:\n{stdout}")
        if stderr:
            logger.info(f"Aider stderr:\n{stderr}")
        
        # Check if Aider succeeded
        if process.returncode != 0:
            logger.error(f"Aider failed with exit code {process.returncode}")
            if stderr:
                logger.error(f"Stderr: {stderr}")
            if stdout:
                logger.error(f"Stdout: {stdout}")
            return False, {}, None
        
        # Parse the output
        changes, solution_description = parse_aider_output(stdout)
        
        # Log the results
        logger.info(f"Changes detected: {bool(changes)}")
        if changes:
            logger.info(f"Files changed: {list(changes.keys())}")
            
            # Store the changes and description for PR creation
            issue_details["changes"] = changes
            issue_details["solution_description"] = solution_description
            
            return True, changes, solution_description
        
        return False, {}, None
        
    except Exception as e:
        logger.exception(f"Error running Aider: {e}")
        return False, {}, None
    
    finally:
        # Clean up the temp file
        if os.path.exists(prompt_file):
            os.unlink(prompt_file)
            logger.debug(f"Cleaned up prompt file: {prompt_file}")
