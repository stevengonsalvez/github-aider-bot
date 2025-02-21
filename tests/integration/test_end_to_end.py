"""
End-to-end integration tests for the GitHub Aider Bot.
"""
import json
import logging
import os
import time
import unittest
from unittest.mock import patch, MagicMock

import pytest
import requests
from fastapi.testclient import TestClient

# Set up logging
logging.basicConfig(level=logging.INFO)

# Import app
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from app import app
from config import config
from github.issues import process_issue_event
from aider.integration import run_aider_on_issue


class TestEndToEnd(unittest.TestCase):
    """End-to-end integration tests."""
    
    def setUp(self):
        """Set up the test client."""
        self.client = TestClient(app)
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_root(self):
        """Test the root endpoint."""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "app" in response.json()
        assert "version" in response.json()
    
    @pytest.mark.skipif(not os.environ.get("GITHUB_APP_ID"), reason="No GitHub App ID")
    def test_webhook_handling(self):
        """Test webhook handling."""
        # Create a mock webhook payload
        payload = {
            "action": "opened",
            "issue": {
                "number": 1,
                "title": "Test Issue",
                "body": "This is a test issue with an error in app.py.",
                "html_url": "https://github.com/test/repo/issues/1",
                "user": {
                    "login": "test-user"
                },
                "labels": [],
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
            },
            "repository": {
                "full_name": "test/repo",
                "clone_url": "https://github.com/test/repo.git",
            }
        }
        
        # Mock the verify_webhook function to always return the payload
        with patch('app.verify_webhook', return_value=payload):
            response = self.client.post("/webhook", json=payload)
            assert response.status_code == 200
            assert response.json()["status"] == "processing"
            assert response.json()["issue_number"] == 1
    
    @pytest.mark.skipif(not os.environ.get("AIDER_API_KEY"), reason="No Aider API key")
    def test_aider_integration(self):
        """Test Aider integration."""
        # Mock issue details
        issue_details = {
            "number": 1,
            "title": "Fix the bug in app.py",
            "body": "There's a bug in app.py that causes an error when processing webhooks.",
            "file_paths": ["app.py"],
            "error_messages": ["KeyError: 'action'"],
            "code_blocks": ["def webhook_handler(payload):\n    action = payload['action']\n    return action"],
            "is_fixable": True,
            "fix_potential": 0.8,
        }
        
        # Mock repo config
        repo_config = {
            "labels": {
                "process": ["bug", "fix-me"],
                "ignore": ["discussion", "wontfix"]
            },
            "files": {
                "include": ["**"],
                "exclude": []
            },
            "pr": {
                "draft": False,
                "reviewers": []
            }
        }
        
        # Create a temp directory with a mock repo
        import tempfile
        import os
        import shutil
        
        repo_dir = tempfile.mkdtemp(prefix="aider-bot-test-")
        try:
            # Create a mock app.py file with a bug
            os.makedirs(os.path.join(repo_dir, "src"), exist_ok=True)
            with open(os.path.join(repo_dir, "src", "app.py"), "w") as f:
                f.write("""
def webhook_handler(payload):
    # This will raise a KeyError if 'action' is not in payload
    action = payload['action']
    return action
""")
            
            # Mock the run_aider_on_issue function to not actually run Aider but return a mock fix
            with patch('aider.integration.run_aider_on_issue', return_value=(True, {
                "src/app.py": """
diff --git a/src/app.py b/src/app.py
index 1234567..890abcd 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,4 +1,5 @@
 def webhook_handler(payload):
-    # This will raise a KeyError if 'action' is not in payload
-    action = payload['action']
+    # Check if 'action' is in payload to avoid KeyError
+    action = payload.get('action', None)
+    if action is None:
+        return None
     return action
"""
            })):
                # Test the fix issue function
                from github.issues import fix_issue
                
                # Mock the repository and issue objects
                repo = MagicMock()
                repo.clone_url = "https://github.com/test/repo.git"
                
                issue = MagicMock()
                issue.number = 1
                
                # Mock other functions that would interact with GitHub
                with patch('github.pr.create_pull_request', return_value="https://github.com/test/repo/pull/1"):
                    with patch('git.operations.checkout_branch', return_value=repo_dir):
                        with patch('git.operations.commit_changes', return_value=True):
                            # Run the fix_issue function
                            from github.issues import fix_issue
                            fix_issue(repo, issue, issue_details, "fix/issue-1", repo_config)
                            
                            # Verify that the issue.create_comment was called with success message
                            assert any("✅" in call[0][0] for call in issue.create_comment.call_args_list)
        
        finally:
            # Clean up the temp directory
            shutil.rmtree(repo_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
