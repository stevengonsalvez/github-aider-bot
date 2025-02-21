"""
Issue analysis module.
"""
import logging
import re
from typing import Dict, Any, List, Optional, Set

# Configure logging
logger = logging.getLogger(__name__)


def extract_file_paths(text: str) -> List[str]:
    """
    Extract potential file paths from issue text.
    
    Args:
        text: Issue text
    
    Returns:
        List of file paths
    """
    # Look for file paths in the text
    # This is a simple regex that might need tuning based on actual issues
    file_path_patterns = [
        r'(?:^|\s)(\S+\.[a-zA-Z0-9]{1,10})(?:\s|$|:|,)',  # Simple file with extension
        r'(?:^|\s)((?:\.{0,2}\/)?(?:\w+\/)*\w+\.\w+)(?:\s|$|:|,)',  # Paths like ./dir/file.ext or dir/file.ext
        r'in\s+`([^`]+\.[a-zA-Z0-9]{1,10})`',  # Files mentioned like: in `file.py`
        r'at\s+`([^`]+\.[a-zA-Z0-9]{1,10})`',  # Files mentioned like: at `file.py`
        r'(?:file|path):\s*[\'"]?([^\'"]+\.[a-zA-Z0-9]{1,10})[\'"]?',  # Files mentioned like: file: 'file.py'
    ]
    
    file_paths = set()
    for pattern in file_path_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            file_path = match.group(1)
            # Clean up the file path
            file_path = file_path.strip()
            # Filter out common false positives
            if not (file_path.startswith("http") or 
                    file_path in ("v1.0", "v2.0") or 
                    file_path.endswith(".0") or
                    file_path.endswith(".com")):
                file_paths.add(file_path)
    
    return list(file_paths)


def extract_error_messages(text: str) -> List[str]:
    """
    Extract potential error messages from issue text.
    
    Args:
        text: Issue text
    
    Returns:
        List of error messages
    """
    # Look for error patterns
    error_patterns = [
        r'Error:\s*(.+?)(?:\n|$)',  # Lines starting with "Error:"
        r'Exception:\s*(.+?)(?:\n|$)',  # Lines with "Exception:"
        r'Traceback[^`]+```(?:python)?(.*?)```',  # Code blocks with traceback
        r'```\s*(?:console|shell|bash)?\s*(.*?Error:.*?)```',  # Code blocks with errors
        r'```\s*(?:console|shell|bash)?\s*(.*?Exception:.*?)```',  # Code blocks with exceptions
    ]
    
    error_messages = []
    for pattern in error_patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            error_message = match.group(1).strip()
            if error_message:
                error_messages.append(error_message)
    
    return error_messages


def extract_code_blocks(text: str) -> List[str]:
    """
    Extract code blocks from issue text.
    
    Args:
        text: Issue text
    
    Returns:
        List of code blocks
    """
    # Look for code blocks
    code_blocks = []
    for block in re.finditer(r'```(?:\w+)?\s*(.*?)```', text, re.DOTALL):
        code = block.group(1).strip()
        if code:
            code_blocks.append(code)
    
    return code_blocks


def determine_issue_type(text: str) -> str:
    """
    Determine the type of issue.
    
    Args:
        text: Issue text
    
    Returns:
        Issue type
    """
    # Look for keywords that indicate the issue type
    bug_keywords = ["bug", "error", "exception", "crash", "fail", "broken", "doesn't work", "does not work"]
    feature_keywords = ["feature", "enhancement", "request", "add", "new", "improvement"]
    question_keywords = ["question", "how to", "guidance", "help", "wondering", "?"]
    
    text_lower = text.lower()
    
    bug_count = sum(1 for keyword in bug_keywords if keyword in text_lower)
    feature_count = sum(1 for keyword in feature_keywords if keyword in text_lower)
    question_count = sum(1 for keyword in question_keywords if keyword in text_lower)
    
    # Check for error messages and stack traces
    if re.search(r'Error:|Exception:|Traceback', text):
        bug_count += 2
    
    # Make a decision based on counts
    if bug_count > feature_count and bug_count > question_count:
        return "bug"
    elif feature_count > bug_count and feature_count > question_count:
        return "feature"
    elif question_count > bug_count and question_count > feature_count:
        return "question"
    else:
        # Default to bug if unclear
        return "bug"


def evaluate_fix_potential(text: str, issue_type: str) -> float:
    """
    Evaluate the potential for an automated fix.
    
    Args:
        text: Issue text
        issue_type: Issue type
    
    Returns:
        Score between 0.0 and 1.0
    """
    # Only bugs are potentially fixable automatically
    if issue_type != "bug":
        return 0.0
    
    score = 0.5  # Start with a middle score
    
    # Add points for positive indicators
    if extract_file_paths(text):
        score += 0.2  # We have file paths
    
    if extract_error_messages(text):
        score += 0.2  # We have error messages
    
    if extract_code_blocks(text):
        score += 0.1  # We have code blocks
    
    # Look for specificity
    if re.search(r'(specific|exact|line|column|function|method)\s+(\d+|name)', text, re.IGNORECASE):
        score += 0.1  # Issue seems specific
    
    # Look for negative indicators
    if re.search(r'(sometimes|intermittent|random|occasionally|rarely|not sure)', text, re.IGNORECASE):
        score -= 0.2  # Issue seems inconsistent
    
    if len(text.split()) < 20:
        score -= 0.2  # Issue is too short
    
    if "steps to reproduce" not in text.lower() and "reproduce" not in text.lower():
        score -= 0.1  # No reproduction steps
    
    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))


def analyze_issue(text: str) -> Dict[str, Any]:
    """
    Analyze an issue to determine if it's fixable.
    
    Args:
        text: Issue text
    
    Returns:
        Analysis results
    """
    logger.info("Analyzing issue...")
    
    # Extract information from the issue
    file_paths = extract_file_paths(text)
    error_messages = extract_error_messages(text)
    code_blocks = extract_code_blocks(text)
    issue_type = determine_issue_type(text)
    fix_potential = evaluate_fix_potential(text, issue_type)
    
    # Determine if the issue is fixable
    is_fixable = fix_potential >= 0.6
    
    # Generate an issue summary
    summary = f"Issue type: {issue_type}\n"
    if file_paths:
        summary += f"Affected files: {', '.join(file_paths)}\n"
    if error_messages:
        summary += f"Error messages found: {len(error_messages)}\n"
    if code_blocks:
        summary += f"Code blocks found: {len(code_blocks)}\n"
    summary += f"Fix potential: {fix_potential:.2f}\n"
    
    logger.info(f"Analysis complete: fix_potential={fix_potential:.2f}, is_fixable={is_fixable}")
    
    return {
        "issue_type": issue_type,
        "file_paths": file_paths,
        "error_messages": error_messages,
        "code_blocks": code_blocks,
        "fix_potential": fix_potential,
        "is_fixable": is_fixable,
        "summary": summary,
    }
