#!/usr/bin/env python3
"""Discord CLI - Full administrative control over Discord servers.

A standalone CLI tool that provides all 128+ Discord operations via the
Discord REST API v10. Designed to be used by Claude skills or directly
from the command line.

Usage:
    python discord-cli.py <category>.<action> [--param value ...]
    python discord-cli.py --discover
    python discord-cli.py --schema <operation>

Examples:
    python discord-cli.py messages.send --channel_id 123 --content "Hello!"
    python discord-cli.py channels.list
    python discord-cli.py moderation.ban --user_id 456 --reason "spam"
    python discord-cli.py batch.members.add_role --role_id 789 --member_ids '["a","b"]'
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://discord.com/api/v10"
BATCH_CONCURRENCY = 10
BATCH_DELAY_MS = 50
CONFIG_PATH = Path.home() / ".discord-cli.json"

# Load operations schema - look relative to this script, then in src/
SCRIPT_DIR = Path(__file__).parent
for candidate in [
    SCRIPT_DIR / "operations.json",
    SCRIPT_DIR.parent / "src" / "operations.json",
    SCRIPT_DIR.parent / "operations.json",
]:
    if candidate.exists():
        with open(candidate) as f:
            OPERATIONS = json.load(f)
        break
else:
    OPERATIONS = {"categories": {}}


def load_config():
    """Load token and guild ID from env vars or config file."""
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    guild = os.environ.get("DISCORD_GUILD_ID", "")
    if not token and CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
            token = token or cfg.get("token", "")
            guild = guild or cfg.get("guild_id", "")
    return token, guild


BOT_TOKEN, GUILD_ID = load_config()


def get_headers(reason=None):
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    if reason:
        headers["X-Audit-Log-Reason"] = reason
    return headers


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def fmt_user(u):
    return {"id": u.get("id"), "username": u.get("username"),
            "display_name": u.get("global_name") or u.get("username")}

def fmt_member(m):
    user = m.get("user", {})
    return {"user_id": user.get("id"), "username": user.get("username"),
            "display_name": user.get("global_name") or user.get("username"),
            "nick": m.get("nick"), "roles": m.get("roles", []),
            "joined_at": m.get("joined_at")}

def fmt_message(msg):
    return {"id": msg.get("id"), "author": fmt_user(msg.get("author", {})),
            "content": msg.get("content"), "timestamp": msg.get("timestamp")}

def fmt_channel(c):
    return {"id": c.get("id"), "name": c.get("name"), "type": c.get("type"),
            "topic": c.get("topic"), "parent_id": c.get("parent_id")}

def fmt_role(r):
    return {"id": r.get("id"), "name": r.get("name"), "color": r.get("color"),
            "position": r.get("position"), "hoist": r.get("hoist"),
            "mentionable": r.get("mentionable"), "permissions": r.get("permissions")}

def fmt_event(e):
    return {"id": e.get("id"), "name": e.get("name"),
            "description": e.get("description"),
            "start_time": e.get("scheduled_start_time"),
            "end_time": e.get("scheduled_end_time"), "status": e.get("status")}

def fmt_invite(i):
    return {"code": i.get("code"), "uses": i.get("uses"),
            "max_uses": i.get("max_uses"), "max_age": i.get("max_age"),
            "channel": {"id": i.get("channel", {}).get("id"),
                        "name": i.get("channel", {}).get("name")},
            "inviter": fmt_user(i.get("inviter", {}))}

def fmt_webhook(w):
    return {"id": w.get("id"), "name": w.get("name"), "url": w.get("url"),
            "channel_id": w.get("channel_id")}

def fmt_audit(e):
    return {"id": e.get("id"), "action_type": e.get("action_type"),
            "user_id": e.get("user_id"), "target_id": e.get("target_id"),
            "reason": e.get("reason")}

def fmt_automod(r):
    return {"id": r.get("id"), "name": r.get("name"),
            "trigger_type": r.get("trigger_type"), "enabled": r.get("enabled"),
            "actions": r.get("actions")}


# ---------------------------------------------------------------------------
# Operation Handlers
# ---------------------------------------------------------------------------

async def h_messages_send(p):
    payload = {"content": p["content"]}
    if p.get("reply_to"):
        payload["message_reference"] = {"message_id": p["reply_to"]}
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/messages", headers=get_headers(), json=payload)
        r.raise_for_status()
        return f"Message sent (ID: {r.json()['id']})"

async def h_messages_list(p):
    limit = min(p.get("limit", 50), 100)
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/messages", headers=get_headers(), params={"limit": limit})
        r.raise_for_status()
        return json.dumps([fmt_message(m) for m in r.json()], indent=2)

async def h_messages_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}", headers=get_headers())
        r.raise_for_status()
        return json.dumps(fmt_message(r.json()), indent=2)

async def h_messages_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Message {p['message_id']} deleted"

async def h_messages_bulk_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/messages/bulk-delete", headers=get_headers(), json={"messages": p["message_ids"]})
        r.raise_for_status()
        return f"Deleted {len(p['message_ids'])} messages"

async def h_messages_edit(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}", headers=get_headers(), json={"content": p["content"]})
        r.raise_for_status()
        return f"Message {p['message_id']} edited"

async def h_messages_pin(p):
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/channels/{p['channel_id']}/pins/{p['message_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Message {p['message_id']} pinned"

async def h_messages_unpin(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['channel_id']}/pins/{p['message_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Message {p['message_id']} unpinned"

async def h_messages_list_pins(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/pins", headers=get_headers())
        r.raise_for_status()
        return json.dumps([fmt_message(m) for m in r.json()], indent=2)

async def h_messages_crosspost(p):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}/crosspost", headers=get_headers())
        r.raise_for_status()
        return f"Message {p['message_id']} crossposted"

# -- Reactions --
async def h_reactions_add(p):
    emoji = quote(p["emoji"], safe="")
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}/reactions/{emoji}/@me", headers=get_headers())
        r.raise_for_status()
        return f"Reaction {p['emoji']} added"

async def h_reactions_remove(p):
    emoji = quote(p["emoji"], safe="")
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}/reactions/{emoji}/@me", headers=get_headers())
        r.raise_for_status()
        return f"Reaction {p['emoji']} removed"

async def h_reactions_remove_user(p):
    emoji = quote(p["emoji"], safe="")
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}/reactions/{emoji}/{p['user_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Reaction removed from user {p['user_id']}"

async def h_reactions_remove_all(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}/reactions", headers=get_headers())
        r.raise_for_status()
        return "All reactions removed"

async def h_reactions_list(p):
    emoji = quote(p["emoji"], safe="")
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}/reactions/{emoji}", headers=get_headers())
        r.raise_for_status()
        return json.dumps([fmt_user(u) for u in r.json()], indent=2)

# -- Threads --
async def h_threads_create(p):
    payload = {"name": p["name"], "auto_archive_duration": p.get("auto_archive_duration", 1440)}
    async with httpx.AsyncClient() as c:
        if p.get("message_id"):
            url = f"{BASE_URL}/channels/{p['channel_id']}/messages/{p['message_id']}/threads"
        else:
            url = f"{BASE_URL}/channels/{p['channel_id']}/threads"
            payload["type"] = 11
        r = await c.post(url, headers=get_headers(), json=payload)
        r.raise_for_status()
        t = r.json()
        return f"Thread created: {t['name']} (ID: {t['id']})"

async def h_threads_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/threads/archived/public", headers=get_headers())
        r.raise_for_status()
        threads = [{"id": t["id"], "name": t["name"]} for t in r.json().get("threads", [])]
        return json.dumps(threads, indent=2)

async def h_threads_join(p):
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/channels/{p['thread_id']}/thread-members/@me", headers=get_headers())
        r.raise_for_status()
        return f"Joined thread {p['thread_id']}"

async def h_threads_leave(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['thread_id']}/thread-members/@me", headers=get_headers())
        r.raise_for_status()
        return f"Left thread {p['thread_id']}"

async def h_threads_add_member(p):
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/channels/{p['thread_id']}/thread-members/{p['user_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Added user {p['user_id']} to thread"

async def h_threads_remove_member(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['thread_id']}/thread-members/{p['user_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Removed user {p['user_id']} from thread"

async def h_threads_archive(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/channels/{p['thread_id']}", headers=get_headers(), json={"archived": True})
        r.raise_for_status()
        return f"Thread {p['thread_id']} archived"

async def h_threads_unarchive(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/channels/{p['thread_id']}", headers=get_headers(), json={"archived": False})
        r.raise_for_status()
        return f"Thread {p['thread_id']} unarchived"

async def h_threads_lock(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/channels/{p['thread_id']}", headers=get_headers(), json={"locked": True})
        r.raise_for_status()
        return f"Thread {p['thread_id']} locked"

async def h_threads_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['thread_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Thread {p['thread_id']} deleted"

async def h_threads_list_members(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['thread_id']}/thread-members", headers=get_headers(), params={"limit": min(p.get("limit", 100), 100), "with_member": "true"})
        r.raise_for_status()
        return json.dumps([{"user_id": m.get("user_id"), "join_timestamp": m.get("join_timestamp")} for m in r.json()], indent=2)

async def h_threads_list_archived_public(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/threads/archived/public", headers=get_headers(), params={"limit": p.get("limit", 50)})
        r.raise_for_status()
        d = r.json()
        return json.dumps({"threads": [{"id": t.get("id"), "name": t.get("name")} for t in d.get("threads", [])], "has_more": d.get("has_more", False)}, indent=2)

async def h_threads_list_archived_private(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/threads/archived/private", headers=get_headers(), params={"limit": p.get("limit", 50)})
        r.raise_for_status()
        d = r.json()
        return json.dumps({"threads": [{"id": t.get("id"), "name": t.get("name")} for t in d.get("threads", [])], "has_more": d.get("has_more", False)}, indent=2)

# -- Channels --
async def h_channels_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/channels", headers=get_headers())
        r.raise_for_status()
        return json.dumps([fmt_channel(ch) for ch in r.json()], indent=2)

async def h_channels_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers())
        r.raise_for_status()
        return json.dumps(fmt_channel(r.json()), indent=2)

async def h_channels_create(p):
    payload = {"name": p["name"]}
    for k, dk in [("type","type"),("topic","topic"),("parent_id","parent_id"),("nsfw","nsfw")]:
        if p.get(k) is not None: payload[dk] = p[k]
    if p.get("slowmode") is not None: payload["rate_limit_per_user"] = p["slowmode"]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/channels", headers=get_headers(), json=payload)
        r.raise_for_status()
        ch = r.json()
        return f"Channel created: {ch['name']} (ID: {ch['id']})"

async def h_channels_edit(p):
    payload = {}
    if p.get("name"): payload["name"] = p["name"]
    if p.get("topic") is not None: payload["topic"] = p["topic"]
    if p.get("nsfw") is not None: payload["nsfw"] = p["nsfw"]
    if p.get("slowmode") is not None: payload["rate_limit_per_user"] = p["slowmode"]
    if p.get("parent_id"): payload["parent_id"] = p["parent_id"]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers(), json=payload)
        r.raise_for_status()
        return f"Channel {p['channel_id']} edited"

async def h_channels_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Channel {p['channel_id']} deleted"

async def h_channels_set_permissions(p):
    tt = 0 if p["target_type"] == "role" else 1
    payload = {"type": tt}
    if p.get("allow"): payload["allow"] = p["allow"]
    if p.get("deny"): payload["deny"] = p["deny"]
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/channels/{p['channel_id']}/permissions/{p['target_id']}", headers=get_headers(), json=payload)
        r.raise_for_status()
        return f"Permissions set for {p['target_id']}"

async def h_channels_delete_permissions(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/channels/{p['channel_id']}/permissions/{p['target_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Permissions deleted for {p['target_id']}"

# -- Members --
async def h_members_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/members", headers=get_headers(), params={"limit": min(p.get("limit", 100), 1000)})
        r.raise_for_status()
        return json.dumps([fmt_member(m) for m in r.json()], indent=2)

async def h_members_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}", headers=get_headers())
        r.raise_for_status()
        return json.dumps(fmt_member(r.json()), indent=2)

async def h_members_search(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/members/search", headers=get_headers(), params={"query": p["query"], "limit": min(p.get("limit", 100), 1000)})
        r.raise_for_status()
        return json.dumps([fmt_member(m) for m in r.json()], indent=2)

async def h_members_edit(p):
    payload = {}
    if "nick" in p: payload["nick"] = p["nick"] or None
    if p.get("mute") is not None: payload["mute"] = p["mute"]
    if p.get("deaf") is not None: payload["deaf"] = p["deaf"]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}", headers=get_headers(), json=payload)
        r.raise_for_status()
        return f"Member {p['user_id']} edited"

async def h_members_add_role(p):
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}/roles/{p['role_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Role {p['role_id']} added to user {p['user_id']}"

async def h_members_remove_role(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}/roles/{p['role_id']}", headers=get_headers())
        r.raise_for_status()
        return f"Role {p['role_id']} removed from user {p['user_id']}"

# -- Moderation --
async def h_moderation_kick(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}", headers=get_headers(p.get("reason")))
        r.raise_for_status()
        return f"User {p['user_id']} kicked"

async def h_moderation_ban(p):
    payload = {}
    dd = p.get("delete_message_days", 0)
    if dd: payload["delete_message_seconds"] = dd * 86400
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/guilds/{GUILD_ID}/bans/{p['user_id']}", headers=get_headers(p.get("reason")), json=payload if payload else None)
        r.raise_for_status()
        return f"User {p['user_id']} banned"

async def h_moderation_unban(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/bans/{p['user_id']}", headers=get_headers())
        r.raise_for_status()
        return f"User {p['user_id']} unbanned"

async def h_moderation_list_bans(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/bans", headers=get_headers(), params={"limit": p.get("limit", 100)})
        r.raise_for_status()
        return json.dumps([{"user": fmt_user(b["user"]), "reason": b.get("reason")} for b in r.json()], indent=2)

async def h_moderation_get_ban(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/bans/{p['user_id']}", headers=get_headers())
        r.raise_for_status()
        b = r.json()
        return json.dumps({"user": fmt_user(b["user"]), "reason": b.get("reason")}, indent=2)

async def h_moderation_timeout(p):
    until = datetime.now(timezone.utc) + timedelta(seconds=p["duration_seconds"])
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}", headers=get_headers(p.get("reason")), json={"communication_disabled_until": until.isoformat()})
        r.raise_for_status()
        return f"User {p['user_id']} timed out for {p['duration_seconds']}s"

async def h_moderation_remove_timeout(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}", headers=get_headers(), json={"communication_disabled_until": None})
        r.raise_for_status()
        return f"Timeout removed from user {p['user_id']}"

# -- Roles --
async def h_roles_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=get_headers()); r.raise_for_status()
        return json.dumps([fmt_role(x) for x in r.json()], indent=2)
async def h_roles_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=get_headers()); r.raise_for_status()
        role = next((x for x in r.json() if x["id"] == p["role_id"]), None)
        return json.dumps(fmt_role(role), indent=2) if role else f"Role {p['role_id']} not found"
async def h_roles_create(p):
    payload = {"name": p["name"]}
    for k in ["color","hoist","mentionable","permissions"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=get_headers(), json=payload); r.raise_for_status()
        role = r.json(); return f"Role created: {role['name']} (ID: {role['id']})"
async def h_roles_edit(p):
    payload = {}
    for k in ["name","color","hoist","mentionable","permissions"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/roles/{p['role_id']}", headers=get_headers(), json=payload); r.raise_for_status()
        return f"Role {p['role_id']} edited"
async def h_roles_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/roles/{p['role_id']}", headers=get_headers()); r.raise_for_status()
        return f"Role {p['role_id']} deleted"
async def h_roles_reorder(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/roles", headers=get_headers(), json=p["roles"]); r.raise_for_status()
        return f"Reordered {len(p['roles'])} roles"
# -- Invites --
async def h_invites_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/invites", headers=get_headers()); r.raise_for_status()
        return json.dumps([fmt_invite(i) for i in r.json()], indent=2)
async def h_invites_create(p):
    payload = {}
    for k in ["max_age","max_uses","unique"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/invites", headers=get_headers(), json=payload or {}); r.raise_for_status()
        return f"Invite created: https://discord.gg/{r.json()['code']}"
async def h_invites_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/invites/{p['invite_code']}", headers=get_headers()); r.raise_for_status()
        return json.dumps(fmt_invite(r.json()), indent=2)
async def h_invites_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/invites/{p['invite_code']}", headers=get_headers()); r.raise_for_status()
        return f"Invite {p['invite_code']} revoked"
# -- Events --
async def h_events_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events", headers=get_headers()); r.raise_for_status()
        return json.dumps([fmt_event(e) for e in r.json()], indent=2)
async def h_events_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{p['event_id']}", headers=get_headers()); r.raise_for_status()
        return json.dumps(fmt_event(r.json()), indent=2)
async def h_events_create(p):
    payload = {"name": p["name"], "scheduled_start_time": p["start_time"], "privacy_level": 2}
    if p.get("description"): payload["description"] = p["description"]
    if p.get("end_time"): payload["scheduled_end_time"] = p["end_time"]
    if p.get("channel_id"):
        payload["channel_id"] = p["channel_id"]; payload["entity_type"] = 2
    else:
        payload["entity_type"] = 3; payload["entity_metadata"] = {"location": p.get("location", "Online")}
        if not p.get("end_time"): payload["scheduled_end_time"] = p["start_time"]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events", headers=get_headers(), json=payload); r.raise_for_status()
        ev = r.json(); return f"Event created: {ev['name']} (ID: {ev['id']})"
async def h_events_edit(p):
    payload = {}
    for k, dk in [("name","name"),("description","description"),("start_time","scheduled_start_time"),("end_time","scheduled_end_time"),("status","status")]:
        if p.get(k) is not None: payload[dk] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{p['event_id']}", headers=get_headers(), json=payload); r.raise_for_status()
        return f"Event {p['event_id']} edited"
async def h_events_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{p['event_id']}", headers=get_headers()); r.raise_for_status()
        return f"Event {p['event_id']} deleted"
async def h_events_list_users(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/scheduled-events/{p['event_id']}/users", headers=get_headers()); r.raise_for_status()
        return json.dumps([fmt_user(u.get("user", {})) for u in r.json()], indent=2)
# -- Polls --
async def h_polls_create(p):
    answers = [{"poll_media": {"text": a}} for a in p["answers"]]
    payload = {"poll": {"question": {"text": p["question"]}, "answers": answers, "duration": p.get("duration_hours", 24), "allow_multiselect": p.get("allow_multiselect", False)}}
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/messages", headers=get_headers(), json=payload); r.raise_for_status()
        return f"Poll created (Message ID: {r.json()['id']})"
async def h_polls_end(p):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/polls/{p['message_id']}/expire", headers=get_headers()); r.raise_for_status()
        return f"Poll {p['message_id']} ended"
# -- Guild --
async def h_guild_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}", headers=get_headers(), params={"with_counts": "true"}); r.raise_for_status()
        g = r.json()
        return json.dumps({"id": g.get("id"), "name": g.get("name"), "description": g.get("description"), "member_count": g.get("approximate_member_count"), "owner_id": g.get("owner_id")}, indent=2)
async def h_guild_edit(p):
    payload = {}
    for k in ["name","description","verification_level","default_message_notifications","explicit_content_filter","afk_channel_id","afk_timeout","system_channel_id"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}", headers=get_headers(), json=payload); r.raise_for_status()
        return "Server settings updated"
async def h_guild_get_prune_count(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/prune", headers=get_headers(), params={"days": p["days"]}); r.raise_for_status()
        return f"{r.json()['pruned']} members would be pruned"
async def h_guild_prune(p):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/prune", headers=get_headers(), json={"days": p["days"], "compute_prune_count": p.get("compute_prune_count", True)}); r.raise_for_status()
        d = r.json(); return f"Pruned {d['pruned']} members" if d.get("pruned") is not None else "Prune initiated"
# -- Audit Log --
async def h_audit_log_list(p):
    qp = {"limit": p.get("limit", 50)}
    if p.get("user_id"): qp["user_id"] = p["user_id"]
    if p.get("action_type") is not None: qp["action_type"] = p["action_type"]
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/audit-logs", headers=get_headers(), params=qp); r.raise_for_status()
        return json.dumps([fmt_audit(e) for e in r.json().get("audit_log_entries", [])], indent=2)
# -- AutoMod --
async def h_automod_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules", headers=get_headers()); r.raise_for_status()
        return json.dumps([fmt_automod(x) for x in r.json()], indent=2)
async def h_automod_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules/{p['rule_id']}", headers=get_headers()); r.raise_for_status()
        return json.dumps(fmt_automod(r.json()), indent=2)
async def h_automod_create(p):
    payload = {"name": p["name"], "event_type": p["event_type"], "trigger_type": p["trigger_type"], "actions": p["actions"]}
    for k in ["trigger_metadata","enabled","exempt_roles","exempt_channels"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules", headers=get_headers(), json=payload); r.raise_for_status()
        rule = r.json(); return f"Automod rule created: {rule['name']} (ID: {rule['id']})"
async def h_automod_edit(p):
    payload = {}
    for k in ["name","trigger_metadata","actions","enabled","exempt_roles","exempt_channels"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules/{p['rule_id']}", headers=get_headers(), json=payload); r.raise_for_status()
        return f"Automod rule {p['rule_id']} edited"
async def h_automod_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/auto-moderation/rules/{p['rule_id']}", headers=get_headers()); r.raise_for_status()
        return f"Automod rule {p['rule_id']} deleted"
# -- Webhooks --
async def h_webhooks_list_guild(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/webhooks", headers=get_headers()); r.raise_for_status()
        return json.dumps([fmt_webhook(w) for w in r.json()], indent=2)
async def h_webhooks_list_channel(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}/webhooks", headers=get_headers()); r.raise_for_status()
        return json.dumps([fmt_webhook(w) for w in r.json()], indent=2)
async def h_webhooks_create(p):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/webhooks", headers=get_headers(), json={"name": p["name"]}); r.raise_for_status()
        w = r.json(); return f"Webhook created: {w['name']} (URL: {w.get('url','N/A')})"
async def h_webhooks_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/webhooks/{p['webhook_id']}", headers=get_headers()); r.raise_for_status()
        return json.dumps(fmt_webhook(r.json()), indent=2)
async def h_webhooks_edit(p):
    payload = {}
    if p.get("name"): payload["name"] = p["name"]
    if p.get("channel_id"): payload["channel_id"] = p["channel_id"]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/webhooks/{p['webhook_id']}", headers=get_headers(), json=payload); r.raise_for_status()
        return f"Webhook {p['webhook_id']} edited"
async def h_webhooks_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/webhooks/{p['webhook_id']}", headers=get_headers()); r.raise_for_status()
        return f"Webhook {p['webhook_id']} deleted"
async def h_webhooks_send(p):
    payload = {}
    for k in ["content","username","avatar_url"]:
        if p.get(k): payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.post(p["webhook_url"], json=payload); r.raise_for_status()
        return "Webhook message sent"
# -- Voice --
async def h_voice_move_member(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}", headers=get_headers(), json={"channel_id": p["channel_id"]}); r.raise_for_status()
        return f"User {p['user_id']} moved to voice channel {p['channel_id']}"
async def h_voice_disconnect_member(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['user_id']}", headers=get_headers(), json={"channel_id": None}); r.raise_for_status()
        return f"User {p['user_id']} disconnected from voice"
# -- Emojis --
async def h_emojis_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/emojis", headers=get_headers()); r.raise_for_status()
        return json.dumps([{"id": e["id"], "name": e["name"], "animated": e.get("animated", False)} for e in r.json()], indent=2)
async def h_emojis_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/emojis/{p['emoji_id']}", headers=get_headers()); r.raise_for_status()
        e = r.json(); return json.dumps({"id": e["id"], "name": e["name"], "animated": e.get("animated", False)}, indent=2)
async def h_emojis_create(p):
    async with httpx.AsyncClient() as c:
        img = await c.get(p["image_url"]); img.raise_for_status()
        ct = img.headers.get("content-type", "image/png")
        uri = f"data:{ct};base64,{base64.b64encode(img.content).decode()}"
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/emojis", headers=get_headers(), json={"name": p["name"], "image": uri}); r.raise_for_status()
        e = r.json(); return f"Emoji created: {e['name']} (ID: {e['id']})"
async def h_emojis_edit(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/emojis/{p['emoji_id']}", headers=get_headers(), json={"name": p["name"]}); r.raise_for_status()
        return f"Emoji {p['emoji_id']} renamed to {p['name']}"
async def h_emojis_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/emojis/{p['emoji_id']}", headers=get_headers()); r.raise_for_status()
        return f"Emoji {p['emoji_id']} deleted"
# -- Stickers --
async def h_stickers_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/stickers", headers=get_headers()); r.raise_for_status()
        return json.dumps([{"id": s["id"], "name": s["name"], "description": s.get("description")} for s in r.json()], indent=2)
async def h_stickers_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/stickers/{p['sticker_id']}", headers=get_headers()); r.raise_for_status()
        s = r.json(); return json.dumps({"id": s["id"], "name": s["name"], "description": s.get("description")}, indent=2)
async def h_stickers_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/stickers/{p['sticker_id']}", headers=get_headers()); r.raise_for_status()
        return f"Sticker {p['sticker_id']} deleted"
# -- Forum --
async def h_forum_create_post(p):
    payload = {"name": p["name"], "message": {"content": p["content"]}}
    if p.get("applied_tags"): payload["applied_tags"] = p["applied_tags"]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/channels/{p['channel_id']}/threads", headers=get_headers(), json=payload); r.raise_for_status()
        t = r.json(); return f"Forum post created: {t['name']} (ID: {t['id']})"
async def h_forum_list_tags(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers()); r.raise_for_status()
        tags = r.json().get("available_tags", [])
        return json.dumps([{"id": t["id"], "name": t["name"], "moderated": t.get("moderated", False)} for t in tags], indent=2)
async def h_forum_create_tag(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers()); r.raise_for_status()
        tags = r.json().get("available_tags", [])
        nt = {"name": p["name"]}
        if p.get("moderated") is not None: nt["moderated"] = p["moderated"]
        if p.get("emoji_name"): nt["emoji_name"] = p["emoji_name"]
        tags.append(nt)
        r = await c.patch(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers(), json={"available_tags": tags}); r.raise_for_status()
        return f"Tag '{p['name']}' created"
async def h_forum_edit_tag(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers()); r.raise_for_status()
        tags = r.json().get("available_tags", [])
        for t in tags:
            if t["id"] == p["tag_id"]:
                if p.get("name"): t["name"] = p["name"]
                if p.get("moderated") is not None: t["moderated"] = p["moderated"]
        r = await c.patch(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers(), json={"available_tags": tags}); r.raise_for_status()
        return f"Tag {p['tag_id']} edited"
async def h_forum_delete_tag(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers()); r.raise_for_status()
        tags = [t for t in r.json().get("available_tags", []) if t["id"] != p["tag_id"]]
        r = await c.patch(f"{BASE_URL}/channels/{p['channel_id']}", headers=get_headers(), json={"available_tags": tags}); r.raise_for_status()
        return f"Tag {p['tag_id']} deleted"
# -- Stage --
async def h_stage_create_instance(p):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/stage-instances", headers=get_headers(), json={"channel_id": p["channel_id"], "topic": p["topic"], "privacy_level": p.get("privacy_level", 2)}); r.raise_for_status()
        return f"Stage instance started: {p['topic']}"
async def h_stage_get_instance(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/stage-instances/{p['channel_id']}", headers=get_headers()); r.raise_for_status()
        i = r.json(); return json.dumps({"channel_id": i.get("channel_id"), "topic": i.get("topic")}, indent=2)
async def h_stage_edit_instance(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/stage-instances/{p['channel_id']}", headers=get_headers(), json={"topic": p["topic"]}); r.raise_for_status()
        return f"Stage topic updated to: {p['topic']}"
async def h_stage_delete_instance(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/stage-instances/{p['channel_id']}", headers=get_headers()); r.raise_for_status()
        return "Stage instance ended"
async def h_stage_invite_speaker(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/voice-states/{p['user_id']}", headers=get_headers(), json={"channel_id": p["channel_id"], "suppress": False}); r.raise_for_status()
        return f"User {p['user_id']} invited to speak"
async def h_stage_move_to_audience(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/voice-states/{p['user_id']}", headers=get_headers(), json={"channel_id": p["channel_id"], "suppress": True}); r.raise_for_status()
        return f"User {p['user_id']} moved to audience"
# -- Onboarding --
async def h_onboarding_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/onboarding", headers=get_headers()); r.raise_for_status()
        return json.dumps(r.json(), indent=2)
async def h_onboarding_edit(p):
    payload = {}
    for k in ["prompts","default_channel_ids","enabled","mode"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/guilds/{GUILD_ID}/onboarding", headers=get_headers(), json=payload); r.raise_for_status()
        return "Onboarding settings updated"
async def h_onboarding_create_prompt(p):
    payload = {"title": p["title"], "options": p["options"]}
    for k in ["single_select","required","in_onboarding","type"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/onboarding/prompts", headers=get_headers(), json=payload); r.raise_for_status()
        d = r.json(); return f"Prompt created: {d.get('title')} (ID: {d.get('id')})"
# -- Welcome Screen --
async def h_welcome_screen_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/welcome-screen", headers=get_headers()); r.raise_for_status()
        return json.dumps(r.json(), indent=2)
async def h_welcome_screen_edit(p):
    payload = {}
    for k in ["enabled","description","welcome_channels"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/welcome-screen", headers=get_headers(), json=payload); r.raise_for_status()
        return "Welcome screen updated"
# -- Soundboard --
async def h_soundboard_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds", headers=get_headers()); r.raise_for_status()
        sounds = r.json().get("items", [])
        return json.dumps([{"id": s["sound_id"], "name": s["name"], "volume": s.get("volume", 1)} for s in sounds], indent=2)
async def h_soundboard_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds/{p['sound_id']}", headers=get_headers()); r.raise_for_status()
        s = r.json(); return json.dumps({"id": s["sound_id"], "name": s["name"], "volume": s.get("volume", 1)}, indent=2)
async def h_soundboard_create(p):
    async with httpx.AsyncClient() as c:
        snd = await c.get(p["sound_url"]); snd.raise_for_status()
        ct = snd.headers.get("content-type", "audio/mpeg")
        uri = f"data:{ct};base64,{base64.b64encode(snd.content).decode()}"
        payload = {"name": p["name"], "sound": uri}
        for k in ["volume","emoji_name"]:
            if p.get(k) is not None: payload[k] = p[k]
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds", headers=get_headers(), json=payload); r.raise_for_status()
        s = r.json(); return f"Sound created: {s['name']} (ID: {s['sound_id']})"
async def h_soundboard_edit(p):
    payload = {}
    for k in ["name","volume","emoji_name"]:
        if p.get(k) is not None: payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds/{p['sound_id']}", headers=get_headers(), json=payload); r.raise_for_status()
        return f"Sound {p['sound_id']} edited"
async def h_soundboard_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/soundboard-sounds/{p['sound_id']}", headers=get_headers()); r.raise_for_status()
        return f"Sound {p['sound_id']} deleted"
# -- Commands --
async def _get_app_id():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/oauth2/applications/@me", headers=get_headers()); r.raise_for_status()
        return r.json()["id"]
async def h_commands_list_global(p):
    aid = await _get_app_id()
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/applications/{aid}/commands", headers=get_headers()); r.raise_for_status()
        return json.dumps([{"id": x["id"], "name": x["name"], "description": x.get("description")} for x in r.json()], indent=2)
async def h_commands_list_guild(p):
    aid = await _get_app_id()
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/applications/{aid}/guilds/{GUILD_ID}/commands", headers=get_headers()); r.raise_for_status()
        return json.dumps([{"id": x["id"], "name": x["name"], "description": x.get("description")} for x in r.json()], indent=2)
async def h_commands_create(p):
    aid = await _get_app_id()
    payload = {"name": p["name"], "description": p["description"], "type": 1}
    if p.get("options"): payload["options"] = p["options"]
    url = f"{BASE_URL}/applications/{aid}/guilds/{GUILD_ID}/commands" if p.get("guild_only", True) else f"{BASE_URL}/applications/{aid}/commands"
    async with httpx.AsyncClient() as c:
        r = await c.post(url, headers=get_headers(), json=payload); r.raise_for_status()
        cmd = r.json(); return f"Command created: /{cmd['name']} (ID: {cmd['id']})"
async def h_commands_edit(p):
    aid = await _get_app_id()
    payload = {}
    for k in ["name","description","options"]:
        if p.get(k): payload[k] = p[k]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/applications/{aid}/guilds/{GUILD_ID}/commands/{p['command_id']}", headers=get_headers(), json=payload)
        if r.status_code == 404:
            r = await c.patch(f"{BASE_URL}/applications/{aid}/commands/{p['command_id']}", headers=get_headers(), json=payload)
        r.raise_for_status(); return f"Command {p['command_id']} edited"
async def h_commands_delete(p):
    aid = await _get_app_id()
    url = f"{BASE_URL}/applications/{aid}/guilds/{GUILD_ID}/commands/{p['command_id']}" if p.get("guild_only", True) else f"{BASE_URL}/applications/{aid}/commands/{p['command_id']}"
    async with httpx.AsyncClient() as c:
        r = await c.delete(url, headers=get_headers()); r.raise_for_status()
        return f"Command {p['command_id']} deleted"
# -- Integrations --
async def h_integrations_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/integrations", headers=get_headers()); r.raise_for_status()
        return json.dumps([{"id": i["id"], "name": i["name"], "type": i["type"]} for i in r.json()], indent=2)
async def h_integrations_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/integrations/{p['integration_id']}", headers=get_headers()); r.raise_for_status()
        return f"Integration {p['integration_id']} deleted"
# -- Widget --
async def h_widget_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/widget", headers=get_headers()); r.raise_for_status()
        return json.dumps(r.json(), indent=2)
async def h_widget_get_data(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/widget.json", headers=get_headers()); r.raise_for_status()
        return json.dumps(r.json(), indent=2)
async def h_widget_edit(p):
    payload = {}
    if p.get("enabled") is not None: payload["enabled"] = p["enabled"]
    if p.get("channel_id"): payload["channel_id"] = p["channel_id"]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/widget", headers=get_headers(), json=payload); r.raise_for_status()
        return "Widget settings updated"
# -- Vanity --
async def h_vanity_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/vanity-url", headers=get_headers()); r.raise_for_status()
        d = r.json(); return json.dumps({"code": d.get("code"), "uses": d.get("uses")}, indent=2)
async def h_vanity_edit(p):
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/vanity-url", headers=get_headers(), json={"code": p["code"]}); r.raise_for_status()
        return f"Vanity URL set to: discord.gg/{p['code']}"
# -- Templates --
async def h_templates_list(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/{GUILD_ID}/templates", headers=get_headers()); r.raise_for_status()
        return json.dumps([{"code": t["code"], "name": t["name"], "description": t.get("description")} for t in r.json()], indent=2)
async def h_templates_get(p):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE_URL}/guilds/templates/{p['template_code']}", headers=get_headers()); r.raise_for_status()
        t = r.json(); return json.dumps({"code": t["code"], "name": t["name"], "description": t.get("description")}, indent=2)
async def h_templates_create(p):
    payload = {"name": p["name"]}
    if p.get("description"): payload["description"] = p["description"]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/templates", headers=get_headers(), json=payload); r.raise_for_status()
        t = r.json(); return f"Template created: {t['name']} (code: {t['code']})"
async def h_templates_sync(p):
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{BASE_URL}/guilds/{GUILD_ID}/templates/{p['template_code']}", headers=get_headers()); r.raise_for_status()
        return f"Template {p['template_code']} synced"
async def h_templates_edit(p):
    payload = {}
    if p.get("name"): payload["name"] = p["name"]
    if p.get("description") is not None: payload["description"] = p["description"]
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/templates/{p['template_code']}", headers=get_headers(), json=payload); r.raise_for_status()
        return f"Template {p['template_code']} edited"
async def h_templates_delete(p):
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/templates/{p['template_code']}", headers=get_headers()); r.raise_for_status()
        return f"Template {p['template_code']} deleted"
# -- DM --
async def h_dm_send(p):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/users/@me/channels", headers=get_headers(), json={"recipient_id": p["user_id"]}); r.raise_for_status()
        dm = r.json()
        r = await c.post(f"{BASE_URL}/channels/{dm['id']}/messages", headers=get_headers(), json={"content": p["content"]}); r.raise_for_status()
        return f"DM sent to user {p['user_id']}"
# -- Bulk Ban --
async def h_bulk_ban_execute(p):
    payload = {"user_ids": p["user_ids"]}
    if p.get("delete_message_seconds"): payload["delete_message_seconds"] = p["delete_message_seconds"]
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE_URL}/guilds/{GUILD_ID}/bulk-ban", headers=get_headers(p.get("reason")), json=payload); r.raise_for_status()
        res = r.json(); return f"Bulk ban: {len(res.get('banned_users', []))} banned, {len(res.get('failed_users', []))} failed"
# -- Batch operations --
async def _batch_op(items, key_name, op_fn):
    success, failed, errors = 0, 0, []
    sem = asyncio.Semaphore(BATCH_CONCURRENCY)
    async def run(item):
        nonlocal success, failed
        async with sem:
            try:
                await op_fn(item)
                success += 1
            except httpx.HTTPStatusError as e:
                failed += 1
                try: detail = e.response.json().get("message", e.response.text)
                except Exception: detail = e.response.text
                errors.append({key_name: item, "error": f"HTTP {e.response.status_code}: {detail}"})
            except Exception as e:
                failed += 1; errors.append({key_name: item, "error": str(e)})
            await asyncio.sleep(BATCH_DELAY_MS / 1000)
    await asyncio.gather(*[run(i) for i in items])
    return json.dumps({"success": success, "failed": failed, "errors": errors}, indent=2)

async def h_batch_members_add_role(p):
    async def op(mid):
        async with httpx.AsyncClient() as c:
            r = await c.put(f"{BASE_URL}/guilds/{GUILD_ID}/members/{mid}/roles/{p['role_id']}", headers=get_headers()); r.raise_for_status()
    return await _batch_op(p["member_ids"], "member_id", op)
async def h_batch_members_remove_role(p):
    async def op(mid):
        async with httpx.AsyncClient() as c:
            r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/members/{mid}/roles/{p['role_id']}", headers=get_headers()); r.raise_for_status()
    return await _batch_op(p["member_ids"], "member_id", op)
async def h_batch_channels_set_permissions(p):
    tt = 0 if p["target_type"] == "role" else 1
    payload = {"type": tt}
    if p.get("allow"): payload["allow"] = p["allow"]
    if p.get("deny"): payload["deny"] = p["deny"]
    async def op(cid):
        async with httpx.AsyncClient() as c:
            r = await c.put(f"{BASE_URL}/channels/{cid}/permissions/{p['target_id']}", headers=get_headers(), json=payload); r.raise_for_status()
    return await _batch_op(p["channel_ids"], "channel_id", op)
async def h_batch_members_timeout(p):
    until = datetime.now(timezone.utc) + timedelta(seconds=p["duration_seconds"])
    async def op(mid):
        async with httpx.AsyncClient() as c:
            r = await c.patch(f"{BASE_URL}/guilds/{GUILD_ID}/members/{mid}", headers=get_headers(p.get("reason")), json={"communication_disabled_until": until.isoformat()}); r.raise_for_status()
    return await _batch_op(p["member_ids"], "member_id", op)
async def h_batch_members_kick(p):
    async def op(mid):
        async with httpx.AsyncClient() as c:
            r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/members/{mid}", headers=get_headers(p.get("reason"))); r.raise_for_status()
    return await _batch_op(p["member_ids"], "member_id", op)
async def h_batch_channels_delete(p):
    async def op(cid):
        async with httpx.AsyncClient() as c:
            r = await c.delete(f"{BASE_URL}/channels/{cid}", headers=get_headers()); r.raise_for_status()
    return await _batch_op(p["channel_ids"], "channel_id", op)
async def h_batch_channels_edit(p):
    payload = {}
    if p.get("name"): payload["name"] = p["name"]
    if p.get("topic") is not None: payload["topic"] = p["topic"]
    if p.get("nsfw") is not None: payload["nsfw"] = p["nsfw"]
    if p.get("slowmode") is not None: payload["rate_limit_per_user"] = p["slowmode"]
    async def op(cid):
        async with httpx.AsyncClient() as c:
            r = await c.patch(f"{BASE_URL}/channels/{cid}", headers=get_headers(), json=payload); r.raise_for_status()
    return await _batch_op(p["channel_ids"], "channel_id", op)
async def h_batch_roles_add_to_member(p):
    async def op(rid):
        async with httpx.AsyncClient() as c:
            r = await c.put(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['member_id']}/roles/{rid}", headers=get_headers()); r.raise_for_status()
    return await _batch_op(p["role_ids"], "role_id", op)
async def h_batch_roles_remove_from_member(p):
    async def op(rid):
        async with httpx.AsyncClient() as c:
            r = await c.delete(f"{BASE_URL}/guilds/{GUILD_ID}/members/{p['member_id']}/roles/{rid}", headers=get_headers()); r.raise_for_status()
    return await _batch_op(p["role_ids"], "role_id", op)
async def h_batch_threads_archive(p):
    async def op(tid):
        async with httpx.AsyncClient() as c:
            r = await c.patch(f"{BASE_URL}/channels/{tid}", headers=get_headers(), json={"archived": True}); r.raise_for_status()
    return await _batch_op(p["thread_ids"], "thread_id", op)

# ---------------------------------------------------------------------------
# Handler Registry
# ---------------------------------------------------------------------------
HANDLERS = {
    "messages.send": h_messages_send, "messages.list": h_messages_list, "messages.get": h_messages_get,
    "messages.delete": h_messages_delete, "messages.bulk_delete": h_messages_bulk_delete,
    "messages.edit": h_messages_edit, "messages.pin": h_messages_pin, "messages.unpin": h_messages_unpin,
    "messages.list_pins": h_messages_list_pins, "messages.crosspost": h_messages_crosspost,
    "reactions.add": h_reactions_add, "reactions.remove": h_reactions_remove,
    "reactions.remove_user": h_reactions_remove_user, "reactions.remove_all": h_reactions_remove_all,
    "reactions.list": h_reactions_list,
    "threads.create": h_threads_create, "threads.list": h_threads_list, "threads.join": h_threads_join,
    "threads.leave": h_threads_leave, "threads.add_member": h_threads_add_member,
    "threads.remove_member": h_threads_remove_member, "threads.archive": h_threads_archive,
    "threads.unarchive": h_threads_unarchive, "threads.lock": h_threads_lock,
    "threads.delete": h_threads_delete, "threads.list_members": h_threads_list_members,
    "threads.list_archived_public": h_threads_list_archived_public,
    "threads.list_archived_private": h_threads_list_archived_private,
    "channels.list": h_channels_list, "channels.get": h_channels_get, "channels.create": h_channels_create,
    "channels.edit": h_channels_edit, "channels.delete": h_channels_delete,
    "channels.set_permissions": h_channels_set_permissions,
    "channels.delete_permissions": h_channels_delete_permissions,
    "members.list": h_members_list, "members.get": h_members_get, "members.search": h_members_search,
    "members.edit": h_members_edit, "members.add_role": h_members_add_role,
    "members.remove_role": h_members_remove_role,
    "moderation.kick": h_moderation_kick, "moderation.ban": h_moderation_ban,
    "moderation.unban": h_moderation_unban, "moderation.list_bans": h_moderation_list_bans,
    "moderation.get_ban": h_moderation_get_ban, "moderation.timeout": h_moderation_timeout,
    "moderation.remove_timeout": h_moderation_remove_timeout,
    "roles.list": h_roles_list, "roles.get": h_roles_get, "roles.create": h_roles_create,
    "roles.edit": h_roles_edit, "roles.delete": h_roles_delete, "roles.reorder": h_roles_reorder,
    "invites.list": h_invites_list, "invites.create": h_invites_create,
    "invites.get": h_invites_get, "invites.delete": h_invites_delete,
    "events.list": h_events_list, "events.get": h_events_get, "events.create": h_events_create,
    "events.edit": h_events_edit, "events.delete": h_events_delete,
    "events.list_users": h_events_list_users,
    "polls.create": h_polls_create, "polls.end": h_polls_end,
    "guild.get": h_guild_get, "guild.edit": h_guild_edit,
    "guild.get_prune_count": h_guild_get_prune_count, "guild.prune": h_guild_prune,
    "audit_log.list": h_audit_log_list,
    "automod.list": h_automod_list, "automod.get": h_automod_get, "automod.create": h_automod_create,
    "automod.edit": h_automod_edit, "automod.delete": h_automod_delete,
    "webhooks.list_guild": h_webhooks_list_guild, "webhooks.list_channel": h_webhooks_list_channel,
    "webhooks.create": h_webhooks_create, "webhooks.get": h_webhooks_get,
    "webhooks.edit": h_webhooks_edit, "webhooks.delete": h_webhooks_delete,
    "webhooks.send": h_webhooks_send,
    "voice.move_member": h_voice_move_member, "voice.disconnect_member": h_voice_disconnect_member,
    "emojis.list": h_emojis_list, "emojis.get": h_emojis_get, "emojis.create": h_emojis_create,
    "emojis.edit": h_emojis_edit, "emojis.delete": h_emojis_delete,
    "stickers.list": h_stickers_list, "stickers.get": h_stickers_get, "stickers.delete": h_stickers_delete,
    "forum.create_post": h_forum_create_post, "forum.list_tags": h_forum_list_tags,
    "forum.create_tag": h_forum_create_tag, "forum.edit_tag": h_forum_edit_tag,
    "forum.delete_tag": h_forum_delete_tag,
    "stage.create_instance": h_stage_create_instance, "stage.get_instance": h_stage_get_instance,
    "stage.edit_instance": h_stage_edit_instance, "stage.delete_instance": h_stage_delete_instance,
    "stage.invite_speaker": h_stage_invite_speaker, "stage.move_to_audience": h_stage_move_to_audience,
    "onboarding.get": h_onboarding_get, "onboarding.edit": h_onboarding_edit,
    "onboarding.create_prompt": h_onboarding_create_prompt,
    "welcome_screen.get": h_welcome_screen_get, "welcome_screen.edit": h_welcome_screen_edit,
    "soundboard.list": h_soundboard_list, "soundboard.get": h_soundboard_get,
    "soundboard.create": h_soundboard_create, "soundboard.edit": h_soundboard_edit,
    "soundboard.delete": h_soundboard_delete,
    "commands.list_global": h_commands_list_global, "commands.list_guild": h_commands_list_guild,
    "commands.create": h_commands_create, "commands.edit": h_commands_edit,
    "commands.delete": h_commands_delete,
    "integrations.list": h_integrations_list, "integrations.delete": h_integrations_delete,
    "widget.get": h_widget_get, "widget.get_data": h_widget_get_data, "widget.edit": h_widget_edit,
    "vanity.get": h_vanity_get, "vanity.edit": h_vanity_edit,
    "templates.list": h_templates_list, "templates.get": h_templates_get,
    "templates.create": h_templates_create, "templates.sync": h_templates_sync,
    "templates.edit": h_templates_edit, "templates.delete": h_templates_delete,
    "dm.send": h_dm_send,
    "bulk_ban.execute": h_bulk_ban_execute,
    "batch.members.add_role": h_batch_members_add_role,
    "batch.members.remove_role": h_batch_members_remove_role,
    "batch.channels.set_permissions": h_batch_channels_set_permissions,
    "batch.members.timeout": h_batch_members_timeout,
    "batch.members.kick": h_batch_members_kick,
    "batch.channels.delete": h_batch_channels_delete,
    "batch.channels.edit": h_batch_channels_edit,
    "batch.roles.add_to_member": h_batch_roles_add_to_member,
    "batch.roles.remove_from_member": h_batch_roles_remove_from_member,
    "batch.threads.archive": h_batch_threads_archive,
}

# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

# Read-only operations that don't need confirmation
READ_ONLY_OPS = {k for k in HANDLERS if any(k.endswith(s) for s in [
    ".list", ".get", ".search", ".list_pins", ".list_members",
    ".list_archived_public", ".list_archived_private",
    ".list_guild", ".list_channel", ".list_global",
    ".list_bans", ".get_ban", ".get_prune_count",
    ".get_instance", ".get_data",
])}


def discover():
    """List all available operations grouped by category."""
    cats = {}
    for op in sorted(HANDLERS.keys()):
        parts = op.split(".")
        cat = parts[0] if len(parts) == 2 else f"{parts[0]}.{parts[1]}"
        cats.setdefault(cat, []).append(op)
    print("\n  Discord CLI - Available Operations\n")
    for cat, ops in cats.items():
        print(f"  [{cat}]")
        for op in ops:
            desc = ""
            # Parse operation key: "category.action" -> look up categories[category][operations][action]
            op_parts = op.split(".")
            if len(op_parts) >= 2:
                cat_key = op_parts[0]
                action_key = ".".join(op_parts[1:])
                cat_data = OPERATIONS.get("categories", {}).get(cat_key, {})
                op_info = cat_data.get("operations", {}).get(action_key, {})
                if isinstance(op_info, dict) and op_info.get("description"):
                    desc = f"  - {op_info['description']}"
            print(f"    {op}{desc}")
        print()
    print(f"  Total: {len(HANDLERS)} operations\n")


def show_schema(operation):
    """Show the parameter schema for an operation."""
    op_parts = operation.split(".")
    if len(op_parts) >= 2:
        cat_key = op_parts[0]
        action_key = ".".join(op_parts[1:])
        cat_data = OPERATIONS.get("categories", {}).get(cat_key, {})
        op_info = cat_data.get("operations", {}).get(action_key, {})
        if isinstance(op_info, dict) and op_info:
            print(f"\n  Operation: {operation}")
            print(f"  Description: {op_info.get('description', 'N/A')}")
            params = op_info.get("parameters", {})
            if params:
                print("  Parameters:")
                for name, info in params.items():
                    if isinstance(info, dict):
                        req = " (required)" if info.get("required") else ""
                        ptype = info.get("type", "any")
                        desc = info.get("description", "")
                        print(f"    --{name}  [{ptype}]{req}  {desc}")
            print()
            return
    print(f"  Unknown operation: {operation}")
    print("  Use --discover to see available operations")



def setup_config():
    """Interactive config setup."""
    print("\n  Discord CLI - Configuration Setup\n")
    token = input("  Bot Token: ").strip()
    guild = input("  Guild ID: ").strip()
    cfg = {"token": token, "guild_id": guild}
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"\n  Config saved to {CONFIG_PATH}")
    print("  You can also set DISCORD_BOT_TOKEN and DISCORD_GUILD_ID env vars.\n")


def parse_value(v):
    """Parse a CLI value, handling JSON arrays/objects."""
    if v is None:
        return None
    # Try to parse as JSON for arrays/objects/numbers/booleans
    try:
        parsed = json.loads(v)
        return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # Boolean strings
    if v.lower() in ("true", "yes"): return True
    if v.lower() in ("false", "no"): return False
    return v


async def execute(operation, params, auto_confirm=False, json_output=False):
    """Execute an operation with confirmation prompt."""
    handler = HANDLERS.get(operation)
    if not handler:
        print(f"Error: Unknown operation '{operation}'", file=sys.stderr)
        print("Use --discover to see available operations", file=sys.stderr)
        sys.exit(1)

    # Check config
    if not BOT_TOKEN:
        print("Error: No bot token configured.", file=sys.stderr)
        print("Set DISCORD_BOT_TOKEN env var or run with --config", file=sys.stderr)
        sys.exit(1)

    # Confirmation prompt (skip for read-only ops or --yes flag)
    if not auto_confirm and operation not in READ_ONLY_OPS:
        print(f"\n  Operation: {operation}")
        print(f"  Parameters: {json.dumps(params, indent=4)}")
        if GUILD_ID:
            print(f"  Guild: {GUILD_ID}")
        confirm = input("\n  Execute this operation? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            print("  Cancelled.")
            return

    # Execute
    try:
        result = await handler(params)
        if json_output:
            # Try to parse as JSON for consistent output
            try:
                data = json.loads(result)
                print(json.dumps(data))
            except (json.JSONDecodeError, TypeError):
                print(json.dumps({"result": result}))
        else:
            print(result)
    except httpx.HTTPStatusError as e:
        err = f"Discord API error {e.response.status_code}: {e.response.text}"
        if json_output:
            print(json.dumps({"error": err}))
        else:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        err = f"Error: {str(e)}"
        if json_output:
            print(json.dumps({"error": err}))
        else:
            print(err, file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Discord CLI - Full administrative control over Discord servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s channels.list
  %(prog)s messages.send --channel_id 123 --content "Hello!"
  %(prog)s moderation.ban --user_id 456 --reason "spam" --yes
  %(prog)s --discover
  %(prog)s --schema messages.send
        """,
    )
    parser.add_argument("operation", nargs="?", help="Operation to execute (e.g., messages.send)")
    parser.add_argument("--discover", action="store_true", help="List all operations")
    parser.add_argument("--schema", metavar="OP", help="Show parameter schema for an operation")
    parser.add_argument("--config", action="store_true", help="Interactive config setup")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--json", action="store_true", help="JSON output mode")

    # Parse known args, treat rest as --key value pairs
    args, remaining = parser.parse_known_args()

    if args.discover:
        discover()
        return
    if args.schema:
        show_schema(args.schema)
        return
    if args.config:
        setup_config()
        return

    if not args.operation:
        parser.print_help()
        return

    # Parse remaining args as --key value pairs
    params = {}
    i = 0
    while i < len(remaining):
        arg = remaining[i]
        if arg.startswith("--"):
            key = arg[2:]
            if i + 1 < len(remaining) and not remaining[i + 1].startswith("--"):
                params[key] = parse_value(remaining[i + 1])
                i += 2
            else:
                params[key] = True
                i += 1
        else:
            i += 1

    asyncio.run(execute(args.operation, params, auto_confirm=args.yes, json_output=args.json))


if __name__ == "__main__":
    main()
