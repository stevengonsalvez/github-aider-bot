"""
GitHub App integration module.
"""
import time
import logging
from typing import Optional, Dict, Any

import jwt
import requests
from github import Github
from github.GithubIntegration import GithubIntegration

from config import config

# Configure logging
logger = logging.getLogger(__name__)


def create_jwt() -> str:
    """
    Create a JWT for GitHub App authentication.
    
    Returns:
        JWT token string
    """
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + (10 * 60),  # 10 minutes expiration
        "iss": config.github.app_id
    }
    
    private_key = config.github.private_key
    token = jwt.encode(payload, private_key, algorithm="RS256")
    
    return token


def get_installation_id(owner: str, repo: str) -> Optional[int]:
    """
    Get the installation ID for a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Installation ID if found, None otherwise
    """
    token = create_jwt()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{owner}/{repo}/installation"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("id")
    except Exception as e:
        logger.error(f"Failed to get installation ID: {e}")
        return None


def get_installation_token(installation_id: int) -> Optional[str]:
    """
    Get an installation access token.
    
    Args:
        installation_id: GitHub App installation ID
        
    Returns:
        Installation token if successful, None otherwise
    """
    token = create_jwt()
    integration = GithubIntegration(config.github.app_id, config.github.private_key)
    
    try:
        access_token = integration.get_access_token(installation_id)
        return access_token.token
    except Exception as e:
        logger.error(f"Failed to get installation token: {e}")
        return None


def get_installation_client(owner: str, repo: str) -> Optional[Github]:
    """
    Get a GitHub client for a repository installation.
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        GitHub client if successful, None otherwise
    """
    installation_id = get_installation_id(owner, repo)
    if not installation_id:
        return None
    
    token = get_installation_token(installation_id)
    if not token:
        return None
    
    return Github(token)


def get_repo_config(owner: str, repo: str, client: Optional[Github] = None) -> Dict[str, Any]:
    """
    Get repository configuration from .github/aider-bot.yml.
    
    Args:
        owner: Repository owner
        repo: Repository name
        client: GitHub client (optional)
        
    Returns:
        Repository configuration
    """
    if client is None:
        client = get_installation_client(owner, repo)
        if client is None:
            return config.get_repo_config().dict()
    
    try:
        repository = client.get_repo(f"{owner}/{repo}")
        content = repository.get_contents(".github/aider-bot.yml")
        config_content = content.decoded_content.decode("utf-8")
        return config.get_repo_config(config_content).dict()
    except Exception as e:
        logger.info(f"No repository configuration found or error: {e}")
        return config.get_repo_config().dict()
