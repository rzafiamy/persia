"""Beautiful console display utilities for Persia using Rich."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.rule import Rule
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# ─── Theme ────────────────────────────────────────────────────────────────────

PERSIA_THEME = Theme(
    {
        "persia.brand": "bold bright_magenta",
        "persia.user": "bold cyan",
        "persia.assistant": "bold bright_white",
        "persia.tool": "bold yellow",
        "persia.tool.result": "dim green",
        "persia.error": "bold red",
        "persia.warning": "bold yellow",
        "persia.success": "bold green",
        "persia.muted": "dim white",
        "persia.accent": "bright_magenta",
        "persia.border": "bright_magenta",
    }
)

console = Console(theme=PERSIA_THEME, highlight=True)

# ─── Banner ───────────────────────────────────────────────────────────────────

BANNER = r"""
    ____  ____  ____  _____   ___
   / __ \/ __/ / __ \/ ___/  /  /  __ _
  / /_/ / _/  / /_/ /\__ \  / /  / // /
 / .___/___/ /_  __/___/ / /_/   \_,_/
/_/          /_/  /____/
"""

BANNER_COMPACT = "PERSIA"


def print_banner(version: str = "0.1.0", model: str = "") -> None:
    """Print the startup banner."""
    lines = [
        Text("", style=""),
    ]
    # Brand panel
    brand_text = Text()
    brand_text.append("  ✦  PERSIA  ✦\n", style="bold bright_magenta")
    brand_text.append("  Autonomous AI Agent CLI\n", style="dim white")
    if model:
        brand_text.append(f"  Model: {model}\n", style="bright_cyan")
    brand_text.append(f"  v{version}", style="dim magenta")

    panel = Panel(
        Align.center(brand_text),
        border_style="bright_magenta",
        box=box.DOUBLE_EDGE,
        padding=(1, 4),
    )
    console.print(panel)
    console.print()


def print_help() -> None:
    """Print help information."""
    table = Table(
        title="Available Commands",
        box=box.ROUNDED,
        border_style="bright_magenta",
        show_header=True,
        header_style="bold bright_magenta",
        padding=(0, 2),
    )
    table.add_column("Command", style="bold cyan", no_wrap=True)
    table.add_column("Description", style="white")

    commands = [
        ("/help", "Show this help message"),
        ("/clear", "Clear the screen"),
        ("/reset", "Reset conversation history"),
        ("/history", "Show conversation history"),
        ("/model <name>", "Switch AI model"),
        ("/system <prompt>", "Set system prompt"),
        ("/tools", "List available tools"),
        ("/status", "Show system & session status"),
        ("/save <file>", "Save conversation to file"),
        ("/load <file>", "Load conversation from file"),
        ("/exit or /quit", "Exit Persia"),
        ("Ctrl+C", "Cancel current request"),
        ("Ctrl+D", "Exit Persia"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print()
    console.print(table)
    console.print()
    console.print(
        Panel(
            "[dim]💡 Just type naturally — Persia understands plain English!\n"
            "   Try: 'list files in my home directory' or 'what's running on port 8080'[/dim]",
            border_style="dim magenta",
            box=box.SIMPLE_HEAVY,
        )
    )
    console.print()


# ─── Message Rendering ────────────────────────────────────────────────────────


def render_user_message(text: str) -> None:
    """Render a user message."""
    panel = Panel(
        Text(text, style="white"),
        title="[persia.user]You[/persia.user]",
        title_align="left",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def _extract_code_blocks(text: str) -> list[tuple[str, str, str]]:
    """Extract code blocks from markdown text. Returns list of (before, lang, code)."""
    pattern = r"```(\w*)\n(.*?)```"
    parts = []
    last_end = 0
    for m in re.finditer(pattern, text, re.DOTALL):
        before = text[last_end : m.start()]
        lang = m.group(1) or "text"
        code = m.group(2)
        parts.append((before, lang, code))
        last_end = m.end()
    if last_end < len(text):
        parts.append((text[last_end:], "", ""))
    return parts


def render_assistant_message(text: str, title: str = "Persia") -> None:
    """Render an assistant response with markdown & syntax highlighting."""
    # Use Rich Markdown for rendering
    content = Markdown(text, code_theme="monokai", hyperlinks=True)
    panel = Panel(
        content,
        title=f"[persia.assistant]✦ {title}[/persia.assistant]",
        title_align="left",
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)
    console.print()


def render_tool_call(tool_name: str, args: dict) -> None:
    """Render a tool call notification."""
    args_str = ", ".join(
        f"[dim]{k}[/dim]=[cyan]{repr(v)[:60]}[/cyan]" for k, v in args.items()
    )
    console.print(
        f"  [persia.tool]⚙ Tool:[/persia.tool] [bold yellow]{tool_name}[/bold yellow]"
        f"({args_str})",
        highlight=False,
    )


def render_tool_result(tool_name: str, result: str, success: bool = True) -> None:
    """Render a tool result."""
    icon = "✓" if success else "✗"
    style = "persia.tool.result" if success else "persia.error"
    preview = result[:120].replace("\n", " ") + ("…" if len(result) > 120 else "")
    console.print(f"  [{style}]{icon} {tool_name}:[/{style}] [dim]{preview}[/dim]")


def render_error(message: str, detail: str = "") -> None:
    """Render an error message."""
    content = Text()
    content.append(f"✗ {message}", style="bold red")
    if detail:
        content.append(f"\n  {detail}", style="dim red")
    console.print(
        Panel(content, border_style="red", box=box.ROUNDED, padding=(0, 1))
    )


def render_warning(message: str) -> None:
    """Render a warning message."""
    console.print(f"[persia.warning]⚠  {message}[/persia.warning]")


def render_success(message: str) -> None:
    """Render a success message."""
    console.print(f"[persia.success]✓  {message}[/persia.success]")


def render_info(message: str) -> None:
    """Render an info message."""
    console.print(f"[persia.muted]ℹ  {message}[/persia.muted]")


def render_divider(label: str = "") -> None:
    """Render a section divider."""
    console.print(Rule(label, style="dim magenta"))


# ─── Status & Tables ──────────────────────────────────────────────────────────


def render_tools_table(tools: list[dict]) -> None:
    """Render a table of available tools."""
    table = Table(
        title="Available Tools",
        box=box.ROUNDED,
        border_style="bright_magenta",
        show_header=True,
        header_style="bold bright_magenta",
        padding=(0, 2),
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Tool", style="bold yellow", no_wrap=True)
    table.add_column("Description", style="white")

    for i, tool in enumerate(tools, 1):
        table.add_row(str(i), tool.get("name", ""), tool.get("description", ""))

    console.print()
    console.print(table)
    console.print()


def render_system_status(info: dict) -> None:
    """Render system status table."""
    table = Table(
        title="System Status",
        box=box.ROUNDED,
        border_style="bright_magenta",
        show_header=True,
        header_style="bold bright_magenta",
        padding=(0, 2),
        show_lines=True,
    )
    table.add_column("Metric", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")

    for key, val in info.items():
        table.add_row(str(key), str(val))

    console.print()
    console.print(table)
    console.print()


def render_history(turns: list[dict]) -> None:
    """Render conversation history."""
    if not turns:
        render_info("No conversation history yet.")
        return

    console.print()
    console.print(Rule("Conversation History", style="dim magenta"))
    for i, turn in enumerate(turns):
        role = turn.get("role", "?")
        content = str(turn.get("content", ""))[:200]
        if role == "user":
            console.print(f"[cyan bold][{i+1}] You:[/cyan bold] {content}")
        elif role == "assistant":
            console.print(f"[bright_magenta bold][{i+1}] Persia:[/bright_magenta bold] {content}")
        elif role == "tool":
            console.print(f"[yellow dim][{i+1}] Tool:[/yellow dim] {content[:80]}")
    console.print()


# ─── Spinner / Progress ───────────────────────────────────────────────────────


def make_thinking_spinner() -> Progress:
    """Create a spinner for 'thinking' state."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style="bright_magenta"),
        TextColumn("[bright_magenta]Persia is thinking…[/bright_magenta]"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


# ─── Streaming Live Display ───────────────────────────────────────────────────


class StreamingDisplay:
    """Manages live streaming output from the assistant."""

    def __init__(self, title: str = "Persia"):
        self.title = title
        self._buffer = ""
        self._live: Optional[Live] = None

    def start(self) -> None:
        panel = Panel(
            Text("▋", style="bright_magenta blink"),
            title=f"[persia.assistant]✦ {self.title}[/persia.assistant]",
            title_align="left",
            border_style="bright_magenta",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        self._live = Live(
            panel,
            console=console,
            refresh_per_second=15,
            transient=False,
        )
        self._live.start()

    def append(self, chunk: str) -> None:
        self._buffer += chunk
        if self._live:
            content = Markdown(self._buffer, code_theme="monokai")
            panel = Panel(
                content,
                title=f"[persia.assistant]✦ {self.title}[/persia.assistant]",
                title_align="left",
                border_style="bright_magenta",
                box=box.ROUNDED,
                padding=(0, 1),
            )
            self._live.update(panel)

    def stop(self) -> str:
        if self._live:
            self._live.stop()
            self._live = None
        console.print()
        return self._buffer

    @property
    def content(self) -> str:
        return self._buffer
