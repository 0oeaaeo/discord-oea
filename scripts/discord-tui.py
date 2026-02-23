#!/usr/bin/env python3
"""Discord OEA — Interactive TUI Mode.

A fully interactive terminal interface for browsing and executing
all 144 Discord operations. Features rich styling, category browsing,
schema-aware parameter forms, live command preview, and execution.

Usage:
    python discord-tui.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add scripts dir to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    from rich.syntax import Syntax
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from rich.live import Live
    from rich.align import Align
    from rich.markdown import Markdown
    from rich import box
except ImportError:
    print("Error: 'rich' is required for TUI mode.")
    print("Install with: pip install rich")
    sys.exit(1)

# Import the CLI module
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("discord_cli", SCRIPT_DIR / "discord-cli.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
except Exception as e:
    print(f"Error loading discord-cli.py: {e}")
    sys.exit(1)

console = Console()

# ---------------------------------------------------------------------------
# Theme & Constants
# ---------------------------------------------------------------------------

ACCENT = "bright_cyan"
ACCENT2 = "bright_magenta"
DIM = "dim white"
SUCCESS = "green"
ERROR = "red"
WARNING = "yellow"

CATEGORY_ICONS = {
    "messages": "💬", "reactions": "😀", "threads": "🧵", "channels": "📁",
    "members": "👥", "moderation": "🔨", "roles": "🎭", "invites": "✉️",
    "events": "📅", "polls": "📊", "guild": "🏰", "audit_log": "📜",
    "automod": "🤖", "webhooks": "🔗", "voice": "🎤", "emojis": "😎",
    "stickers": "🏷️", "soundboard": "🔊", "forum": "📋", "stage": "🎙️",
    "onboarding": "🚀", "welcome_screen": "👋", "commands": "⚡",
    "integrations": "🔌", "widget": "📦", "vanity": "✨", "templates": "📄",
    "dm": "📩", "bulk_ban": "🚫", "batch": "⚡",
}

CATEGORY_DESCRIPTIONS = {
    "messages": "Send, edit, delete, pin, and crosspost messages",
    "reactions": "Add, remove, and list emoji reactions",
    "threads": "Create, archive, lock, and manage thread members",
    "channels": "Create, edit, delete channels and permissions",
    "members": "List, search, edit members and manage roles",
    "moderation": "Kick, ban, timeout, and manage bans",
    "roles": "Create, edit, delete, and reorder roles",
    "invites": "Create, list, and revoke server invites",
    "events": "Schedule, edit, and manage server events",
    "polls": "Create polls and end them early",
    "guild": "View and edit server settings, prune members",
    "audit_log": "Query the server audit log",
    "automod": "Create and manage auto-moderation rules",
    "webhooks": "Create, edit, and send via webhooks",
    "voice": "Move and disconnect voice members",
    "emojis": "Upload, rename, and delete custom emojis",
    "stickers": "View and delete server stickers",
    "soundboard": "Upload and manage soundboard sounds",
    "forum": "Create posts and manage forum tags",
    "stage": "Start/end stage instances, manage speakers",
    "onboarding": "Configure server onboarding flow",
    "welcome_screen": "View and edit the welcome screen",
    "commands": "Manage slash commands",
    "integrations": "List and remove integrations",
    "widget": "Configure the server widget",
    "vanity": "Get and set vanity invite URL",
    "templates": "Create and manage server templates",
    "dm": "Send direct messages to users",
    "bulk_ban": "Ban multiple users at once",
    "batch": "Bulk operations with rate limiting",
}


# ---------------------------------------------------------------------------
# ASCII Art Header
# ---------------------------------------------------------------------------

LOGO = r"""[bright_cyan]
    ____  _                       __   ____  _________
   / __ \(_)_____________  _____/ /  / __ \/ ____/   |
  / / / / / ___/ ___/ __ \/ ___/ /  / / / / __/ / /| |
 / /_/ / (__  ) /__/ /_/ / /  / /  / /_/ / /___/ ___ |
/_____/_/____/\___/\____/_/  /_/   \____/_____/_/  |_|
[/bright_cyan]
[dim]          Omni-Execute Agent • Interactive Mode[/dim]
[dim]              144 operations • 29 categories[/dim]
"""


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def show_header():
    """Display the header with connection status."""
    console.clear()
    console.print(LOGO)
    
    # Connection status bar
    token_ok = bool(cli.BOT_TOKEN)
    guild_ok = bool(cli.GUILD_ID)
    
    status_parts = []
    if token_ok:
        status_parts.append(f"[{SUCCESS}]● Token[/{SUCCESS}]")
    else:
        status_parts.append(f"[{ERROR}]○ Token[/{ERROR}]")
    
    if guild_ok:
        status_parts.append(f"[{SUCCESS}]● Guild {cli.GUILD_ID}[/{SUCCESS}]")
    else:
        status_parts.append(f"[{ERROR}]○ Guild[/{ERROR}]")
    
    status = "  ".join(status_parts)
    console.print(Align.center(status))
    console.print()


def show_categories():
    """Display category grid with icons."""
    # Build categorized operations
    cats = {}
    for op in sorted(cli.HANDLERS.keys()):
        parts = op.split(".")
        if parts[0] == "batch":
            cat = "batch"
        else:
            cat = parts[0]
        cats.setdefault(cat, []).append(op)
    
    table = Table(
        title="[bold]Select a Category[/bold]",
        box=box.ROUNDED,
        border_style=ACCENT,
        show_header=True,
        header_style=f"bold {ACCENT}",
        pad_edge=True,
        expand=True,
    )
    table.add_column("#", style="bold yellow", width=4, justify="right")
    table.add_column("Category", style=f"bold {ACCENT2}", width=20)
    table.add_column("Ops", style="bold white", width=5, justify="center")
    table.add_column("Description", style=DIM)
    
    sorted_cats = sorted(cats.items())
    for idx, (cat, ops) in enumerate(sorted_cats, 1):
        icon = CATEGORY_ICONS.get(cat, "📌")
        desc = CATEGORY_DESCRIPTIONS.get(cat, "")
        table.add_row(
            str(idx),
            f"{icon} {cat}",
            str(len(ops)),
            desc,
        )
    
    console.print(table)
    console.print()
    return sorted_cats


def show_operations(cat_name, operations):
    """Display operations in a category."""
    table = Table(
        title=f"[bold]{CATEGORY_ICONS.get(cat_name, '📌')} {cat_name.upper()} Operations[/bold]",
        box=box.ROUNDED,
        border_style=ACCENT2,
        show_header=True,
        header_style=f"bold {ACCENT2}",
        expand=True,
    )
    table.add_column("#", style="bold yellow", width=4, justify="right")
    table.add_column("Operation", style=f"bold {ACCENT}", width=35)
    table.add_column("Description", style=DIM)
    
    for idx, op in enumerate(operations, 1):
        # Get description from operations.json
        op_parts = op.split(".")
        desc = ""
        if len(op_parts) >= 2:
            cat_key = op_parts[0]
            action_key = ".".join(op_parts[1:])
            cat_data = cli.OPERATIONS.get("categories", {}).get(cat_key, {})
            op_info = cat_data.get("operations", {}).get(action_key, {})
            if isinstance(op_info, dict):
                desc = op_info.get("description", "")
        
        table.add_row(str(idx), op, desc)
    
    console.print(table)
    console.print()


def get_operation_params(operation):
    """Get parameter schema for an operation from operations.json."""
    op_parts = operation.split(".")
    if len(op_parts) >= 2:
        cat_key = op_parts[0]
        action_key = ".".join(op_parts[1:])
        cat_data = cli.OPERATIONS.get("categories", {}).get(cat_key, {})
        op_info = cat_data.get("operations", {}).get(action_key, {})
        if isinstance(op_info, dict):
            return op_info.get("parameters", {}), op_info.get("description", "")
    return {}, ""


def show_param_form(operation, params_schema, description):
    """Interactive parameter form with schema hints."""
    console.print(Panel(
        f"[bold]{operation}[/bold]\n[dim]{description}[/dim]",
        border_style=ACCENT,
        title="[bold yellow]Parameter Input[/bold yellow]",
    ))
    
    params = {}
    
    if not params_schema:
        console.print(f"  [{DIM}]No parameters required.[/{DIM}]")
        return params
    
    for name, info in params_schema.items():
        if not isinstance(info, dict):
            continue
        
        required = info.get("required", False)
        ptype = info.get("type", "string")
        desc = info.get("description", "")
        default = info.get("default")
        
        # Build prompt label
        req_tag = f"[bold red]*[/bold red]" if required else ""
        type_tag = f"[{DIM}][{ptype}][/{DIM}]"
        desc_tag = f"  [{DIM}]{desc}[/{DIM}]" if desc else ""
        
        console.print(f"\n  {req_tag} [bold]{name}[/bold] {type_tag}{desc_tag}")
        
        if default is not None:
            prompt_text = f"    → {name} [{DIM}](default: {default})[/{DIM}]"
        else:
            prompt_text = f"    → {name}"
        
        value = Prompt.ask(prompt_text, default="" if not default else str(default))
        
        if value == "" and not required:
            continue
        elif value == "" and required:
            console.print(f"    [{WARNING}]⚠ Skipped required param (command may fail)[/{WARNING}]")
            continue
        
        # Parse value
        params[name] = cli.parse_value(value)
    
    return params


def show_command_preview(operation, params):
    """Show the command that will be executed."""
    cmd_parts = [f"python discord-cli.py {operation}"]
    for k, v in params.items():
        if isinstance(v, (list, dict)):
            cmd_parts.append(f"--{k} '{json.dumps(v)}'")
        elif isinstance(v, bool):
            cmd_parts.append(f"--{k} {'true' if v else 'false'}")
        else:
            cmd_parts.append(f"--{k} \"{v}\"")
    
    cmd_str = " \\\n    ".join(cmd_parts)
    
    # Check if read-only
    is_read_only = operation in cli.READ_ONLY_OPS
    
    panel_content = f"[bold white]{cmd_str}[/bold white]"
    if not is_read_only:
        panel_content += f"\n\n[{WARNING}]⚠ This operation will modify your server.[/{WARNING}]"
    
    panel_style = SUCCESS if is_read_only else WARNING
    
    console.print(Panel(
        panel_content,
        title="[bold]Command Preview[/bold]",
        border_style=panel_style,
        padding=(1, 2),
    ))
    
    return is_read_only


def show_result(result, success=True):
    """Display operation result."""
    try:
        data = json.loads(result)
        formatted = json.dumps(data, indent=2)
        syntax = Syntax(formatted, "json", theme="monokai", line_numbers=False)
        content = syntax
    except (json.JSONDecodeError, TypeError):
        content = Text(str(result))
    
    style = SUCCESS if success else ERROR
    title = "✅ Result" if success else "❌ Error"
    
    console.print(Panel(
        content,
        title=f"[bold]{title}[/bold]",
        border_style=style,
        padding=(1, 2),
    ))


# ---------------------------------------------------------------------------
# Main TUI Loop
# ---------------------------------------------------------------------------

async def run_operation(operation, params):
    """Execute an operation and display result."""
    handler = cli.HANDLERS.get(operation)
    if not handler:
        show_result(f"Unknown operation: {operation}", success=False)
        return
    
    with console.status(f"[{ACCENT}]Executing {operation}...", spinner="dots"):
        try:
            result = await handler(params)
            show_result(result, success=True)
        except Exception as e:
            show_result(str(e), success=False)


def main_menu():
    """Quick actions menu at the bottom."""
    console.print(
        f"  [{DIM}]Enter number to select • "
        f"[bold]s[/bold]=search • "
        f"[bold]h[/bold]=history • "
        f"[bold]q[/bold]=quit[/{DIM}]"
    )


def search_operations(query):
    """Search across all operations."""
    results = []
    query_lower = query.lower()
    for op in sorted(cli.HANDLERS.keys()):
        if query_lower in op.lower():
            results.append(op)
            continue
        # Also search descriptions
        op_parts = op.split(".")
        if len(op_parts) >= 2:
            cat_data = cli.OPERATIONS.get("categories", {}).get(op_parts[0], {})
            action_key = ".".join(op_parts[1:])
            op_info = cat_data.get("operations", {}).get(action_key, {})
            if isinstance(op_info, dict):
                desc = op_info.get("description", "").lower()
                if query_lower in desc:
                    results.append(op)
    return results


def main():
    """Main TUI event loop."""
    if not cli.BOT_TOKEN:
        console.print(Panel(
            f"[{WARNING}]No bot token configured![/{WARNING}]\n\n"
            "Set environment variables:\n"
            "  [bold]export DISCORD_BOT_TOKEN=\"your-token\"[/bold]\n"
            "  [bold]export DISCORD_GUILD_ID=\"your-guild-id\"[/bold]\n\n"
            "Or run: [bold]python discord-cli.py --config[/bold]",
            title="[bold]Configuration Required[/bold]",
            border_style=WARNING,
        ))
    
    history = []  # Track recent operations
    
    while True:
        # ── CATEGORY SCREEN ──
        show_header()
        sorted_cats = show_categories()
        main_menu()
        
        choice = Prompt.ask(f"\n  [{ACCENT}]Category[/{ACCENT}]").strip()
        
        if choice.lower() in ("q", "quit", "exit"):
            console.print(f"\n  [{DIM}]Goodbye! 👋[/{DIM}]\n")
            break
        
        # Search mode
        if choice.lower() == "s":
            query = Prompt.ask(f"  [{ACCENT}]Search[/{ACCENT}]")
            results = search_operations(query)
            if not results:
                console.print(f"  [{WARNING}]No operations matching '{query}'[/{WARNING}]")
                Prompt.ask(f"  [{DIM}]Press Enter to continue[/{DIM}]")
                continue
            
            show_header()
            show_operations(f"Search: '{query}'", results)
            op_choice = Prompt.ask(f"  [{ACCENT}]Operation #[/{ACCENT}]").strip()
            
            if op_choice.lower() in ("b", "back", ""):
                continue
            try:
                op_idx = int(op_choice) - 1
                if 0 <= op_idx < len(results):
                    selected_op = results[op_idx]
                else:
                    continue
            except ValueError:
                # Maybe they typed the operation name directly
                if op_choice in cli.HANDLERS:
                    selected_op = op_choice
                else:
                    continue
            
            # Go to param form
            params_schema, description = get_operation_params(selected_op)
            params = show_param_form(selected_op, params_schema, description)
            is_read_only = show_command_preview(selected_op, params)
            
            if is_read_only or Confirm.ask(f"  [{ACCENT}]Execute?[/{ACCENT}]", default=False):
                asyncio.run(run_operation(selected_op, params))
                history.append(selected_op)
            else:
                console.print(f"  [{DIM}]Cancelled.[/{DIM}]")
            
            Prompt.ask(f"\n  [{DIM}]Press Enter to continue[/{DIM}]")
            continue
        
        # History mode
        if choice.lower() == "h":
            if not history:
                console.print(f"  [{DIM}]No history yet.[/{DIM}]")
                Prompt.ask(f"  [{DIM}]Press Enter to continue[/{DIM}]")
                continue
            console.print(Panel(
                "\n".join(f"  {i+1}. [bold]{op}[/bold]" for i, op in enumerate(history[-20:])),
                title="[bold]Recent Operations[/bold]",
                border_style=ACCENT,
            ))
            Prompt.ask(f"  [{DIM}]Press Enter to continue[/{DIM}]")
            continue
        
        # Category selection
        try:
            cat_idx = int(choice) - 1
            if cat_idx < 0 or cat_idx >= len(sorted_cats):
                continue
        except ValueError:
            # Maybe they typed a category name
            matching = [(i, c) for i, (c, _) in enumerate(sorted_cats) if c == choice.lower()]
            if matching:
                cat_idx = matching[0][0]
            else:
                continue
        
        cat_name, operations = sorted_cats[cat_idx]
        
        # ── OPERATIONS SCREEN ──
        while True:
            show_header()
            show_operations(cat_name, operations)
            console.print(f"  [{DIM}]Enter # to select • [bold]b[/bold]=back • [bold]q[/bold]=quit[/{DIM}]")
            
            op_choice = Prompt.ask(f"\n  [{ACCENT2}]Operation #[/{ACCENT2}]").strip()
            
            if op_choice.lower() in ("b", "back", ""):
                break
            if op_choice.lower() in ("q", "quit", "exit"):
                console.print(f"\n  [{DIM}]Goodbye! 👋[/{DIM}]\n")
                return
            
            try:
                op_idx = int(op_choice) - 1
                if op_idx < 0 or op_idx >= len(operations):
                    continue
            except ValueError:
                # Direct operation name
                if op_choice in cli.HANDLERS:
                    selected_op = op_choice
                else:
                    continue
            else:
                selected_op = operations[op_idx]
            
            # ── PARAMETER FORM ──
            show_header()
            params_schema, description = get_operation_params(selected_op)
            params = show_param_form(selected_op, params_schema, description)
            
            console.print()
            is_read_only = show_command_preview(selected_op, params)
            
            # ── CONFIRMATION & EXECUTION ──
            if is_read_only:
                asyncio.run(run_operation(selected_op, params))
                history.append(selected_op)
            elif Confirm.ask(f"\n  [{ACCENT}]Execute this operation?[/{ACCENT}]", default=False):
                asyncio.run(run_operation(selected_op, params))
                history.append(selected_op)
            else:
                console.print(f"  [{DIM}]Cancelled.[/{DIM}]")
            
            Prompt.ask(f"\n  [{DIM}]Press Enter to continue[/{DIM}]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n\n  [{DIM}]Interrupted. Goodbye! 👋[/{DIM}]\n")
