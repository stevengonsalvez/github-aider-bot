"""
Main application module for the GitHub Aider Bot.
"""
import hmac
import json
import logging
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from config import config
from github.app import get_installation_client
from github.issues import process_issue_event
from github.pr import create_pull_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(title="GitHub Aider Bot")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_webhook(request: Request) -> Optional[Dict[str, Any]]:
    """
    Verify that the webhook came from GitHub.
    
    Args:
        request: The incoming request
        
    Returns:
        The parsed webhook payload if valid
        
    Raises:
        HTTPException: If the webhook signature is invalid
    """
    if not config.github.webhook_secret:
        logger.warning("Webhook secret not configured, skipping verification")
        body = await request.body()
        return json.loads(body)
    
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    body = await request.body()
    
    # Verify signature
    sha_name, signature = signature.split("=")
    if sha_name != "sha256":
        raise HTTPException(status_code=401, detail="Invalid signature hash algorithm")
    
    mac = hmac.new(
        config.github.webhook_secret.encode(), 
        msg=body, 
        digestmod="sha256"
    )
    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return json.loads(body)


@app.post("/webhook")
async def webhook(
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any] = Depends(verify_webhook),
):
    """Handle GitHub webhook events."""
    event_type = payload.get("action")
    if not event_type:
        return {"status": "ignored", "reason": "No action specified"}
    
    # Check if it's an issue event
    if "issue" in payload:
        # Only process newly opened issues or issues with specific labels
        if event_type in ["opened", "labeled"]:
            # Process the issue in the background
            background_tasks.add_task(
                process_issue_event, 
                payload
            )
            return {
                "status": "processing",
                "event_type": event_type,
                "issue_number": payload["issue"]["number"],
            }
    
    return {"status": "ignored", "event_type": event_type}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "GitHub Aider Bot",
        "version": "0.1.0",
        "docs": "/docs",
    }


def main():
    """Run the server."""
    uvicorn.run(
        "src.app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
    )


if __name__ == "__main__":
    main()
