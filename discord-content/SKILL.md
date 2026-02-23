---
name: discord-content
description: Manage Discord server content — custom emojis, stickers, soundboard sounds, forum posts/tags, and stage channel instances. Uses discord-cli.py for content operations via the Discord REST API.
---

# Discord Content Management

This skill covers custom content management through `discord-cli.py`.

## IMPORTANT: Always Confirm Before Executing

**Before creating, editing, or deleting content, present the exact command to the user and explain what will happen.** Read-only operations execute immediately.

## Operations Reference

### Emojis (5 operations)
```bash
# List custom emojis
python skills/scripts/discord-cli.py emojis.list

# Get emoji details
python skills/scripts/discord-cli.py emojis.get --emoji_id EMOJI_ID

# Create emoji from URL (max 256KB, 128x128px recommended)
python skills/scripts/discord-cli.py emojis.create --name "pogchamp" --image_url "https://example.com/emoji.png" --yes

# Rename emoji
python skills/scripts/discord-cli.py emojis.edit --emoji_id EMOJI_ID --name "new_name" --yes

# Delete emoji
python skills/scripts/discord-cli.py emojis.delete --emoji_id EMOJI_ID --yes
```

### Stickers (3 operations)
```bash
python skills/scripts/discord-cli.py stickers.list
python skills/scripts/discord-cli.py stickers.get --sticker_id SID
python skills/scripts/discord-cli.py stickers.delete --sticker_id SID --yes
```

### Soundboard (5 operations)
```bash
python skills/scripts/discord-cli.py soundboard.list
python skills/scripts/discord-cli.py soundboard.get --sound_id SID
python skills/scripts/discord-cli.py soundboard.create --name "airhorn" --sound_url "https://example.com/sound.mp3" --volume 0.8 --yes
python skills/scripts/discord-cli.py soundboard.edit --sound_id SID --name "newname" --volume 0.5 --yes
python skills/scripts/discord-cli.py soundboard.delete --sound_id SID --yes
```

### Forum (5 operations)
```bash
# Create forum post (channel must be type 15 = forum)
python skills/scripts/discord-cli.py forum.create_post --channel_id CID --name "Bug Report" --content "Details here" --applied_tags '["TAG_ID"]' --yes

# Manage forum tags
python skills/scripts/discord-cli.py forum.list_tags --channel_id CID
python skills/scripts/discord-cli.py forum.create_tag --channel_id CID --name "Bug" --moderated true --yes
python skills/scripts/discord-cli.py forum.edit_tag --channel_id CID --tag_id TID --name "Feature" --yes
python skills/scripts/discord-cli.py forum.delete_tag --channel_id CID --tag_id TID --yes
```

### Stage (6 operations)
```bash
# Start a stage instance (channel must be type 13 = stage)
python skills/scripts/discord-cli.py stage.create_instance --channel_id CID --topic "Q&A Session" --yes

# Get / edit / end stage
python skills/scripts/discord-cli.py stage.get_instance --channel_id CID
python skills/scripts/discord-cli.py stage.edit_instance --channel_id CID --topic "New Topic" --yes
python skills/scripts/discord-cli.py stage.delete_instance --channel_id CID --yes

# Speaker management
python skills/scripts/discord-cli.py stage.invite_speaker --channel_id CID --user_id UID --yes
python skills/scripts/discord-cli.py stage.move_to_audience --channel_id CID --user_id UID --yes
```
