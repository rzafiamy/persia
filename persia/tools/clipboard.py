"""Clipboard and desktop integration tools for Persia."""
from __future__ import annotations

import subprocess
import sys
from typing import Any

from pylemura.types.tools import FunctionTool
from pylemura.types.tools import ToolContext


async def _read_clipboard(params: Any, ctx: ToolContext) -> str:
    """Read text from the system clipboard."""
    try:
        import pyperclip
        content = pyperclip.paste()
        if not content:
            return "(Clipboard is empty)"
        return f"Clipboard contents ({len(content)} chars):\n{content}"
    except ImportError:
        pass

    # Fallback: try xclip / xsel / pbpaste
    for cmd in [["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"], ["pbpaste"]]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                return result.stdout or "(Clipboard is empty)"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return "Error: Could not read clipboard. Install pyperclip: pip install pyperclip"


async def _write_clipboard(params: Any, ctx: ToolContext) -> str:
    """Write text to the system clipboard."""
    text = params.get("text", "")
    if not text:
        return "Error: text is required"

    try:
        import pyperclip
        pyperclip.copy(text)
        return f"Copied {len(text)} characters to clipboard"
    except ImportError:
        pass

    # Fallback
    for cmd_template in [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["pbcopy"],
    ]:
        try:
            proc = subprocess.run(
                cmd_template,
                input=text.encode(),
                capture_output=True,
                timeout=3,
            )
            if proc.returncode == 0:
                return f"Copied {len(text)} characters to clipboard"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return "Error: Could not write to clipboard. Install pyperclip: pip install pyperclip"


async def _open_url(params: Any, ctx: ToolContext) -> str:
    """Open a URL in the default browser."""
    import webbrowser
    url = params.get("url", "").strip()
    if not url:
        return "Error: url is required"
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"
    try:
        webbrowser.open(url)
        return f"Opened in browser: {url}"
    except Exception as e:
        return f"Error opening URL: {e}"


async def _open_file(params: Any, ctx: ToolContext) -> str:
    """Open a file with the default application."""
    import subprocess
    from pathlib import Path

    path = params.get("path", "").strip()
    if not path:
        return "Error: path is required"

    full_path = Path(path).expanduser().resolve()
    if not full_path.exists():
        return f"Error: File not found: {full_path}"

    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(full_path)])
        elif sys.platform == "win32":
            subprocess.Popen(["start", "", str(full_path)], shell=True)
        else:
            subprocess.Popen(["xdg-open", str(full_path)])
        return f"Opened: {full_path}"
    except Exception as e:
        return f"Error opening file: {e}"


async def _send_notification(params: Any, ctx: ToolContext) -> str:
    """Send a desktop notification."""
    title = params.get("title", "Persia")
    message = params.get("message", "")
    urgency = params.get("urgency", "normal")  # low | normal | critical

    if not message:
        return "Error: message is required"

    try:
        if sys.platform == "darwin":
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=True, timeout=5)
        elif sys.platform == "linux":
            subprocess.run(
                ["notify-send", f"--urgency={urgency}", title, message],
                check=True, timeout=5,
            )
        elif sys.platform == "win32":
            # Windows toast notification via PowerShell
            ps_script = (
                f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;'
                f'$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02;'
                f'$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template);'
                f'$xml.SelectSingleNode("//text[@id=1]").InnerText = "{title}";'
                f'$xml.SelectSingleNode("//text[@id=2]").InnerText = "{message}";'
                f'$notif = [Windows.UI.Notifications.ToastNotification]::new($xml);'
                f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Persia").Show($notif);'
            )
            subprocess.run(["powershell", "-Command", ps_script], timeout=5)
        return f"Notification sent: {title} — {message}"
    except FileNotFoundError:
        return "Error: Notification system not available (try: sudo apt install libnotify-bin)"
    except Exception as e:
        return f"Error sending notification: {e}"


def make_clipboard_tools() -> list:
    """Create clipboard and desktop integration tools."""
    return [
        FunctionTool(
            name="read_clipboard",
            description="Read the current contents of the system clipboard.",
            parameters={"type": "object", "properties": {}, "required": []},
            func=_read_clipboard,
        ),
        FunctionTool(
            name="write_clipboard",
            description="Write text to the system clipboard.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to copy to clipboard"},
                },
                "required": ["text"],
            },
            func=_write_clipboard,
        ),
        FunctionTool(
            name="open_url",
            description="Open a URL in the user's default web browser.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open (must start with http:// or https://)"},
                },
                "required": ["url"],
            },
            func=_open_url,
        ),
        FunctionTool(
            name="open_file",
            description="Open a file with the default application (e.g., open a PDF, image, or document).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to open"},
                },
                "required": ["path"],
            },
            func=_open_file,
        ),
        FunctionTool(
            name="send_notification",
            description="Send a desktop notification to the user.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Notification title", "default": "Persia"},
                    "message": {"type": "string", "description": "Notification body text"},
                    "urgency": {"type": "string", "enum": ["low", "normal", "critical"], "description": "Urgency level (default: normal)", "default": "normal"},
                },
                "required": ["message"],
            },
            func=_send_notification,
        ),
    ]
