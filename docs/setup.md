# GitHub Aider Bot Setup Guide

This guide will walk you through setting up the GitHub Aider Bot for your repositories.

## Prerequisites

- GitHub account with admin access to the repositories
- Python 3.8 or higher
- OpenAI API key for Aider

## Step 1: Create a GitHub App

1. Go to your GitHub Settings > Developer settings > GitHub Apps
2. Click "New GitHub App"
3. Fill in the details:
   - Name: "Aider Bot" (or your preferred name)
   - Homepage URL: Your project URL or GitHub profile
   - Webhook URL: Your bot's webhook endpoint (e.g., `https://your-bot-domain.com/webhook`)
   - Webhook secret: Generate a secure random string
4. Permissions:
   - Repository permissions:
     - Contents: Read & Write
     - Issues: Read & Write
     - Pull requests: Read & Write
     - Metadata: Read-only
   - Subscribe to events:
     - Issues
     - Issue comment
     - Pull request
5. Click "Create GitHub App"

## Step 2: Generate a Private Key

1. After creating the app, scroll down to the "Private keys" section
2. Click "Generate a private key"
3. Save the downloaded key file (`.pem`) securely

## Step 3: Install the App to Your Repositories

1. Go to your GitHub App's settings page
2. Click "Install App" in the sidebar
3. Choose which repositories to install the app on
4. Click "Install"

## Step 4: Configure the Bot

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/github-aider-bot.git
   cd github-aider-bot
   ```

2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

3. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your settings:
   ```
   GITHUB_APP_ID=your_app_id
   GITHUB_PRIVATE_KEY_PATH=path/to/your-private-key.pem
   GITHUB_WEBHOOK_SECRET=your_webhook_secret
   GITHUB_APP_NAME=your_app_name
   
   AIDER_BINARY_PATH=aider
   AIDER_MODEL=gpt-4-turbo
   AIDER_API_KEY=your_openai_api_key
   ```

## Step 5: Deploy the Bot

### Option 1: Run Locally with Ngrok

1. Install ngrok: https://ngrok.com/download
2. Start the bot:
   ```bash
   python src/app.py
   ```
3. In another terminal, start ngrok:
   ```bash
   ngrok http 8000
   ```
4. Update your GitHub App's webhook URL with the ngrok URL

### Option 2: Deploy to a Server

1. Set up a server with Python installed
2. Clone the repository and configure as above
3. Set up a service to run the bot (systemd, supervisor, etc.)
4. Configure a reverse proxy (nginx, apache) to forward requests to the bot
5. Update your GitHub App's webhook URL with your server URL

### Option 3: Deploy to AWS Lambda

1. Update the deployment configuration in the `.github/workflows/ci.yml` file
2. Push to GitHub to trigger the deployment workflow
3. Set up API Gateway to forward requests to your Lambda function
4. Update your GitHub App's webhook URL with the API Gateway URL

## Step 6: Repository Configuration

Create a `.github/aider-bot.yml` file in each repository where you want to customize the bot's behavior:

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

## Step 7: Test the Bot

1. Create a new issue with the label "fix-me"
2. Wait for the bot to analyze the issue
3. The bot will create a PR if it can fix the issue
4. Review and merge the PR

## Troubleshooting

- Check the logs for any errors
- Verify that the GitHub App has the correct permissions
- Ensure the webhook URL is accessible from GitHub
- Confirm that your OpenAI API key is valid and has sufficient credits
