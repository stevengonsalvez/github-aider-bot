# Issue Analysis Module

This module is responsible for analyzing GitHub issues to determine if they're fixable and extract relevant information.

## Components

- `issue_analyzer.py`: Main issue analysis functionality

## Functionality

The issue analyzer:

1. Extracts file paths mentioned in the issue
2. Identifies error messages and stack traces
3. Extracts code blocks
4. Determines the issue type (bug, feature, question)
5. Evaluates the potential for an automated fix
6. Provides a summary of the analysis

## Usage

```python
from analysis.issue_analyzer import analyze_issue

# Analyze an issue
issue_text = "There's a bug in app.py that causes an error..."
analysis_result = analyze_issue(issue_text)

# Use the results
if analysis_result["is_fixable"]:
    print(f"Issue is fixable with potential {analysis_result['fix_potential']}")
    print(f"Affected files: {analysis_result['file_paths']}")
    print(f"Error messages: {analysis_result['error_messages']}")
```
