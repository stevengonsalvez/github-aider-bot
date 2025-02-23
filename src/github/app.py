"""
GitHub App integration module.
"""
import jwt
import time
import logging
from typing import Optional, Dict, Any, Tuple

import requests
from github import GithubIntegration, Github
import aiohttp
from gidgethub.aiohttp import GitHubAPI

from src.config import config

# Configure logging
logger = logging.getLogger(__name__)


def create_jwt() -> str:
    """
    Create a JWT for GitHub App authentication.
    """
    try:
        if not config.github.app_id:
            logger.error("Missing GitHub App ID")
            return ""
        if not config.github.private_key:
            logger.error("Missing GitHub App private key")
            return ""
            
        logger.debug(f"Creating JWT with app_id: {config.github.app_id}")
        
        now = int(time.time())
        payload = {
            "iat": now,
            "exp": now + (10 * 60),  # 10 minutes expiration
            "iss": str(config.github.app_id)  # Ensure app_id is string
        }
        
        logger.debug(f"JWT payload: {payload}")
        logger.debug(f"Private key length: {len(config.github.private_key)}")
        
        token = jwt.encode(
            payload, 
            config.github.private_key, 
            algorithm="RS256"
        )
        
        # If token is bytes, decode to string
        if isinstance(token, bytes):
            token = token.decode('utf-8')
            
        logger.debug(f"Generated JWT token (first 10 chars): {token[:10]}...")
        return token
        
    except Exception as e:
        logger.exception(f"Error creating JWT: {e}")
        return ""


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


async def get_installation_client(owner: str, repo: str) -> Tuple[Github, str]:
    """Get a GitHub client and access token for an installation."""
    try:
        # Create GitHub Integration
        integration = GithubIntegration(
            config.github.app_id,
            config.github.private_key
        )
        
        # Get installation
        installation = integration.get_repo_installation(owner, repo)
        
        # Get access token
        access_token = integration.get_access_token(installation.id)
        
        # Create GitHub client with installation token
        return Github(access_token.token), access_token.token
        
    except Exception as e:
        logger.exception(f"Error getting installation client: {e}")
        return None, None


async def get_repo_config(owner: str, repo: str, client: GitHubAPI) -> Dict[str, Any]:
    """
    Get repository configuration from .github/aider-bot.yml
    """
    try:
        # Try to get config file
        config_content = await client.getitem(
            f"/repos/{owner}/{repo}/contents/.github/aider-bot.yml",
            accept="application/vnd.github.v3+json"
        )
        
        if config_content:
            import yaml
            import base64
            
            # Decode content
            content = base64.b64decode(config_content["content"]).decode()
            
            # Parse YAML
            return yaml.safe_load(content) or {}
            
    except Exception as e:
        logger.info(f"No config found for {owner}/{repo}: {e}")
    
    # Return default config if none found
    return {}
