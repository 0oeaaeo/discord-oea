---
name: discord-communicate
description: Discord messaging and communication — send/edit/delete messages, reactions, threads, webhooks, DMs, and polls. Uses discord-cli.py to manage all communication channels via the Discord REST API.
---

# Discord Communication

This skill covers all messaging and communication operations through `discord-cli.py`.

## IMPORTANT: Always Confirm Before Executing

**Before sending messages, DMs, or webhook content, present the exact command and content to the user for approval.** Read-only operations (list, get) execute immediately without confirmation.

## Operations Reference

### Messages (10 operations)
```bash
# Send a message
python skills/scripts/discord-cli.py messages.send --channel_id CHANNEL_ID --content "Hello world!" --yes

# Reply to a message
python skills/scripts/discord-cli.py messages.send --channel_id CHANNEL_ID --content "Great point!" --reply_to MESSAGE_ID --yes

# List recent messages
python skills/scripts/discord-cli.py messages.list --channel_id CHANNEL_ID --limit 25

# Get a specific message
python skills/scripts/discord-cli.py messages.get --channel_id CHANNEL_ID --message_id MESSAGE_ID

# Edit a message (bot's own)
python skills/scripts/discord-cli.py messages.edit --channel_id CHANNEL_ID --message_id MESSAGE_ID --content "Updated!" --yes

# Delete a message
python skills/scripts/discord-cli.py messages.delete --channel_id CHANNEL_ID --message_id MESSAGE_ID --yes

# Bulk delete (2-100 messages, max 14 days old)
python skills/scripts/discord-cli.py messages.bulk_delete --channel_id CHANNEL_ID --message_ids '["ID1","ID2"]' --yes

# Pin/unpin messages
python skills/scripts/discord-cli.py messages.pin --channel_id CHANNEL_ID --message_id MESSAGE_ID --yes
python skills/scripts/discord-cli.py messages.unpin --channel_id CHANNEL_ID --message_id MESSAGE_ID --yes

# List pinned messages
python skills/scripts/discord-cli.py messages.list_pins --channel_id CHANNEL_ID

# Crosspost to following servers (news channels)
python skills/scripts/discord-cli.py messages.crosspost --channel_id CHANNEL_ID --message_id MESSAGE_ID --yes
```

### Reactions (5 operations)
```bash
# Add reaction (URL-encode custom emojis: name:id)
python skills/scripts/discord-cli.py reactions.add --channel_id CID --message_id MID --emoji "👍" --yes
python skills/scripts/discord-cli.py reactions.add --channel_id CID --message_id MID --emoji "custom:123456" --yes

# Remove own reaction
python skills/scripts/discord-cli.py reactions.remove --channel_id CID --message_id MID --emoji "👍" --yes

# Remove user's reaction
python skills/scripts/discord-cli.py reactions.remove_user --channel_id CID --message_id MID --emoji "👍" --user_id UID --yes

# Remove all reactions
python skills/scripts/discord-cli.py reactions.remove_all --channel_id CID --message_id MID --yes

# List users who reacted
python skills/scripts/discord-cli.py reactions.list --channel_id CID --message_id MID --emoji "👍"
```

### Threads (13 operations)
```bash
# Create thread from message
python skills/scripts/discord-cli.py threads.create --channel_id CID --name "Discussion" --message_id MID --yes

# Create standalone thread
python skills/scripts/discord-cli.py threads.create --channel_id CID --name "Discussion" --yes

# List threads / join / leave
python skills/scripts/discord-cli.py threads.list --channel_id CID
python skills/scripts/discord-cli.py threads.join --thread_id TID --yes
python skills/scripts/discord-cli.py threads.leave --thread_id TID --yes

# Manage thread members
python skills/scripts/discord-cli.py threads.add_member --thread_id TID --user_id UID --yes
python skills/scripts/discord-cli.py threads.remove_member --thread_id TID --user_id UID --yes
python skills/scripts/discord-cli.py threads.list_members --thread_id TID

# Archive / unarchive / lock / delete
python skills/scripts/discord-cli.py threads.archive --thread_id TID --yes
python skills/scripts/discord-cli.py threads.unarchive --thread_id TID --yes
python skills/scripts/discord-cli.py threads.lock --thread_id TID --yes
python skills/scripts/discord-cli.py threads.delete --thread_id TID --yes

# List archived threads
python skills/scripts/discord-cli.py threads.list_archived_public --channel_id CID
python skills/scripts/discord-cli.py threads.list_archived_private --channel_id CID
```

### Webhooks (7 operations)
```bash
# List webhooks
python skills/scripts/discord-cli.py webhooks.list_guild
python skills/scripts/discord-cli.py webhooks.list_channel --channel_id CID

# Create webhook
python skills/scripts/discord-cli.py webhooks.create --channel_id CID --name "Notifications" --yes

# Get / edit / delete
python skills/scripts/discord-cli.py webhooks.get --webhook_id WID
python skills/scripts/discord-cli.py webhooks.edit --webhook_id WID --name "New Name" --yes
python skills/scripts/discord-cli.py webhooks.delete --webhook_id WID --yes

# Send via webhook (can impersonate name/avatar)
python skills/scripts/discord-cli.py webhooks.send --webhook_url "https://discord.com/api/webhooks/..." --content "Automated message" --username "Bot" --yes
```

### DMs (1 operation)
```bash
# Send direct message to a user
python skills/scripts/discord-cli.py dm.send --user_id USER_ID --content "Hello!" --yes
```

### Polls (2 operations)
```bash
# Create a poll (duration in hours)
python skills/scripts/discord-cli.py polls.create --channel_id CID --question "Favorite color?" --answers '["Red","Blue","Green"]' --duration_hours 24 --allow_multiselect false --yes

# End a poll early
python skills/scripts/discord-cli.py polls.end --channel_id CID --message_id MID --yes
```
