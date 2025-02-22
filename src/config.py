"""
Configuration module for the GitHub Aider Bot.
"""
import os
from pathlib import Path
from typing import Optional, Dict, List, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = Field(default=os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default=int(os.getenv("PORT", "8000")))
    debug: bool = Field(default=os.getenv("DEBUG", "False").lower() == "true")


class GitHubConfig(BaseModel):
    """GitHub App configuration."""
    app_id: int = Field(default=int(os.getenv("GITHUB_APP_ID", "0") or "0"))
    private_key_path: str = Field(default=os.getenv("GITHUB_PRIVATE_KEY_PATH", ""))
    webhook_secret: str = Field(default=os.getenv("GITHUB_WEBHOOK_SECRET", ""))
    app_name: str = Field(default=os.getenv("GITHUB_APP_NAME", "aider-bot"))

    @property
    def private_key(self) -> str:
        """Read the private key from the file."""
        if not self.private_key_path:
            return ""
            
        try:
            with open(self.private_key_path, "r") as key_file:
                return key_file.read()
        except Exception as e:
            print(f"Warning: Failed to read private key: {e}")
            return ""


class AiderConfig(BaseModel):
    """Configuration for Aider integration."""
    binary_path: str = "aider"
    model: str = "gpt-4-turbo-preview"  # Updated to latest model
    api_key: Optional[str] = None


class RepoConfig(BaseModel):
    """Repository-specific configuration."""
    labels: Dict[str, List[str]] = Field(
        default={"process": ["bug", "fix-me"], "ignore": ["discussion", "wontfix"]}
    )
    files: Dict[str, List[str]] = Field(
        default={"include": ["**"], "exclude": []}
    )
    pr: Dict[str, Any] = Field(
        default={"draft": False, "reviewers": []}
    )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "RepoConfig":
        """Create config from YAML content."""
        import yaml
        try:
            config_dict = yaml.safe_load(yaml_content) or {}
            return cls(**config_dict)
        except Exception as e:
            print(f"Error parsing repo config: {e}")
            return cls()


class Config:
    """Main configuration class."""
    def __init__(self):
        self.server = ServerConfig()
        self.github = GitHubConfig()
        self.aider = AiderConfig()

    def get_repo_config(self, repo_config_content: Optional[str] = None) -> RepoConfig:
        """Get repository-specific configuration."""
        if repo_config_content:
            return RepoConfig.from_yaml(repo_config_content)
        return RepoConfig()


# Create a singleton instance
config = Config()
