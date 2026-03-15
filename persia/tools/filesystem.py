"""Filesystem tools for Persia."""
from __future__ import annotations

import fnmatch
import json
import os
import shutil
from pathlib import Path
from typing import Any

from pylemura.types.tools import FunctionTool
from pylemura.types.tools import ToolContext


def _safe_path(path_str: str) -> Path:
    """Resolve and return a safe path."""
    return Path(path_str).expanduser().resolve()


async def _read_file(params: Any, ctx: ToolContext) -> str:
    path = _safe_path(params.get("path", ""))
    encoding = params.get("encoding", "utf-8")
    max_bytes = params.get("max_bytes", 50_000)

    if not path.exists():
        return f"Error: File not found: {path}"
    if not path.is_file():
        return f"Error: Not a file: {path}"

    size = path.stat().st_size
    try:
        content = path.read_bytes()[:max_bytes].decode(encoding, errors="replace")
        suffix = f"\n\n[Truncated — showing {max_bytes:,} of {size:,} bytes]" if size > max_bytes else ""
        return content + suffix
    except Exception as e:
        return f"Error reading file: {e}"


async def _write_file(params: Any, ctx: ToolContext) -> str:
    path = _safe_path(params.get("path", ""))
    content = params.get("content", "")
    mode = params.get("mode", "overwrite")  # overwrite | append

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content):,} characters to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


async def _list_directory(params: Any, ctx: ToolContext) -> str:
    path = _safe_path(params.get("path", "."))
    show_hidden = params.get("show_hidden", False)
    max_items = params.get("max_items", 200)

    if not path.exists():
        return f"Error: Directory not found: {path}"
    if not path.is_dir():
        return f"Error: Not a directory: {path}"

    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        if not show_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]
        entries = entries[:max_items]

        lines = [f"Directory: {path}\n"]
        dirs = [e for e in entries if e.is_dir()]
        files = [e for e in entries if e.is_file()]
        other = [e for e in entries if not e.is_dir() and not e.is_file()]

        for d in dirs:
            lines.append(f"  [DIR]  {d.name}/")
        for f in files:
            size = f.stat().st_size
            size_str = f"{size:,}B" if size < 1024 else f"{size/1024:.1f}KB" if size < 1024**2 else f"{size/1024**2:.1f}MB"
            lines.append(f"  [FILE] {f.name}  ({size_str})")
        for o in other:
            lines.append(f"  [LINK] {o.name}")

        lines.append(f"\n{len(dirs)} directories, {len(files)} files")
        return "\n".join(lines)
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error listing directory: {e}"


async def _find_files(params: Any, ctx: ToolContext) -> str:
    root = _safe_path(params.get("root", "."))
    pattern = params.get("pattern", "*")
    max_results = params.get("max_results", 100)
    include_hidden = params.get("include_hidden", False)
    file_type = params.get("file_type", "any")  # any | file | dir

    if not root.exists():
        return f"Error: Path not found: {root}"

    results = []
    try:
        for item in root.rglob(pattern):
            if len(results) >= max_results:
                break
            if not include_hidden and any(p.startswith(".") for p in item.parts[-3:]):
                continue
            if file_type == "file" and not item.is_file():
                continue
            if file_type == "dir" and not item.is_dir():
                continue
            results.append(str(item))

        if not results:
            return f"No files matching '{pattern}' found in {root}"

        output = f"Found {len(results)} match(es) for '{pattern}' in {root}:\n"
        output += "\n".join(f"  {r}" for r in results)
        return output
    except Exception as e:
        return f"Error searching: {e}"


async def _delete_file(params: Any, ctx: ToolContext) -> str:
    path = _safe_path(params.get("path", ""))
    recursive = params.get("recursive", False)

    if not path.exists():
        return f"Error: Path not found: {path}"

    try:
        if path.is_file() or path.is_symlink():
            path.unlink()
            return f"Deleted file: {path}"
        elif path.is_dir():
            if recursive:
                shutil.rmtree(path)
                return f"Deleted directory (recursive): {path}"
            else:
                path.rmdir()
                return f"Deleted empty directory: {path}"
    except Exception as e:
        return f"Error deleting: {e}"


async def _move_file(params: Any, ctx: ToolContext) -> str:
    src = _safe_path(params.get("source", ""))
    dst = _safe_path(params.get("destination", ""))

    if not src.exists():
        return f"Error: Source not found: {src}"

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"Moved: {src} → {dst}"
    except Exception as e:
        return f"Error moving: {e}"


async def _copy_file(params: Any, ctx: ToolContext) -> str:
    src = _safe_path(params.get("source", ""))
    dst = _safe_path(params.get("destination", ""))

    if not src.exists():
        return f"Error: Source not found: {src}"

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        return f"Copied: {src} → {dst}"
    except Exception as e:
        return f"Error copying: {e}"


async def _create_directory(params: Any, ctx: ToolContext) -> str:
    path = _safe_path(params.get("path", ""))
    try:
        path.mkdir(parents=True, exist_ok=True)
        return f"Created directory: {path}"
    except Exception as e:
        return f"Error creating directory: {e}"


async def _get_file_info(params: Any, ctx: ToolContext) -> str:
    path = _safe_path(params.get("path", ""))
    if not path.exists():
        return f"Error: Path not found: {path}"

    stat = path.stat()
    import time
    info = {
        "path": str(path),
        "type": "directory" if path.is_dir() else "file" if path.is_file() else "symlink",
        "size": f"{stat.st_size:,} bytes",
        "modified": time.ctime(stat.st_mtime),
        "created": time.ctime(stat.st_ctime),
        "permissions": oct(stat.st_mode)[-3:],
        "owner_uid": stat.st_uid,
    }
    return json.dumps(info, indent=2)


async def _search_in_files(params: Any, ctx: ToolContext) -> str:
    """Search for text content within files."""
    root = _safe_path(params.get("root", "."))
    query = params.get("query", "")
    pattern = params.get("pattern", "*")
    case_sensitive = params.get("case_sensitive", False)
    max_results = params.get("max_results", 50)
    context_lines = params.get("context_lines", 1)

    if not query:
        return "Error: query is required"

    results = []
    search_query = query if case_sensitive else query.lower()

    try:
        for filepath in root.rglob(pattern):
            if not filepath.is_file():
                continue
            if len(results) >= max_results:
                break
            try:
                lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
                for i, line in enumerate(lines):
                    haystack = line if case_sensitive else line.lower()
                    if search_query in haystack:
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        ctx_lines = "\n".join(
                            f"  {'>' if j == i else ' '} {j+1}: {lines[j]}"
                            for j in range(start, end)
                        )
                        results.append(f"{filepath}:\n{ctx_lines}")
                        if len(results) >= max_results:
                            break
            except Exception:
                continue

        if not results:
            return f"No matches for '{query}' in {root}"
        return f"Found {len(results)} match(es):\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"Error searching: {e}"


def make_filesystem_tools() -> list:
    """Create all filesystem tools."""
    return [
        FunctionTool(
            name="read_file",
            description="Read the contents of a file. Returns the file text content.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to the file"},
                    "max_bytes": {"type": "integer", "description": "Maximum bytes to read (default 50000)", "default": 50000},
                    "encoding": {"type": "string", "description": "File encoding (default utf-8)", "default": "utf-8"},
                },
                "required": ["path"],
            },
            func=_read_file,
        ),
        FunctionTool(
            name="write_file",
            description="Write or append content to a file. Creates parent directories if needed.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"], "description": "Write mode (default: overwrite)", "default": "overwrite"},
                },
                "required": ["path", "content"],
            },
            func=_write_file,
        ),
        FunctionTool(
            name="list_directory",
            description="List files and directories in a given path.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current directory)", "default": "."},
                    "show_hidden": {"type": "boolean", "description": "Show hidden files/dirs (default: false)", "default": False},
                    "max_items": {"type": "integer", "description": "Maximum items to list (default: 200)", "default": 200},
                },
                "required": [],
            },
            func=_list_directory,
        ),
        FunctionTool(
            name="find_files",
            description="Search for files/directories by name pattern (glob) in a directory tree.",
            parameters={
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "Root directory to search from (default: current dir)", "default": "."},
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py', '**/*.json')", "default": "*"},
                    "max_results": {"type": "integer", "description": "Maximum results to return", "default": 100},
                    "file_type": {"type": "string", "enum": ["any", "file", "dir"], "description": "Filter by type", "default": "any"},
                    "include_hidden": {"type": "boolean", "description": "Include hidden files", "default": False},
                },
                "required": [],
            },
            func=_find_files,
        ),
        FunctionTool(
            name="search_in_files",
            description="Search for text content within files in a directory. Returns matching lines with context.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for"},
                    "root": {"type": "string", "description": "Root directory to search (default: current dir)", "default": "."},
                    "pattern": {"type": "string", "description": "File glob pattern (e.g. '*.py')", "default": "*"},
                    "case_sensitive": {"type": "boolean", "description": "Case-sensitive search", "default": False},
                    "max_results": {"type": "integer", "description": "Maximum results", "default": 50},
                    "context_lines": {"type": "integer", "description": "Lines of context around match", "default": 1},
                },
                "required": ["query"],
            },
            func=_search_in_files,
        ),
        FunctionTool(
            name="delete_file",
            description="Delete a file or directory. Use recursive=true for non-empty directories.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to delete"},
                    "recursive": {"type": "boolean", "description": "Recursively delete directory contents", "default": False},
                },
                "required": ["path"],
            },
            func=_delete_file,
        ),
        FunctionTool(
            name="move_file",
            description="Move or rename a file or directory.",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"},
                },
                "required": ["source", "destination"],
            },
            func=_move_file,
        ),
        FunctionTool(
            name="copy_file",
            description="Copy a file or directory to a new location.",
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"},
                },
                "required": ["source", "destination"],
            },
            func=_copy_file,
        ),
        FunctionTool(
            name="create_directory",
            description="Create a new directory (and parents if needed).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create"},
                },
                "required": ["path"],
            },
            func=_create_directory,
        ),
        FunctionTool(
            name="get_file_info",
            description="Get metadata about a file or directory (size, type, permissions, timestamps).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to inspect"},
                },
                "required": ["path"],
            },
            func=_get_file_info,
        ),
    ]
