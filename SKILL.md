---
name: discord-oea
description: Full Discord server management through CLI. Route to the appropriate sub-skill based on what you need to do. Covers all 144 Discord API operations including messaging, moderation, channels, roles, members, emojis, webhooks, forum, stage, onboarding, templates, batch operations, and more. Each sub-skill contains detailed operation references and examples.
---

# Discord OEA — Omni-Execute Agent

This is the **root skill** for Discord server management. Use the routing table below to find the right sub-skill for your task, then read that skill's `SKILL.md` for detailed operations and examples.

## Setup

Requires `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID` environment variables. See `references/setup-guide.md` for full setup instructions.

## Quick Routing Table

| If you need to... | Use this skill |
|---|---|
| Create, edit, or delete **channels** | `discord-manage/SKILL.md` |
| Create, edit, or reorder **roles** | `discord-manage/SKILL.md` |
| List, search, or edit **members** | `discord-manage/SKILL.md` |
| Create or revoke **invites** | `discord-manage/SKILL.md` |
| Create or manage **scheduled events** | `discord-manage/SKILL.md` |
| **Kick, ban, or timeout** users | `discord-moderate/SKILL.md` |
| Manage **automod** rules | `discord-moderate/SKILL.md` |
| Query the **audit log** | `discord-moderate/SKILL.md` |
| Move or disconnect **voice** members | `discord-moderate/SKILL.md` |
| **Bulk ban** multiple users | `discord-moderate/SKILL.md` |
| **Send, edit, or delete messages** | `discord-communicate/SKILL.md` |
| Add or remove **reactions** | `discord-communicate/SKILL.md` |
| Create or manage **threads** | `discord-communicate/SKILL.md` |
| Create or send via **webhooks** | `discord-communicate/SKILL.md` |
| Send a **DM** to a user | `discord-communicate/SKILL.md` |
| Create or end **polls** | `discord-communicate/SKILL.md` |
| Upload or manage **custom emojis** | `discord-content/SKILL.md` |
| Manage **stickers** or **soundboard** sounds | `discord-content/SKILL.md` |
| Create **forum posts** or manage **tags** | `discord-content/SKILL.md` |
| Start or manage **stage** instances | `discord-content/SKILL.md` |
| Edit **server settings** or prune members | `discord-admin/SKILL.md` |
| Configure **onboarding** or **welcome screen** | `discord-admin/SKILL.md` |
| Manage **slash commands** | `discord-admin/SKILL.md` |
| Manage **templates**, **widget**, or **vanity URL** | `discord-admin/SKILL.md` |
| **Bulk operations** (batch role/channel/member actions) | `discord-batch/SKILL.md` |

## IMPORTANT: Confirmation Before Execution

Before running any command that modifies the server, **always present the exact command to the user and explain what it will do**. Only execute after explicit user confirmation. Read-only operations (list, get, search) can execute immediately.

## CLI Tool

All operations use: `python scripts/discord-cli.py <operation> [--param value ...] [--yes]`

Quick discovery:
```bash
python scripts/discord-cli.py --discover        # list all 144 operations
python scripts/discord-cli.py --schema <op>     # show params for an operation
```
