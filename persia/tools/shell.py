"""Shell execution tools for Persia."""
from __future__ import annotations

import asyncio
import os
import shlex
from typing import Any

from pylemura.types.tools import FunctionTool
from pylemura.types.tools import ToolContext

# Commands that are considered dangerous and require confirmation
_DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "dd if=",
    "mkfs",
    "format",
    "> /dev/",
    ":(){ :|:& };:",  # fork bomb
]

_BLOCKED_COMMANDS = {"shutdown", "reboot", "halt", "poweroff"}


def _is_dangerous(cmd: str) -> bool:
    cmd_lower = cmd.lower().strip()
    base_cmd = shlex.split(cmd_lower)[0] if cmd_lower else ""
    if base_cmd in _BLOCKED_COMMANDS:
        return True
    return any(p in cmd_lower for p in _DANGEROUS_PATTERNS)


async def _run_command(params: Any, ctx: ToolContext) -> str:
    command = params.get("command", "").strip()
    timeout = min(params.get("timeout", 30), 120)
    cwd = params.get("cwd", None)
    capture_stderr = params.get("capture_stderr", True)

    if not command:
        return "Error: command is required"

    if _is_dangerous(command):
        return (
            f"Error: This command appears dangerous and has been blocked for safety: {command!r}\n"
            "If you need to run this, please do it manually in your terminal."
        )

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE if capture_stderr else asyncio.subprocess.DEVNULL,
            cwd=cwd,
            env=os.environ.copy(),
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return f"Error: Command timed out after {timeout}s: {command!r}"

        output = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip() if stderr else ""

        result_parts = []
        if output:
            result_parts.append(output)
        if err and capture_stderr:
            result_parts.append(f"[stderr]\n{err}")

        result = "\n".join(result_parts) if result_parts else "(no output)"
        exit_code = proc.returncode

        if exit_code != 0:
            return f"Exit code: {exit_code}\n{result}"
        return result

    except FileNotFoundError as e:
        return f"Error: Command not found — {e}"
    except PermissionError as e:
        return f"Error: Permission denied — {e}"
    except Exception as e:
        return f"Error running command: {e}"


async def _run_python(params: Any, ctx: ToolContext) -> str:
    """Run a Python code snippet."""
    code = params.get("code", "")
    timeout = min(params.get("timeout", 30), 60)

    if not code:
        return "Error: code is required"

    # Write to a temp file and execute
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmpfile = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", tmpfile,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return f"Error: Python script timed out after {timeout}s"

        output = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        result = output
        if err:
            result = (result + "\n[stderr]\n" + err).strip()
        if proc.returncode != 0:
            return f"Exit code: {proc.returncode}\n{result or '(no output)'}"
        return result or "(no output)"
    finally:
        try:
            os.unlink(tmpfile)
        except Exception:
            pass


async def _get_env(params: Any, ctx: ToolContext) -> str:
    """Get environment variable(s)."""
    key = params.get("key", "")
    if key:
        val = os.environ.get(key)
        if val is None:
            return f"Environment variable '{key}' is not set"
        return f"{key}={val}"
    else:
        # Return all env vars
        lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
        return "\n".join(lines)


async def _set_env(params: Any, ctx: ToolContext) -> str:
    """Set an environment variable for the current process."""
    key = params.get("key", "")
    value = params.get("value", "")
    if not key:
        return "Error: key is required"
    os.environ[key] = value
    return f"Set {key}={value}"


async def _which_command(params: Any, ctx: ToolContext) -> str:
    """Find the path of a command."""
    import shutil
    name = params.get("name", "")
    if not name:
        return "Error: name is required"
    path = shutil.which(name)
    if path:
        return f"{name} found at: {path}"
    return f"{name} not found in PATH"


def make_shell_tools() -> list:
    """Create shell execution tools."""
    return [
        FunctionTool(
            name="run_command",
            description=(
                "Execute a shell command and return its output. "
                "Supports any bash/sh command. Use for git, npm, pip, curl, grep, etc. "
                "Dangerous commands (rm -rf /, shutdown, etc.) are blocked."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (max 120, default 30)", "default": 30},
                    "cwd": {"type": "string", "description": "Working directory for the command"},
                    "capture_stderr": {"type": "boolean", "description": "Include stderr in output (default: true)", "default": True},
                },
                "required": ["command"],
            },
            func=_run_command,
        ),
        FunctionTool(
            name="run_python",
            description="Execute a Python 3 code snippet and return its output. Great for calculations, data processing, and scripting.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (max 60, default 30)", "default": 30},
                },
                "required": ["code"],
            },
            func=_run_python,
        ),
        FunctionTool(
            name="get_env",
            description="Get environment variable(s). If key is provided, returns that variable. Otherwise returns all variables.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Environment variable name (optional — omit to list all)"},
                },
                "required": [],
            },
            func=_get_env,
        ),
        FunctionTool(
            name="set_env",
            description="Set an environment variable for the current session.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Variable name"},
                    "value": {"type": "string", "description": "Variable value"},
                },
                "required": ["key", "value"],
            },
            func=_set_env,
        ),
        FunctionTool(
            name="which",
            description="Find the full path of a command/program. Useful to check if a tool is installed.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Command name to locate"},
                },
                "required": ["name"],
            },
            func=_which_command,
        ),
    ]
