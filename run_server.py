#!/usr/bin/env python3
"""
Direct server runner for GitHub Aider Bot.
"""
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment
host = os.getenv("HOST", "0.0.0.0")
port = int(os.getenv("PORT", "8080"))

if __name__ == "__main__":
    print(f"Starting server on {host}:{port}...")
    uvicorn.run(
        "src.app:app",
        host=host,
        port=port,
        reload=False
    )
