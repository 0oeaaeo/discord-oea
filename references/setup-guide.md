# Discord CLI Setup Guide

## Prerequisites

1. **Python 3.10+** with `httpx` installed (`pip install httpx`)
2. A **Discord Bot** with the following configured:
   - Bot created at https://discord.com/developers/applications
   - "Server Members Intent" + "Message Content Intent" enabled
   - Bot invited to your server with Administrator permissions
   - Invite URL: `https://discord.com/api/oauth2/authorize?client_id=YOUR_APP_ID&permissions=8&scope=bot`

## Configuration

Set environment variables (preferred):
```bash
export DISCORD_BOT_TOKEN="your-bot-token"
export DISCORD_GUILD_ID="your-server-id"
```

Or run interactive setup:
```bash
python discord-cli.py --config
```
This saves to `~/.discord-cli.json`.

## Getting Your Server ID

1. Enable Developer Mode in Discord: Settings → Advanced → Developer Mode
2. Right-click your server name → "Copy Server ID"

## Quick Start

```bash
# See all operations
python discord-cli.py --discover

# See parameters for an operation
python discord-cli.py --schema messages.send

# Run a read-only operation (no confirmation needed)
python discord-cli.py channels.list

# Run a mutating operation (confirmation prompted)
python discord-cli.py messages.send --channel_id 123456 --content "Hello!"

# Skip confirmation with --yes
python discord-cli.py messages.send --channel_id 123456 --content "Hello!" --yes

# JSON output for piping
python discord-cli.py channels.list --json
```

## Security Notes

- **Never commit your bot token** to version control
- The bot can only manage users/roles **below** its own role in the hierarchy
- Rate limits are enforced by Discord; batch operations include automatic delays
