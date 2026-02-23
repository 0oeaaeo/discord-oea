#!/usr/bin/env python3
"""Discord OEA — Textual TUI & Web App.

A fully interactive terminal/web UI for browsing and executing
all 144 Discord operations.

Terminal mode:  python discord-tui.py
Web app mode:   textual serve discord-tui.py
"""

import asyncio
import json
import os
import sys
import importlib.util
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
    Horizontal, Vertical, VerticalScroll, Container, Center
)
from textual.widgets import (
    Header, Footer, Static, Label, Input, Button,
    ListView, ListItem, RichLog, Rule, Select,
    Tree, Collapsible, LoadingIndicator, Switch,
    DataTable, Markdown, TabbedContent, TabPane,
)
from textual.screen import ModalScreen
from textual.reactive import reactive
from rich.text import Text
from rich.syntax import Syntax

# Load the CLI module
SCRIPT_DIR = Path(__file__).parent
spec = importlib.util.spec_from_file_location("discord_cli", SCRIPT_DIR / "discord-cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ICONS = {
    "messages": "💬", "reactions": "😀", "threads": "🧵", "channels": "📁",
    "members": "👥", "moderation": "🔨", "roles": "🎭", "invites": "✉️",
    "events": "📅", "polls": "📊", "guild": "🏰", "audit_log": "📜",
    "automod": "🤖", "webhooks": "🔗", "voice": "🎤", "emojis": "😎",
    "stickers": "🏷️", "soundboard": "🔊", "forum": "📋", "stage": "🎙️",
    "onboarding": "🚀", "welcome_screen": "👋", "commands": "⚡",
    "integrations": "🔌", "widget": "📦", "vanity": "✨", "templates": "📄",
    "dm": "📩", "bulk_ban": "🚫", "batch": "⚡",
}

CAT_DESCRIPTIONS = {
    "messages": "Send, edit, delete, pin messages",
    "reactions": "Add/remove emoji reactions",
    "threads": "Create, archive, lock threads",
    "channels": "Create, edit, delete channels",
    "members": "List, search, edit members",
    "moderation": "Kick, ban, timeout users",
    "roles": "Create, edit, reorder roles",
    "invites": "Create and revoke invites",
    "events": "Schedule server events",
    "polls": "Create and end polls",
    "guild": "Server settings and prune",
    "audit_log": "Query audit log",
    "automod": "Manage automod rules",
    "webhooks": "Create and send webhooks",
    "voice": "Move/disconnect voice users",
    "emojis": "Upload, rename custom emojis",
    "stickers": "View and delete stickers",
    "soundboard": "Upload and manage sounds",
    "forum": "Create posts, manage tags",
    "stage": "Manage stage instances",
    "onboarding": "Configure onboarding",
    "welcome_screen": "Edit welcome screen",
    "commands": "Manage slash commands",
    "integrations": "List/remove integrations",
    "widget": "Configure server widget",
    "vanity": "Get/set vanity URL",
    "templates": "Server templates",
    "dm": "Send direct messages",
    "bulk_ban": "Ban multiple users",
    "batch": "Bulk operations",
}


def get_categories():
    """Get operations grouped by category."""
    cats = {}
    for op in sorted(cli.HANDLERS.keys()):
        parts = op.split(".")
        cat = "batch" if parts[0] == "batch" else parts[0]
        cats.setdefault(cat, []).append(op)
    return dict(sorted(cats.items()))


def get_op_info(operation):
    """Get description and parameters for an operation."""
    parts = operation.split(".")
    if len(parts) >= 2:
        cat_key = parts[0]
        action_key = ".".join(parts[1:])
        cat_data = cli.OPERATIONS.get("categories", {}).get(cat_key, {})
        op_info = cat_data.get("operations", {}).get(action_key, {})
        if isinstance(op_info, dict):
            return op_info.get("description", ""), op_info.get("parameters", {})
    return "", {}


# ---------------------------------------------------------------------------
# Confirm Screen
# ---------------------------------------------------------------------------
class ConfirmScreen(ModalScreen[bool]):
    """Modal confirmation dialog."""

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-dialog {
        width: 70;
        height: auto;
        max-height: 24;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #confirm-dialog Label {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }
    #confirm-buttons {
        width: 100%;
        height: auto;
        align-horizontal: center;
        margin-top: 1;
    }
    #confirm-buttons Button {
        margin: 0 2;
    }
    #cmd-preview {
        width: 100%;
        height: auto;
        max-height: 12;
        border: round $accent;
        padding: 1;
        margin: 1 0;
        overflow-y: auto;
    }
    """

    def __init__(self, operation: str, params: dict):
        super().__init__()
        self.operation = operation
        self.params = params

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label("⚠️  [bold]Confirm Execution[/bold]", id="confirm-title")
            yield Label(f"[bold cyan]{self.operation}[/bold cyan]")
            cmd = self._build_cmd()
            yield Static(Syntax(cmd, "bash", theme="monokai"), id="cmd-preview")
            with Horizontal(id="confirm-buttons"):
                yield Button("✅ Execute", variant="success", id="btn-yes")
                yield Button("❌ Cancel", variant="error", id="btn-no")

    def _build_cmd(self):
        parts = [f"python discord-cli.py {self.operation}"]
        for k, v in self.params.items():
            if isinstance(v, (list, dict)):
                parts.append(f"  --{k} '{json.dumps(v)}'")
            elif isinstance(v, bool):
                parts.append(f"  --{k} {'true' if v else 'false'}")
            else:
                parts.append(f'  --{k} "{v}"')
        return " \\\n".join(parts)

    def action_confirm(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self):
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def on_no(self):
        self.dismiss(False)


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
class DiscordOEA(App):
    """Discord OEA — Interactive TUI & Web App."""

    TITLE = "Discord OEA"
    SUB_TITLE = "Omni-Execute Agent"
    ENABLE_COMMAND_PALETTE = True

    CSS = """
    Screen {
        background: $surface;
    }

    /* --- Sidebar --- */
    #sidebar {
        width: 32;
        height: 100%;
        dock: left;
        background: $panel;
        border-right: thick $accent;
    }
    #sidebar-title {
        width: 100%;
        text-align: center;
        padding: 1;
        color: $accent;
        text-style: bold;
    }
    #cat-list {
        height: 1fr;
    }
    #cat-list > ListItem {
        padding: 0 1;
        height: 3;
    }
    #cat-list > ListItem:hover {
        background: $accent 15%;
    }
    #cat-list > ListItem.-selected {
        background: $accent 30%;
    }
    .cat-label {
        padding: 0 1;
    }
    .cat-count {
        color: $text-muted;
        text-align: right;
        width: 6;
    }
    #search-box {
        margin: 0 1;
        dock: top;
    }

    /* --- Main Content --- */
    #main {
        height: 100%;
    }
    #content-area {
        height: 1fr;
    }

    /* --- Ops Panel --- */
    #ops-panel {
        height: 1fr;
        border-bottom: thick $accent;
    }
    #ops-table {
        height: 1fr;
    }
    #ops-header {
        width: 100%;
        height: 3;
        padding: 1;
        text-style: bold;
        color: $accent;
        border-bottom: solid $accent;
    }

    /* --- Bottom Panel (params + results) --- */
    #bottom-panels {
        height: 1fr;
    }
    #params-panel {
        width: 1fr;
        border-right: solid $accent;
        padding: 1;
    }
    #params-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #params-scroll {
        height: 1fr;
    }
    .param-row {
        height: auto;
        margin-bottom: 1;
    }
    .param-label {
        color: $text;
        margin-bottom: 0;
    }
    .param-hint {
        color: $text-muted;
        margin-bottom: 0;
    }
    .param-input {
        margin-bottom: 0;
    }

    #execute-bar {
        width: 100%;
        height: auto;
        align-horizontal: center;
        padding: 1;
        dock: bottom;
    }
    #btn-execute {
        min-width: 20;
    }

    /* --- Results --- */
    #results-panel {
        width: 1fr;
        padding: 1;
    }
    #results-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #results-log {
        height: 1fr;
        border: round $panel;
        padding: 1;
    }

    /* --- Status Bar --- */
    #status-bar {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    .status-connected { color: $success; }
    .status-disconnected { color: $error; }

    /* --- Welcome --- */
    #welcome {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    #welcome-text {
        width: 60;
        height: auto;
        text-align: center;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "focus_search", "Search"),
        Binding("ctrl+e", "execute", "Execute"),
        Binding("escape", "deselect", "Back"),
    ]

    selected_category = reactive("")
    selected_operation = reactive("")

    def __init__(self):
        super().__init__()
        self.categories = get_categories()
        self.param_inputs = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static(
                    "🎮 [bold bright_cyan]Discord OEA[/]\n"
                    "[dim]144 ops • 29 categories[/]",
                    id="sidebar-title"
                )
                yield Input(placeholder="🔍 Search operations...", id="search-box")
                yield ListView(
                    *self._build_cat_items(),
                    id="cat-list"
                )
            # Main area
            with Vertical(id="main"):
                with Horizontal(id="content-area"):
                    # Operations table
                    with Vertical(id="ops-panel"):
                        yield Static("Select a category →", id="ops-header")
                        yield DataTable(id="ops-table", cursor_type="row")
                    # Results panel
                    with Vertical(id="results-panel"):
                        yield Static("📋 [bold]Results[/bold]", id="results-title")
                        yield RichLog(id="results-log", highlight=True, markup=True)
                # Params + execute
                with Horizontal(id="bottom-panels"):
                    with Vertical(id="params-panel"):
                        yield Static("⚙️  [bold]Parameters[/bold]", id="params-title")
                        yield VerticalScroll(id="params-scroll")
                        with Center(id="execute-bar"):
                            yield Button(
                                "▶ Execute", variant="success",
                                id="btn-execute", disabled=True
                            )
        yield Footer()

    def _build_cat_items(self, filter_text=""):
        items = []
        for cat, ops in self.categories.items():
            icon = ICONS.get(cat, "📌")
            label = f"{icon} {cat}"
            if filter_text and filter_text.lower() not in cat.lower():
                # Also search in op names
                if not any(filter_text.lower() in op.lower() for op in ops):
                    continue
            item = ListItem(
                Horizontal(
                    Label(label, classes="cat-label"),
                    Label(f"[{len(ops)}]", classes="cat-count"),
                ),
                id=f"cat-{cat}",
            )
            items.append(item)
        return items

    def on_mount(self):
        table = self.query_one("#ops-table", DataTable)
        table.add_columns("Operation", "Description")
        # Connection status
        token_ok = "🟢" if cli.BOT_TOKEN else "🔴"
        guild = cli.GUILD_ID or "not set"
        self.sub_title = f"{token_ok} Guild: {guild}"

    # --- Search ---
    @on(Input.Changed, "#search-box")
    def on_search(self, event: Input.Changed):
        cat_list = self.query_one("#cat-list", ListView)
        cat_list.clear()
        for item in self._build_cat_items(event.value):
            cat_list.append(item)

    # --- Category Selection ---
    @on(ListView.Selected, "#cat-list")
    def on_cat_selected(self, event: ListView.Selected):
        item_id = event.item.id
        if item_id and item_id.startswith("cat-"):
            cat = item_id[4:]
            self.selected_category = cat
            self._show_operations(cat)

    def _show_operations(self, cat):
        ops = self.categories.get(cat, [])
        header = self.query_one("#ops-header", Static)
        icon = ICONS.get(cat, "📌")
        header.update(f"{icon} [bold]{cat.upper()}[/bold] — {len(ops)} operations")

        table = self.query_one("#ops-table", DataTable)
        table.clear()
        for op in ops:
            desc, _ = get_op_info(op)
            table.add_row(op, desc or "—")

    # --- Operation Selection ---
    @on(DataTable.RowSelected, "#ops-table")
    def on_op_selected(self, event: DataTable.RowSelected):
        row = event.data_table.get_row(event.row_key)
        operation = str(row[0])
        self.selected_operation = operation
        self._show_params(operation)

    def _show_params(self, operation):
        desc, params_schema = get_op_info(operation)
        scroll = self.query_one("#params-scroll", VerticalScroll)
        scroll.remove_children()
        self.param_inputs.clear()

        title = self.query_one("#params-title", Static)
        title.update(f"⚙️  [bold]{operation}[/bold]\n[dim]{desc}[/dim]")

        btn = self.query_one("#btn-execute", Button)
        btn.disabled = False
        if operation in cli.READ_ONLY_OPS:
            btn.label = "▶ Execute (read-only)"
            btn.variant = "primary"
        else:
            btn.label = "▶ Execute"
            btn.variant = "success"

        if not params_schema:
            scroll.mount(Static("[dim]No parameters needed.[/dim]"))
            return

        for name, info in params_schema.items():
            if not isinstance(info, dict):
                continue
            required = info.get("required", False)
            ptype = info.get("type", "string")
            pdesc = info.get("description", "")
            req_mark = " [bold red]*[/bold red]" if required else ""

            container = Vertical(classes="param-row")
            container.mount(
                Static(f"[bold]{name}[/bold]{req_mark} [dim][{ptype}][/dim]", classes="param-label")
            )
            if pdesc:
                container.mount(Static(f"[dim]{pdesc}[/dim]", classes="param-hint"))
            inp = Input(
                placeholder=f"{name} ({ptype})",
                id=f"param-{name}",
                classes="param-input",
            )
            container.mount(inp)
            scroll.mount(container)
            self.param_inputs[name] = inp

    # --- Execute ---
    @on(Button.Pressed, "#btn-execute")
    def on_execute(self):
        self.action_execute()

    def action_execute(self):
        if not self.selected_operation:
            return
        params = self._collect_params()
        is_read_only = self.selected_operation in cli.READ_ONLY_OPS

        if is_read_only:
            self._run_operation(self.selected_operation, params)
        else:
            self.push_screen(
                ConfirmScreen(self.selected_operation, params),
                callback=lambda confirmed: (
                    self._run_operation(self.selected_operation, params)
                    if confirmed else None
                ),
            )

    def _collect_params(self):
        params = {}
        for name, inp in self.param_inputs.items():
            val = inp.value.strip()
            if val:
                params[name] = cli.parse_value(val)
        return params

    @work(thread=True)
    def _run_operation(self, operation, params):
        log = self.query_one("#results-log", RichLog)
        log.write(Rule(f"[bold cyan]{operation}[/bold cyan]"))
        log.write(f"[dim]Params: {json.dumps(params, indent=2)}[/dim]\n")

        handler = cli.HANDLERS.get(operation)
        if not handler:
            log.write(f"[red]Unknown operation: {operation}[/red]")
            return

        try:
            result = asyncio.run(handler(params))
            try:
                data = json.loads(result)
                formatted = json.dumps(data, indent=2)
                log.write(Syntax(formatted, "json", theme="monokai"))
            except (json.JSONDecodeError, TypeError):
                log.write(f"[green]{result}[/green]")
        except Exception as e:
            log.write(f"[bold red]Error:[/bold red] {e}")

        log.write("")

    def action_focus_search(self):
        self.query_one("#search-box", Input).focus()

    def action_deselect(self):
        self.selected_operation = ""
        btn = self.query_one("#btn-execute", Button)
        btn.disabled = True


if __name__ == "__main__":
    app = DiscordOEA()
    app.run()
