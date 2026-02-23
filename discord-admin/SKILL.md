---
name: discord-admin
description: Discord server administration — guild settings, member pruning, onboarding, welcome screen, slash commands, integrations, widget, vanity URL, and server templates. Uses discord-cli.py for admin operations via the Discord REST API.
---

# Discord Server Administration

This skill covers server-level administration through `discord-cli.py`.

## IMPORTANT: Always Confirm Before Executing

**Administrative operations can affect the entire server. ALWAYS present the exact command to the user and explain consequences before executing.** This is especially critical for guild.edit, guild.prune, and template operations.

## Operations Reference

### Guild / Server (4 operations)
```bash
# Get server info
python skills/scripts/discord-cli.py guild.get

# Edit server settings
python skills/scripts/discord-cli.py guild.edit --name "New Server Name" --description "A great server" --verification_level 2 --yes

# Check prune count (dry run)
python skills/scripts/discord-cli.py guild.get_prune_count --days 30

# Execute prune (DESTRUCTIVE - removes inactive members)
python skills/scripts/discord-cli.py guild.prune --days 30 --compute_prune_count true --yes
```

### Onboarding (3 operations)
```bash
python skills/scripts/discord-cli.py onboarding.get
python skills/scripts/discord-cli.py onboarding.edit --enabled true --default_channel_ids '["CID1","CID2"]' --yes
python skills/scripts/discord-cli.py onboarding.create_prompt --title "Pick your interests" --options '[{"title":"Gaming","channel_ids":["CID"]}]' --yes
```

### Welcome Screen (2 operations)
```bash
python skills/scripts/discord-cli.py welcome_screen.get
python skills/scripts/discord-cli.py welcome_screen.edit --enabled true --description "Welcome!" --welcome_channels '[{"channel_id":"CID","description":"Start here","emoji_name":"👋"}]' --yes
```

### Slash Commands (5 operations)
```bash
python skills/scripts/discord-cli.py commands.list_global
python skills/scripts/discord-cli.py commands.list_guild
python skills/scripts/discord-cli.py commands.create --name "ping" --description "Check bot latency" --guild_only true --yes
python skills/scripts/discord-cli.py commands.edit --command_id CMD_ID --description "Updated description" --yes
python skills/scripts/discord-cli.py commands.delete --command_id CMD_ID --guild_only true --yes
```

### Integrations (2 operations)
```bash
python skills/scripts/discord-cli.py integrations.list
python skills/scripts/discord-cli.py integrations.delete --integration_id IID --yes
```

### Widget (3 operations)
```bash
python skills/scripts/discord-cli.py widget.get
python skills/scripts/discord-cli.py widget.get_data
python skills/scripts/discord-cli.py widget.edit --enabled true --channel_id CID --yes
```

### Vanity URL (2 operations)
```bash
python skills/scripts/discord-cli.py vanity.get
python skills/scripts/discord-cli.py vanity.edit --code "myserver" --yes
```

### Templates (6 operations)
```bash
python skills/scripts/discord-cli.py templates.list
python skills/scripts/discord-cli.py templates.get --template_code CODE
python skills/scripts/discord-cli.py templates.create --name "My Template" --description "Server template" --yes
python skills/scripts/discord-cli.py templates.sync --template_code CODE --yes
python skills/scripts/discord-cli.py templates.edit --template_code CODE --name "Updated" --yes
python skills/scripts/discord-cli.py templates.delete --template_code CODE --yes
```

## Verification Level Reference
| Level | Description |
|-------|-------------|
| 0 | None |
| 1 | Low (verified email) |
| 2 | Medium (registered 5+ min) |
| 3 | High (member 10+ min) |
| 4 | Very High (verified phone) |
