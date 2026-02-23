<div align="center">

# 🎮 Discord OEA

### **Omni-Execute Agent** — Full Discord Server Control Through AI Skills

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Discord API v10](https://img.shields.io/badge/Discord%20API-v10-5865F2.svg)](https://discord.com/developers/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Operations](https://img.shields.io/badge/operations-144-ff6b6b.svg)](#operations-overview)
[![Skills](https://img.shields.io/badge/SKILL.md-6%20skills-blueviolet.svg)](#skills)

---

*Give your AI agent the keys to your Discord kingdom.*

**Discord OEA** is a collection of **6 AI agent skills** following the [`SKILL.md` format](https://docs.anthropic.com/en/docs/build-with-claude/skills) — compatible with **any agentic system** that can consume SKILL.md files (Claude, Cursor, Windsurf, custom agents, etc.). It provides full administrative control over Discord servers — **144 operations** across channels, messages, moderation, roles, emojis, webhooks, and more — all through a single, standalone CLI tool.

No MCP server needed. No running processes. Just drop the skills into your agent's workspace and go.

</div>

---

## ⚡ What Can It Do?

```bash
# Create a channel, send a message, and pin it — in seconds
python scripts/discord-cli.py channels.create --name "announcements" --type 0 --yes
python scripts/discord-cli.py messages.send --channel_id 123456 --content "🚀 Server is live!" --yes
python scripts/discord-cli.py messages.pin --channel_id 123456 --message_id 789012 --yes

# Moderate at scale
python scripts/discord-cli.py batch.members.timeout --member_ids '["id1","id2","id3"]' --duration_seconds 3600 --reason "Spam" --yes

# Full server discovery
python scripts/discord-cli.py --discover
```

<details>
<summary><b>🔥 See all 144 operations</b></summary>

| Category | Operations | Examples |
|----------|-----------|----------|
| **Messages** | 10 | send, edit, delete, bulk_delete, pin, crosspost |
| **Reactions** | 5 | add, remove, remove_user, remove_all, list |
| **Threads** | 13 | create, archive, lock, list_members, join/leave |
| **Channels** | 7 | create, edit, delete, set/delete permissions |
| **Members** | 6 | list, get, search, edit, add/remove role |
| **Moderation** | 7 | kick, ban, unban, timeout, list bans |
| **Roles** | 6 | create, edit, delete, reorder, list |
| **Invites** | 4 | create, list, get, delete |
| **Events** | 6 | create, edit, delete, list users |
| **Polls** | 2 | create, end |
| **Guild** | 4 | get info, edit settings, prune members |
| **Audit Log** | 1 | query with filters |
| **AutoMod** | 5 | create, edit, delete rules |
| **Webhooks** | 7 | create, edit, delete, send messages |
| **Voice** | 2 | move member, disconnect |
| **Emojis** | 5 | create from URL, edit, delete |
| **Stickers** | 3 | list, get, delete |
| **Soundboard** | 5 | create from URL, edit, delete |
| **Forum** | 5 | create posts, manage tags |
| **Stage** | 6 | start/end instances, speaker management |
| **Onboarding** | 3 | get, edit, create prompts |
| **Welcome Screen** | 2 | get, edit |
| **Commands** | 5 | create, edit, delete slash commands |
| **Integrations** | 2 | list, delete |
| **Widget** | 3 | get, edit, get data |
| **Vanity URL** | 2 | get, set |
| **Templates** | 6 | create, sync, edit, delete |
| **DM** | 1 | send direct message |
| **Bulk Ban** | 1 | ban up to 200 users at once |
| **Batch** | 10 | bulk role/channel/member/thread operations |

</details>

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.10+** with `httpx` installed
- A **Discord Bot** with Administrator permissions

```bash
pip install httpx
```

### 2. Create Your Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** → name it → **"Bot"** tab → **"Reset Token"** → copy it
3. Enable **"Server Members Intent"** and **"Message Content Intent"** under Privileged Intents
4. Go to **"OAuth2"** tab → URL Generator:
   - Scopes: `bot`
   - Permissions: `Administrator`
5. Copy the generated URL and open it to invite the bot to your server

### 3. Configure

**Option A: Environment Variables** (recommended)
```bash
export DISCORD_BOT_TOKEN="your-bot-token-here"
export DISCORD_GUILD_ID="your-server-id-here"
```

**Option B: Interactive Setup**
```bash
python scripts/discord-cli.py --config
```

> 💡 **Getting your Server ID**: Enable Developer Mode in Discord (Settings → Advanced → Developer Mode), then right-click your server name → "Copy Server ID"

### 4. Test It

```bash
# List all channels in your server
python scripts/discord-cli.py channels.list

# Explore available operations
python scripts/discord-cli.py --discover

# See parameters for any operation
python scripts/discord-cli.py --schema messages.send
```

---

## 🛡️ Safety First: Confirmation Prompts

Every mutating operation prompts for confirmation before executing:

```
$ python scripts/discord-cli.py moderation.ban --user_id 123456 --reason "spam"

  Operation: moderation.ban
  Parameters: {
      "user_id": "123456",
      "reason": "spam"
  }
  Guild: 987654321

  Execute this operation? [y/N] _
```

- **Read-only operations** (list, get, search) execute immediately
- **Use `--yes`** to skip confirmation (for scripting/automation)
- **Use `--json`** for machine-readable output

---

## 🧠 Agent Skills (SKILL.md Format)

Discord OEA is organized into **6 domain-specific skills** following the [`SKILL.md` format](https://docs.anthropic.com/en/docs/build-with-claude/skills) — a portable, agent-agnostic standard for teaching AI agents new capabilities. Any agentic coding system that can read SKILL.md files can use these skills out of the box.

### Installation

Copy the skill folders into your agent's skill/tool directory:

```bash
# Example: Claude Code / CLI
cp -r discord-* scripts/ ~/.claude/skills/

# Example: Any agent with a skills directory
cp -r discord-* scripts/ /path/to/your/agent/skills/
```

### Skill Overview

| Skill | Focus | Key Operations |
|-------|-------|----------------|
| 🏗️ **discord-manage** | Server infrastructure | Channels, roles, members, invites, scheduled events |
| 🔨 **discord-moderate** | Safety & enforcement | Kick, ban, timeout, automod, audit log, voice controls |
| 💬 **discord-communicate** | Messaging & interaction | Messages, reactions, threads, webhooks, DMs, polls |
| 🎨 **discord-content** | Custom content | Emojis, stickers, soundboard, forum posts, stage channels |
| ⚙️ **discord-admin** | Server administration | Guild settings, onboarding, commands, templates, widget |
| ⚡ **discord-batch** | Bulk operations | Mass role assignments, channel edits, member moderation |

Each skill teaches your AI agent:
1. **What** operations are available and when to use them
2. **How** to construct the exact CLI commands with correct parameters
3. **Always** present the command to the user for approval before executing

---

## 🖥️ Interactive TUI & Web App

Built with [Textual](https://textual.textualize.io/) — a full-featured management dashboard in your terminal, with mouse support and a web app mode.

```bash
pip install textual textual-serve httpx  # one-time setup

# Terminal mode
python scripts/discord-tui.py

# Web app mode (opens in your browser!)
textual serve scripts/discord-tui.py
```

**Features:**
- 🖱️ **Full mouse support** — Click to navigate, select, and execute
- 📂 **Sidebar navigation** — Browse all 29 categories with live search
- 📋 **Operations table** — Click any operation to load its parameter form
- ⚙️ **Dynamic input forms** — Parameters auto-generated with type hints and required indicators
- 📊 **Results panel** — Syntax-highlighted JSON output from data calls
- ⚠️ **Confirmation modals** — Read-only ops auto-execute; mutating ops show a preview dialog
- 🌐 **Web app mode** — Same UI in your browser via `textual serve`
- ⌨️ **Keyboard shortcuts** — `Ctrl+S` search, `Ctrl+E` execute, `Ctrl+Q` quit


## �📖 CLI Reference

```
discord-cli.py [operation] [--param value ...] [flags]

Operations:
  category.action          Execute a Discord operation
                           e.g., messages.send, moderation.ban

Flags:
  --discover               List all 144 available operations
  --schema <operation>     Show parameters for an operation
  --config                 Interactive token/guild setup
  --yes, -y                Skip confirmation prompt
  --json                   Machine-readable JSON output
  --help                   Show help

Parameters:
  --param value            Pass parameters as --key value pairs
                           JSON arrays/objects: --ids '["a","b"]'
                           Booleans: --flag true
```

### Examples

```bash
# 🔍 Discovery
python scripts/discord-cli.py --discover
python scripts/discord-cli.py --schema channels.create

# 💬 Messaging
python scripts/discord-cli.py messages.send --channel_id 123 --content "Hello!" --yes
python scripts/discord-cli.py messages.list --channel_id 123 --limit 10

# 🛡️ Moderation
python scripts/discord-cli.py moderation.timeout --user_id 456 --duration_seconds 3600 --reason "Cool down" --yes
python scripts/discord-cli.py audit_log.list --user_id 456 --limit 20

# 🎨 Content
python scripts/discord-cli.py emojis.create --name "pepe" --image_url "https://example.com/pepe.png" --yes

# ⚡ Batch
python scripts/discord-cli.py batch.members.add_role --role_id 789 --member_ids '["a","b","c"]' --yes

# 📊 JSON output for scripting
python scripts/discord-cli.py channels.list --json | jq '.[].name'
```

---

## 🏗️ Architecture

```
discord-oea/
├── scripts/
│   ├── discord-cli.py        # 🔧 Standalone CLI (1300+ lines, all 144 operations)
│   ├── discord-tui.py        # 🖥️ Interactive TUI (rich-based, category browser)
│   └── operations.json       # 📋 Operation schemas with descriptions & parameters
├── discord-manage/
│   └── SKILL.md              # 🏗️ Channels, roles, members, invites, events
├── discord-moderate/
│   └── SKILL.md              # 🔨 Moderation, automod, audit log, voice
├── discord-communicate/
│   └── SKILL.md              # 💬 Messages, reactions, threads, webhooks, DMs, polls
├── discord-content/
│   └── SKILL.md              # 🎨 Emojis, stickers, soundboard, forum, stage
├── discord-admin/
│   └── SKILL.md              # ⚙️ Guild settings, onboarding, commands, templates
├── discord-batch/
│   └── SKILL.md              # ⚡ Bulk operations with rate limiting
└── references/
    └── setup-guide.md        # 📖 Detailed setup instructions
```

The CLI tool makes **direct REST API calls** to Discord v10 — no MCP server, no WebSocket connection, no bot process running. It's completely stateless: run a command, get a result, done.

---

## 🔐 Security

| Concern | How It's Handled |
|---------|-----------------|
| Bot Token | Stored in env vars or `~/.discord-cli.json` (never committed) |
| Confirmation | All mutating ops require explicit `[y/N]` confirmation |
| Role Hierarchy | Bot can only manage users/roles below its own role |
| Rate Limits | Built-in delays (50ms) and concurrency limits (10) for batch ops |
| Permissions | Bot needs Administrator or specific granular permissions |

---

## 🤝 Contributing

PRs welcome! Some ideas:

- [ ] Add more batch operations
- [ ] Webhook message embeds support
- [ ] File/image attachment uploads
- [ ] Rate limit retry with exponential backoff
- [x] ~~Interactive TUI mode~~ ✅

---

## 📄 License

MIT — do whatever you want with it.

---

<div align="center">

**Built with 🎮 by [0oeaaeo](https://github.com/0oeaaeo)**

*Because typing in Discord is overrated when you have an AI that can do it for you.*

</div>
