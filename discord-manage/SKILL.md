---
name: discord-manage
description: Manage Discord server structure — channels, roles, members, invites, and scheduled events. Uses the discord-cli.py tool to create, edit, delete, and configure server infrastructure via the Discord REST API.
---

# Discord Server Management

This skill enables full management of Discord server infrastructure through the `discord-cli.py` CLI tool.

## IMPORTANT: Always Confirm Before Executing

**Before running any mutating command, you MUST present the exact command to the user and ask for explicit confirmation.** The CLI has a built-in confirmation prompt, but when used programmatically, always show the user what will happen first.

Pattern:
1. Determine what needs to be done
2. Build the exact CLI command
3. **Present the command to the user and explain what it will do**
4. Only execute after user confirms

## Setup

Ensure `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID` are set as environment variables, or run:
```bash
python skills/scripts/discord-cli.py --config
```

## Tool Location

The CLI tool is at: `skills/scripts/discord-cli.py`

## Operations Reference

### Channels (7 operations)
```bash
# List all channels
python skills/scripts/discord-cli.py channels.list

# Get channel details
python skills/scripts/discord-cli.py channels.get --channel_id CHANNEL_ID

# Create channel (type: 0=text, 2=voice, 4=category, 5=news, 13=stage, 15=forum)
python skills/scripts/discord-cli.py channels.create --name "general-chat" --type 0 --topic "Welcome!" --parent_id CATEGORY_ID --yes

# Edit channel
python skills/scripts/discord-cli.py channels.edit --channel_id CHANNEL_ID --name "new-name" --topic "New topic" --yes

# Delete channel
python skills/scripts/discord-cli.py channels.delete --channel_id CHANNEL_ID --yes

# Set permission overwrites (target_type: "role" or "member")
python skills/scripts/discord-cli.py channels.set_permissions --channel_id CHANNEL_ID --target_id ROLE_ID --target_type role --allow "2048" --deny "0" --yes

# Remove permission overwrites
python skills/scripts/discord-cli.py channels.delete_permissions --channel_id CHANNEL_ID --target_id ROLE_ID --yes
```

### Roles (6 operations)
```bash
# List all roles
python skills/scripts/discord-cli.py roles.list

# Get role details
python skills/scripts/discord-cli.py roles.get --role_id ROLE_ID

# Create role (color as decimal integer, e.g. 0xFF0000 = 16711680)
python skills/scripts/discord-cli.py roles.create --name "Moderator" --color 3447003 --hoist true --mentionable true --yes

# Edit role
python skills/scripts/discord-cli.py roles.edit --role_id ROLE_ID --name "New Name" --color 15105570 --yes

# Delete role
python skills/scripts/discord-cli.py roles.delete --role_id ROLE_ID --yes

# Reorder roles (JSON array of {id, position})
python skills/scripts/discord-cli.py roles.reorder --roles '[{"id":"ROLE_ID","position":2}]' --yes
```

### Members (6 operations)
```bash
# List members (max 1000)
python skills/scripts/discord-cli.py members.list --limit 100

# Get member details
python skills/scripts/discord-cli.py members.get --user_id USER_ID

# Search members by username
python skills/scripts/discord-cli.py members.search --query "john" --limit 10

# Edit member (nickname, mute, deaf)
python skills/scripts/discord-cli.py members.edit --user_id USER_ID --nick "NewNick" --yes

# Add role to member
python skills/scripts/discord-cli.py members.add_role --user_id USER_ID --role_id ROLE_ID --yes

# Remove role from member
python skills/scripts/discord-cli.py members.remove_role --user_id USER_ID --role_id ROLE_ID --yes
```

### Invites (4 operations)
```bash
# List all invites
python skills/scripts/discord-cli.py invites.list

# Create invite (max_age in seconds, 0=never; max_uses, 0=unlimited)
python skills/scripts/discord-cli.py invites.create --channel_id CHANNEL_ID --max_age 86400 --max_uses 10 --yes

# Get invite details
python skills/scripts/discord-cli.py invites.get --invite_code ABC123

# Delete/revoke invite
python skills/scripts/discord-cli.py invites.delete --invite_code ABC123 --yes
```

### Events (6 operations)
```bash
# List scheduled events
python skills/scripts/discord-cli.py events.list

# Get event details
python skills/scripts/discord-cli.py events.get --event_id EVENT_ID

# Create event (in a voice channel)
python skills/scripts/discord-cli.py events.create --name "Game Night" --start_time "2025-01-15T20:00:00Z" --channel_id VOICE_CHANNEL_ID --yes

# Create external event
python skills/scripts/discord-cli.py events.create --name "Meetup" --start_time "2025-01-15T20:00:00Z" --end_time "2025-01-15T22:00:00Z" --location "Central Park" --yes

# Edit event
python skills/scripts/discord-cli.py events.edit --event_id EVENT_ID --name "Updated Name" --yes

# Delete event
python skills/scripts/discord-cli.py events.delete --event_id EVENT_ID --yes

# List event attendees
python skills/scripts/discord-cli.py events.list_users --event_id EVENT_ID
```

## Common Workflows

### Set up a new category with channels
1. `channels.create --name "Projects" --type 4` → get category ID
2. `channels.create --name "project-alpha" --type 0 --parent_id CATEGORY_ID`
3. `channels.create --name "project-beta" --type 0 --parent_id CATEGORY_ID`

### Lock a channel to a specific role
1. `roles.list` → find the @everyone role ID
2. `channels.set_permissions --channel_id X --target_id EVERYONE_ROLE_ID --target_type role --deny "2048"` (deny Send Messages)
3. `channels.set_permissions --channel_id X --target_id ALLOWED_ROLE_ID --target_type role --allow "2048"` (allow Send Messages)

## Error Handling

- **403 Forbidden**: Bot lacks permissions or target is above bot's role
- **404 Not Found**: Invalid ID
- **429 Rate Limited**: CLI handles retries automatically
- **50013**: Missing permissions — check bot role position
