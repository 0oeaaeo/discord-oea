---
name: discord-moderate
description: Discord server moderation — kick, ban, timeout, automod rules, audit logs, voice controls, and bulk bans. Uses discord-cli.py for all moderation actions via the Discord REST API.
---

# Discord Server Moderation

This skill covers all moderation capabilities through `discord-cli.py`.

## IMPORTANT: Always Confirm Before Executing

**Moderation actions are irreversible or high-impact. ALWAYS present the exact command to the user and explain the consequences before executing.** Never auto-execute moderation commands.

## Operations Reference

### Moderation (7 operations)
```bash
# Kick a member
python skills/scripts/discord-cli.py moderation.kick --user_id USER_ID --reason "Rule violation" --yes

# Ban a member (delete_message_days: 0-7, days of messages to delete)
python skills/scripts/discord-cli.py moderation.ban --user_id USER_ID --reason "Spam" --delete_message_days 1 --yes

# Unban a user
python skills/scripts/discord-cli.py moderation.unban --user_id USER_ID --yes

# List bans
python skills/scripts/discord-cli.py moderation.list_bans --limit 100

# Check if user is banned
python skills/scripts/discord-cli.py moderation.get_ban --user_id USER_ID

# Timeout a member (duration in seconds, max 28 days = 2419200)
python skills/scripts/discord-cli.py moderation.timeout --user_id USER_ID --duration_seconds 3600 --reason "Cool down" --yes

# Remove timeout
python skills/scripts/discord-cli.py moderation.remove_timeout --user_id USER_ID --yes
```

### Bulk Ban (1 operation)
```bash
# Ban multiple users at once (max 200 per call)
python skills/scripts/discord-cli.py bulk_ban.execute --user_ids '["ID1","ID2","ID3"]' --reason "Raid" --delete_message_seconds 86400 --yes
```

### AutoMod Rules (5 operations)
```bash
# List automod rules
python skills/scripts/discord-cli.py automod.list

# Get rule details
python skills/scripts/discord-cli.py automod.get --rule_id RULE_ID

# Create rule (event_type: 1=MESSAGE_SEND; trigger_type: 1=KEYWORD, 3=SPAM, 4=KEYWORD_PRESET, 5=MENTION_SPAM)
# Actions: type 1=BLOCK_MESSAGE, 2=SEND_ALERT_MESSAGE, 3=TIMEOUT
python skills/scripts/discord-cli.py automod.create \
  --name "Block Slurs" \
  --event_type 1 \
  --trigger_type 1 \
  --trigger_metadata '{"keyword_filter":["badword1","badword2"]}' \
  --actions '[{"type":1}]' \
  --enabled true --yes

# Edit rule
python skills/scripts/discord-cli.py automod.edit --rule_id RULE_ID --enabled false --yes

# Delete rule
python skills/scripts/discord-cli.py automod.delete --rule_id RULE_ID --yes
```

### Audit Log (1 operation)
```bash
# Query audit log (action_type: see Discord docs for codes)
python skills/scripts/discord-cli.py audit_log.list --limit 50
python skills/scripts/discord-cli.py audit_log.list --user_id USER_ID --action_type 22 --limit 10
```

### Voice Controls (2 operations)
```bash
# Move member to different voice channel
python skills/scripts/discord-cli.py voice.move_member --user_id USER_ID --channel_id VOICE_CHANNEL_ID --yes

# Disconnect member from voice
python skills/scripts/discord-cli.py voice.disconnect_member --user_id USER_ID --yes
```

## Common Workflows

### Investigate a user's recent activity
1. `audit_log.list --user_id USER_ID --limit 20`
2. Review actions, then decide on moderation

### Set up anti-spam automod
1. `automod.create --name "Anti Spam" --event_type 1 --trigger_type 3 --actions '[{"type":1},{"type":3,"metadata":{"duration_seconds":60}}]' --enabled true`

### Mass-ban raid accounts
1. Identify user IDs from audit log or member list
2. `bulk_ban.execute --user_ids '["id1","id2",...]' --reason "Raid" --delete_message_seconds 3600`

## Timeout Duration Reference
| Duration | Seconds |
|----------|---------|
| 1 minute | 60 |
| 1 hour | 3600 |
| 1 day | 86400 |
| 1 week | 604800 |
| 28 days (max) | 2419200 |
