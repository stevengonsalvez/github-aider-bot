# GitHub Aider Bot Architecture

This document describes the architecture of the GitHub Aider Bot, its components, and how they interact.

## System Overview

The GitHub Aider Bot is designed to automatically fix issues in GitHub repositories using Aider, an AI-powered coding assistant. The bot works by:

1. Receiving webhooks from GitHub when issues are created or updated
2. Analyzing issues to determine if they're fixable
3. Using Aider to implement changes
4. Creating pull requests with the fixes

## Architecture Diagram

```
┌─────────────┐    Webhooks    ┌────────────────┐
│             ├───────────────►│                │
│   GitHub    │                │  Webhook API   │
│             │◄───────────────┤  (FastAPI)     │
└─────────────┘   API Calls    └────────┬───────┘
                                        │
                                        ▼
                                ┌────────────────┐         ┌─────────────┐
                                │                │ Analyze │             │
                                │  Issue         ├────────►│  Issue      │
                                │  Processor     │         │  Analyzer   │
                                │                │◄────────┤             │
                                └────────┬───────┘         └─────────────┘
                                        │
                                        ▼
                                ┌────────────────┐         ┌─────────────┐
                                │                │  Git    │             │
                                │  Aider         ├────────►│  Git        │
                                │  Integration   │         │  Operations │
                                │                │◄────────┤             │
                                └────────┬───────┘         └─────────────┘
                                        │
                                        ▼
                                ┌────────────────┐
                                │                │
                                │  PR Creation   │
                                │                │
                                └────────────────┘
```

## Core Components

### 1. Webhook API (FastAPI)

- Receives and validates GitHub webhooks
- Handles webhook authentication
- Dispatches events to appropriate handlers
- Provides health check and API documentation

**Key Files**: `src/app.py`

### 2. GitHub Integration

- Manages GitHub App authentication
- Handles repository access
- Retrieves repository configuration
- Interacts with GitHub API

**Key Files**: `src/github/app.py`, `src/github/issues.py`, `src/github/pr.py`

### 3. Issue Analysis

- Extracts relevant information from issues
- Identifies issue types (bug, feature, question)
- Determines if an issue is fixable
- Prepares context for Aider

**Key Files**: `src/analysis/issue_analyzer.py`

### 4. Aider Integration

- Formats issue information for Aider
- Invokes Aider CLI or API
- Processes Aider's responses
- Extracts file changes

**Key Files**: `src/aider/integration.py`

### 5. Git Operations

- Clones repositories
- Creates branches
- Commits changes
- Pushes to GitHub

**Key Files**: `src/git/operations.py`

### 6. Configuration

- Loads environment variables
- Parses repository-specific configuration
- Provides defaults

**Key Files**: `src/config.py`

## Data Flow

1. **Webhook Receipt**:
   - GitHub sends a webhook when an issue is created or updated
   - The Webhook API validates the webhook signature
   - The event is dispatched to the appropriate handler

2. **Issue Analysis**:
   - The issue content is parsed and analyzed
   - The bot determines if the issue is fixable
   - Relevant information is extracted (file paths, error messages, etc.)

3. **Repository Setup**:
   - The bot clones the repository
   - A new branch is created for the fix

4. **Aider Integration**:
   - Issue details are formatted for Aider
   - Aider is invoked to generate fixes
   - Aider's output is processed to extract changes

5. **Change Application**:
   - Changes are applied to the repository
   - Changes are committed to the branch
   - The branch is pushed to GitHub

6. **PR Creation**:
   - A pull request is created with the changes
   - The PR is linked to the original issue
   - A comment is added to the issue with the PR link

## Deployment Options

### 1. Serverless (AWS Lambda)

- Webhook API runs as a Lambda function
- Git operations and Aider run in containers (ECS/Fargate)
- Job state stored in DynamoDB
- Job coordination through SQS

### 2. Container-based (Kubernetes)

- All components run in containers
- Horizontal scaling for webhook handling
- Vertical scaling for Aider jobs
- State management through Redis/MongoDB

### 3. Traditional Server

- Single server deployment
- Simpler setup for small-scale usage
- Limited scalability

## Configuration

### Environment Variables

The bot uses environment variables for configuration:

- GitHub App credentials (`GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY_PATH`, etc.)
- Aider configuration (`AIDER_BINARY_PATH`, `AIDER_MODEL`, `AIDER_API_KEY`)
- Server settings (`HOST`, `PORT`, `DEBUG`)

### Repository-specific Configuration

Each repository can have a `.github/aider-bot.yml` file:

```yaml
labels:
  process: ["bug", "fix-me"]
  ignore: ["discussion", "wontfix"]
files:
  include: ["src/**", "lib/**"]
  exclude: ["docs/**", "*.md"]
pr:
  reviewers: ["team-maintainers"]
  draft: true
```

## Security Considerations

- **GitHub Authentication**: Uses GitHub App JWT authentication
- **Secret Management**: Environment variables and secure storage
- **Input Validation**: All webhook payloads are validated
- **Code Isolation**: Aider runs in isolated environments
- **Least Privilege**: GitHub App uses minimal required permissions

## Testing Strategy

- **Unit Tests**: Test individual components
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **CI/CD**: Automated testing on pull requests

## Future Enhancements

- **Learning from Feedback**: Track PR acceptance rates
- **Pre-screening**: ML model to predict fix success probability
- **Multi-repository Context**: Consider code across repositories
- **User Interaction**: Interactive mode for complex issues
- **Performance Optimization**: Caching and parallel processing
