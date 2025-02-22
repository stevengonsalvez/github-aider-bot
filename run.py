#!/usr/bin/env python3
"""
Simple script to run the GitHub Aider Bot.
"""
import os
import sys

print("Starting GitHub Aider Bot...")

# Add the project directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
print(f"Python path: {sys.path}")

try:
    # Run the main function
    print("Importing main function...")
    from src.app import main
    print("Starting server...")
    main()
except Exception as e:
    print(f"Error starting server: {e}")
    import traceback
    traceback.print_exc()
