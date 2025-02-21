# GitHub Aider Bot Usage Guide

This guide explains how to use the GitHub Aider Bot effectively with your repositories.

## Overview

The GitHub Aider Bot automatically helps fix issues in your repository using Aider, an AI-powered coding assistant. When an issue is created or labeled appropriately, the bot will:

1. Analyze the issue to determine if it's something that can be fixed automatically
2. If fixable, create a new branch
3. Use Aider to implement changes
4. Create a pull request with the fixes
5. Update the issue with the PR link

## Creating Fixable Issues

To maximize the bot's effectiveness, follow these guidelines when creating issues:

### Do's:

- **Be specific**: Clearly describe the problem
- **Include error messages**: Copy and paste the exact error output
- **Reference file paths**: Mention the specific files that need to be fixed
- **Include code samples**: Add relevant code snippets using code blocks
- **Provide steps to reproduce**: List clear steps to reproduce the issue

### Don'ts:

- **Be vague**: "The app doesn't work" doesn't give the bot enough information
- **Request complex features**: Brand new features usually need human developers
- **Discuss multiple issues**: Each issue should focus on a single problem
- **Forget context**: Provide necessary background for the bot to understand the issue

### Example of a Good Issue:

```
Title: Fix KeyError in user_profile.py when profile is None

Description:
When a user has no profile set up, the app crashes with the following error:

```
File "app/user_profile.py", line 42, in get_profile
    return user['profile']['name']
KeyError: 'profile'
```

Steps to reproduce:
1. Create a new user account
2. Don't fill out the profile
3. Visit the profile page

The issue is in user_profile.py where it tries to access the 'profile' key without checking if it exists. It should handle the None case gracefully.
```

## Configuration

### Repository Configuration

Create a `.github/aider-bot.yml` file in your repository to customize the bot's behavior:

```yaml
labels:
  process: ["bug", "fix-me"]  # Labels that trigger the bot
  ignore: ["discussion", "wontfix"]  # Labels that will be ignored by the bot
files:
  include: ["src/**", "lib/**"]  # Files to include for analysis
  exclude: ["docs/**", "*.md"]  # Files to exclude from analysis
pr:
  reviewers: ["team-maintainers"]  # Automatic PR reviewers
  draft: true  # Create PRs as drafts
```

### Using Labels

You can control which issues the bot processes using labels:

- Add a label from the `process` list (e.g., "fix-me") to have the bot process an issue
- Add a label from the `ignore` list (e.g., "wontfix") to prevent the bot from processing an issue

## Pull Request Workflow

When the bot creates a pull request:

1. **Review the changes**: Check the PR to verify that the bot's fixes are appropriate
2. **Provide feedback**: Comment on specific lines if adjustments are needed
3. **Merge or close**: Merge the PR if the fixes are good, or close it if not
4. **Issue status**: The original issue will be closed automatically when the PR is merged

## Customizing PR Creation

You can customize how pull requests are created using the `pr` section in your configuration:

```yaml
pr:
  reviewers: ["username1", "username2"]  # Automatically request these reviewers
  draft: true  # Create PRs as drafts
  labels: ["bot-fix", "automated"]  # Apply these labels to the PR
```

## Handling Complex Issues

For complex issues that the bot can't fully fix:

1. The bot will still attempt a partial fix
2. It will comment on what it was able to do and what remains
3. A human developer can then:
   - Build on the bot's PR
   - Create a new PR that addresses the full issue
   - Provide more specific guidance in the issue for another bot attempt

## Best Practices

1. **Start small**: Begin with simple, well-defined bugs
2. **Provide feedback**: Let the bot know what worked and what didn't
3. **Be patient**: The bot is learning from each interaction
4. **Review carefully**: Always review the bot's PRs before merging
5. **Iterative approach**: Sometimes multiple small fixes are better than one big fix

## Limitations

The bot works best on:

- Simple bugs with clear error messages
- Issues with obvious fixes
- Well-documented code
- Repositories with good test coverage

It may struggle with:

- Complex architectural changes
- Bugs without clear error messages
- Issues requiring deep domain knowledge
- Highly interdependent code changes

## Getting Help

If you encounter any issues with the bot:

1. Check the bot's logs for error messages
2. Review the documentation
3. Contact the project maintainers
