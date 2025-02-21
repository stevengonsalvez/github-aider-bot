# GitHub Aider Bot

A GitHub bot that analyzes issues, uses Aider to implement fixes, and creates pull requests.

## Features

- Automatically detects actionable issues
- Uses Aider to generate fixes for bugs
- Creates pull requests with appropriate descriptions
- Updates issues with progress

## Setup

1. Create a GitHub App
2. Install the app on your repositories
3. Configure the bot using `.github/aider-bot.yml`

## Configuration

Create a `.github/aider-bot.yml` file in your repository:

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

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/github-aider-bot.git
cd github-aider-bot

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your GitHub App credentials

# Run the bot
python src/app.py
```

## License

MIT
