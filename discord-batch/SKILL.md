---
name: discord-batch
description: Bulk Discord operations with rate limit awareness — batch role assignments, channel permissions, member timeouts/kicks, channel edits/deletes, and thread archival. Uses discord-cli.py with built-in concurrency control.
---

# Discord Batch Operations

This skill covers all batch/bulk operations through `discord-cli.py`. Batch operations run with automatic concurrency limiting (10 concurrent) and rate limit delays (50ms between operations).

## IMPORTANT: Always Confirm Before Executing

**Batch operations affect multiple resources simultaneously. ALWAYS present the exact command, list the affected resources, and explain consequences before executing.** These operations are especially dangerous and should never be auto-executed.

## Operations Reference

### Batch Role Management (4 operations)
```bash
# Add a role to multiple members
python skills/scripts/discord-cli.py batch.members.add_role --role_id ROLE_ID --member_ids '["UID1","UID2","UID3"]' --yes

# Remove a role from multiple members
python skills/scripts/discord-cli.py batch.members.remove_role --role_id ROLE_ID --member_ids '["UID1","UID2"]' --yes

# Add multiple roles to one member
python skills/scripts/discord-cli.py batch.roles.add_to_member --member_id UID --role_ids '["RID1","RID2","RID3"]' --yes

# Remove multiple roles from one member
python skills/scripts/discord-cli.py batch.roles.remove_from_member --member_id UID --role_ids '["RID1","RID2"]' --yes
```

### Batch Channel Operations (3 operations)
```bash
# Set permissions on multiple channels
python skills/scripts/discord-cli.py batch.channels.set_permissions --channel_ids '["CID1","CID2"]' --target_id ROLE_ID --target_type role --allow "2048" --deny "0" --yes

# Edit multiple channels with same settings
python skills/scripts/discord-cli.py batch.channels.edit --channel_ids '["CID1","CID2"]' --topic "Updated" --slowmode 5 --yes

# Delete multiple channels (DESTRUCTIVE)
python skills/scripts/discord-cli.py batch.channels.delete --channel_ids '["CID1","CID2"]' --yes
```

### Batch Member Moderation (2 operations)
```bash
# Timeout multiple members
python skills/scripts/discord-cli.py batch.members.timeout --member_ids '["UID1","UID2"]' --duration_seconds 3600 --reason "Mass timeout" --yes

# Kick multiple members
python skills/scripts/discord-cli.py batch.members.kick --member_ids '["UID1","UID2"]' --reason "Cleanup" --yes
```

### Batch Thread Management (1 operation)
```bash
# Archive multiple threads
python skills/scripts/discord-cli.py batch.threads.archive --thread_ids '["TID1","TID2","TID3"]' --yes
```

## Output Format

All batch operations return a JSON summary:
```json
{
  "success": 5,
  "failed": 1,
  "errors": [
    {"member_id": "123", "error": "HTTP 403: Missing Permissions"}
  ]
}
```

## Rate Limit Guidelines

- **Concurrency**: 10 simultaneous operations (built-in)
- **Delay**: 50ms between operations (built-in)
- **Safe batch sizes**: Up to ~100 items per batch call
- **Large batches**: Split into multiple calls of 50-100 items
- Discord global rate limit: 50 requests/second
- If you get 429 errors, wait and retry with smaller batches

## Common Workflows

### Assign a role to all members matching a search
1. `members.search --query "new" --limit 100` → collect user IDs
2. `batch.members.add_role --role_id ROLE_ID --member_ids '[...]'`

### Lock down multiple channels
1. `channels.list` → identify channel IDs
2. `batch.channels.set_permissions --channel_ids '[...]' --target_id EVERYONE_ROLE --target_type role --deny "2048"`
