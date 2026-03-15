# Persia — Full Documentation

> **Persia** is an autonomous AI agent CLI powered by [pylemura](https://github.com/rzafiamy/pylemura).
> This guide covers installation, configuration, all 30 tools, advanced settings, tips, and tricks.

---

## Table of Contents

1. [Installation](#1-installation)
2. [Quick Start](#2-quick-start)
3. [Configuration](#3-configuration)
   - [Layered config system](#layered-config-system)
   - [Environment variables reference](#environment-variables-reference)
   - [JSON config file](#json-config-file)
   - [Provider examples](#provider-examples)
4. [CLI Reference](#4-cli-reference)
5. [REPL Commands](#5-repl-commands)
6. [Tools Reference](#6-tools-reference)
   - [Filesystem](#filesystem-tools)
   - [Shell](#shell-tools)
   - [System](#system-tools)
   - [Web](#web-tools)
   - [Desktop & Clipboard](#desktop--clipboard-tools)
7. [Advanced: Tool Firewall](#7-advanced-tool-firewall)
8. [Advanced: Execution Budget](#8-advanced-execution-budget)
9. [Advanced: Context Compression](#9-advanced-context-compression)
10. [Tips & Tricks](#10-tips--tricks)
11. [Extending with Custom Tools](#11-extending-with-custom-tools)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Installation

```bash
pip install persia
```

**From source (editable):**
```bash
git clone https://github.com/rzafiamy/persia
cd persia
pip install -e .
```

**Optional dependencies:**
```bash
# Better clipboard support
pip install pyperclip

# System monitoring
pip install psutil

# Already included in persia's dependencies ↑
```

---

## 2. Quick Start

```bash
# 1. Copy the example env file
cp .env.example .env

# 2. Edit .env with your API key
nano .env

# 3. Launch the interactive REPL
persia

# Or ask a single question
persia ask "what's eating my disk space?"
```

**First-time setup wizard:**
```bash
persia configure
```

---

## 3. Configuration

### Layered Config System

Persia reads configuration from multiple sources in this priority order
(later sources override earlier ones):

```
1. Built-in defaults
2. ~/.config/persia/config.json      (saved via `persia configure`)
3. ~/.config/persia/.env             (user-global .env)
4. ./.env                            (project-local .env)  ← highest .env priority
5. Shell environment variables
6. CLI flags (--model, --api-key…)   ← absolute highest priority
```

### Environment Variables Reference

#### Provider

| Variable | Description | Default |
|---|---|---|
| `PERSIA_API_KEY` | API key (also accepts `OPENAI_API_KEY`, `LEMURA_API_KEY`) | _(required)_ |
| `PERSIA_BASE_URL` | API base URL | `https://api.openai.com/v1` |
| `PERSIA_MODEL` | Default model name | `gpt-4o-mini` |
| `PERSIA_TIMEOUT` | HTTP request timeout (seconds) | `30` |
| `PERSIA_MAX_RETRIES` | Retry attempts on transient errors | `3` |

#### Context & Tokens

| Variable | Description | Default |
|---|---|---|
| `PERSIA_MAX_TOKENS` | Context window size (tokens) | `16384` |
| `PERSIA_MAX_COMPLETION_TOKENS` | Max tokens per response | `4096` |
| `PERSIA_MAX_STEPS` | Max tool calls per user turn | `20` |

#### Behaviour

| Variable | Description | Default |
|---|---|---|
| `PERSIA_STREAMING` | Stream tokens live (`true`/`false`) | `true` |
| `PERSIA_SHOW_TOOL_CALLS` | Display tool names & args | `true` |
| `PERSIA_MAX_HISTORY` | Turns to keep before compression | `50` |
| `PERSIA_SYSTEM_PROMPT` | Custom system prompt | _(Persia persona)_ |
| `PERSIA_LOG_LEVEL` | `debug`/`info`/`warn`/`error` | `warn` |

#### Tool Categories

| Variable | Description | Default |
|---|---|---|
| `PERSIA_ALLOW_SHELL` | Enable shell & Python tools | `true` |
| `PERSIA_ALLOW_FILE_WRITE` | Enable write/delete/move file tools | `true` |
| `PERSIA_ALLOW_WEB` | Enable web search & fetch tools | `true` |
| `PERSIA_ALLOW_DESKTOP` | Enable clipboard & notification tools | `true` |

#### Shell Safety

| Variable | Description | Default |
|---|---|---|
| `PERSIA_SHELL_TIMEOUT` | Shell command timeout (seconds) | `30` |
| `PERSIA_PYTHON_TIMEOUT` | Python snippet timeout (seconds) | `30` |

#### Tool Firewall

| Variable | Description | Default |
|---|---|---|
| `PERSIA_FIREWALL_DEFAULT` | Default decision: `accept`/`deny`/`ask` | `accept` |
| `PERSIA_FIREWALL_ASK_TOOLS` | Comma-separated tools requiring confirmation | `delete_file,kill_process` |
| `PERSIA_FIREWALL_DENY_TOOLS` | Comma-separated tools always blocked | _(none)_ |
| `PERSIA_FIREWALL_ALLOW_TOOLS` | Comma-separated tools always allowed | _(none)_ |

#### Execution Budget

| Variable | Description | Default |
|---|---|---|
| `PERSIA_BUDGET_MAX_TOTAL_CALLS` | Max total tool calls (0 = unlimited) | `0` |
| `PERSIA_BUDGET_PER_TOOL` | Per-tool limits: `cmd:10,search:5` | _(none)_ |
| `PERSIA_MAX_TOKENS_PER_TOOL` | Max chars from a single tool response | `8000` |

#### Context Compression

| Variable | Description | Default |
|---|---|---|
| `PERSIA_COMPRESSION_STRATEGY` | `sandwich`/`history`/`none` | `sandwich` |
| `PERSIA_COMPRESSION_TRIGGER` | Compress when context is X% full | `0.80` |
| `PERSIA_COMPRESSION_PRESERVE_FIRST` | Turns to keep at start | `2` |
| `PERSIA_COMPRESSION_PRESERVE_LAST` | Turns to keep at end | `6` |
| `PERSIA_COMPRESSION_SUMMARY_TOKENS` | Max tokens for the summary | `600` |

---

### JSON Config File

The JSON config at `~/.config/persia/config.json` mirrors all settings above as nested JSON:

```json
{
  "api_key": "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "max_tokens": 16384,
  "max_completion_tokens": 4096,
  "max_steps": 20,
  "streaming": true,
  "show_tool_calls": true,
  "allow_shell": true,
  "allow_file_write": true,
  "allow_web": true,
  "allow_desktop": true,
  "firewall": {
    "default": "accept",
    "ask_tools": ["delete_file", "kill_process"],
    "deny_tools": [],
    "allow_tools": []
  },
  "budget": {
    "max_total_calls": 0,
    "per_tool": {},
    "max_tokens_per_tool": 8000
  },
  "compression": {
    "strategy": "sandwich",
    "trigger": 0.80,
    "preserve_first": 2,
    "preserve_last": 6,
    "summary_tokens": 600
  }
}
```

---

### Provider Examples

**OpenAI**
```ini
PERSIA_API_KEY=sk-proj-...
PERSIA_BASE_URL=https://api.openai.com/v1
PERSIA_MODEL=gpt-4o
PERSIA_MAX_TOKENS=128000
```

**Ollama (local, no key needed)**
```ini
PERSIA_API_KEY=ollama
PERSIA_BASE_URL=http://localhost:11434/v1
PERSIA_MODEL=llama3.2
PERSIA_MAX_TOKENS=131072
```

**Groq (fastest inference)**
```ini
PERSIA_API_KEY=gsk_...
PERSIA_BASE_URL=https://api.groq.com/openai/v1
PERSIA_MODEL=llama-3.3-70b-versatile
PERSIA_MAX_TOKENS=32768
```

**Together AI**
```ini
PERSIA_API_KEY=...
PERSIA_BASE_URL=https://api.together.xyz/v1
PERSIA_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
PERSIA_MAX_TOKENS=65536
```

**Mistral**
```ini
PERSIA_API_KEY=...
PERSIA_BASE_URL=https://api.mistral.ai/v1
PERSIA_MODEL=mistral-large-latest
PERSIA_MAX_TOKENS=32768
```

**LM Studio (local)**
```ini
PERSIA_API_KEY=lm-studio
PERSIA_BASE_URL=http://localhost:1234/v1
PERSIA_MODEL=local-model
```

---

## 4. CLI Reference

```
persia [OPTIONS] COMMAND [ARGS]
```

### Global Options

| Flag | Description |
|---|---|
| `-m, --model TEXT` | Override model for this session |
| `-k, --api-key TEXT` | Override API key |
| `-b, --base-url TEXT` | Override API base URL |
| `-v, --verbose` | Enable debug logging |
| `--no-stream` | Disable streaming output |
| `--no-tools` | Hide tool call display |
| `--no-banner` | Skip the startup banner |

### Commands

| Command | Description |
|---|---|
| `persia` | Launch interactive REPL |
| `persia ask "..."` | Ask a single question, then exit |
| `persia configure` | Interactive setup wizard |
| `persia tools` | List all available tools |
| `persia status` | Show system + config overview |
| `persia run FILE` | Run a prompt from a text file |

---

## 5. REPL Commands

Inside the interactive REPL, type any of these slash-commands:

| Command | Description |
|---|---|
| `/help` | Show all commands |
| `/clear` | Clear the screen |
| `/reset` | Clear conversation history |
| `/history` | Show conversation turns |
| `/tools` | List available tools |
| `/status` | System & session status |
| `/model <name>` | Switch model (rebuilds session, keeps history) |
| `/system <prompt>` | Set a new system prompt |
| `/save [file]` | Save conversation to JSON |
| `/load <file>` | Load a saved conversation |
| `/config` | Show current configuration |
| `/exit` or `/quit` | Exit Persia |
| `Ctrl+C` | Cancel current in-progress request |
| `Ctrl+D` | Exit Persia |

**Input history:** Use ↑/↓ arrow keys to navigate previous inputs (saved to `~/.config/persia/input_history`).

---

## 6. Tools Reference

### Filesystem Tools

#### `read_file`
Read the contents of a file.
```
path        (required) — file path
max_bytes   (default 50000) — truncation limit
encoding    (default utf-8)
```
**Example prompt:** _"Read the contents of ~/notes.txt"_

#### `write_file`
Write or append content to a file.
```
path        (required)
content     (required)
mode        overwrite | append  (default: overwrite)
```
**Example prompt:** _"Append 'Task done' to ~/todo.txt"_

#### `list_directory`
List files and subdirectories.
```
path         (default: current directory)
show_hidden  (default: false)
max_items    (default: 200)
```
**Example prompt:** _"List everything in my Downloads folder"_

#### `find_files`
Search for files by glob pattern.
```
root        (default: current directory)
pattern     glob pattern, e.g. "*.py", "**/*.json"
max_results (default: 100)
file_type   any | file | dir
```
**Example prompt:** _"Find all Markdown files under ~/projects"_

#### `search_in_files`
Grep-like search across file contents.
```
query          (required)
root           (default: current directory)
pattern        file glob filter (default: "*")
case_sensitive (default: false)
max_results    (default: 50)
context_lines  lines around match (default: 1)
```
**Example prompt:** _"Find all files containing 'TODO' in ~/projects/myapp"_

#### `delete_file` ⚠️
Delete a file or directory.
```
path       (required)
recursive  (default: false) — required for non-empty dirs
```
**Note:** Requires firewall confirmation by default.

#### `move_file`
Move or rename a file or directory.
```
source      (required)
destination (required)
```

#### `copy_file`
Copy a file or directory.
```
source      (required)
destination (required)
```

#### `create_directory`
Create a directory (with parents).
```
path  (required)
```

#### `get_file_info`
Get metadata: size, type, permissions, timestamps.
```
path  (required)
```

---

### Shell Tools

#### `run_command`
Execute any shell command.
```
command         (required)
timeout         max seconds (default: 30, max: 120)
cwd             working directory
capture_stderr  (default: true)
```
**Examples:**
```
"run: git log --oneline -20"
"check if docker is running"
"list open network connections"
```
**Blocked commands:** `rm -rf /`, `shutdown`, `reboot`, fork bombs, and other destructive patterns.

#### `run_python`
Execute a Python 3 snippet.
```
code     (required)
timeout  (default: 30, max: 60)
```
**Examples:**
```
"calculate the SHA256 of 'hello world' in Python"
"use Python to parse ~/data.json and count unique keys"
```

#### `get_env`
Get one or all environment variables.
```
key  (optional — omit to list all)
```

#### `set_env`
Set an environment variable for the current session.
```
key    (required)
value  (required)
```

#### `which`
Find the path of a command.
```
name  (required)
```

---

### System Tools

#### `get_system_info`
Returns CPU, memory, disk, network, uptime, and platform details.

#### `list_processes`
List running processes.
```
sort_by      cpu | memory | pid | name  (default: cpu)
top_n        (default: 20, max: 50)
filter_name  substring filter
```
**Example prompt:** _"What are the top 5 processes using the most memory?"_

#### `kill_process` ⚠️
Send a signal to a process.
```
pid     process ID
name    process name (kills all matches)
signal  TERM | KILL | HUP  (default: TERM)
```
**Note:** Requires firewall confirmation by default.

#### `get_network_info`
Get all network interface addresses, speeds, and traffic stats.

#### `check_port`
Check if a port is open and which process is using it.
```
port  (required)
host  (default: localhost)
```
**Example prompt:** _"What's running on port 5432?"_

#### `get_current_user`
Get current user info: username, UID, GID, home, shell.

---

### Web Tools

#### `web_search`
Search the web using DuckDuckGo (no API key required).
```
query        (required)
max_results  (default: 5, max: 10)
```
**Example prompt:** _"Search for the latest Python security vulnerabilities"_

#### `fetch_url`
Fetch a URL and return its content as plain text (HTML stripped).
```
url       (required, must start with http:// or https://)
raw       return raw HTML (default: false)
max_chars (default: 8000)
timeout   (default: 15)
```
**Example prompt:** _"Fetch the content of https://api.github.com/repos/python/cpython/releases/latest"_

#### `download_file`
Download a file from a URL to disk.
```
url          (required)
destination  local path (default: filename from URL in current dir)
timeout      (default: 60)
```

#### `get_ip_info`
Get current public IP address and geolocation.

---

### Desktop & Clipboard Tools

#### `read_clipboard`
Read the current system clipboard contents.

#### `write_clipboard`
Write text to the clipboard.
```
text  (required)
```

#### `open_url`
Open a URL in the default browser.
```
url  (required)
```

#### `open_file`
Open a file with its default application.
```
path  (required)
```
**Example prompt:** _"Open the report at ~/reports/q1.pdf"_

#### `send_notification`
Send a desktop notification.
```
message   (required)
title     (default: "Persia")
urgency   low | normal | critical  (default: normal)
```
**Requires:** `notify-send` on Linux, native on macOS/Windows.

---

## 7. Advanced: Tool Firewall

The tool firewall intercepts every tool call before execution and applies rules.

### How it works

1. Check **allow_tools** list → if matched, always execute
2. Check **deny_tools** list → if matched, always block
3. Check **ask_tools** list → if matched, pause and prompt the user
4. Apply **default** decision for everything else

### Configuration

```ini
# Default decision for unmatched tools
PERSIA_FIREWALL_DEFAULT=accept

# These tools always pause for your confirmation
PERSIA_FIREWALL_ASK_TOOLS=delete_file,kill_process,run_command

# These tools are permanently blocked
PERSIA_FIREWALL_DENY_TOOLS=

# These tools are always allowed without check
PERSIA_FIREWALL_ALLOW_TOOLS=read_file,list_directory,get_system_info
```

### Strict / Read-only Mode

For a read-only session that can't modify anything:
```ini
PERSIA_FIREWALL_DEFAULT=deny
PERSIA_FIREWALL_ALLOW_TOOLS=read_file,list_directory,find_files,search_in_files,get_file_info,get_system_info,list_processes,get_network_info,check_port,get_current_user,web_search,fetch_url,get_ip_info,read_clipboard
PERSIA_ALLOW_SHELL=false
PERSIA_ALLOW_FILE_WRITE=false
```

### Paranoid / Ask-everything Mode

```ini
PERSIA_FIREWALL_DEFAULT=ask
```

---

## 8. Advanced: Execution Budget

Prevent runaway agents and control costs.

```ini
# Allow a maximum of 30 tool calls total per session
PERSIA_BUDGET_MAX_TOTAL_CALLS=30

# Per-tool limits
PERSIA_BUDGET_PER_TOOL=run_command:10,web_search:5,delete_file:2

# Truncate any tool response longer than 4000 chars
PERSIA_MAX_TOKENS_PER_TOOL=4000
```

**When a budget limit is reached**, pylemura raises a `LemuraMaxIterationsError` and Persia shows a clear error message.

---

## 9. Advanced: Context Compression

For long sessions, Persia compresses old turns to stay within the model's context window.

### Sandwich (default)
Keeps the **first N turns** (original context) + **last M turns** (recent context), and replaces everything in between with a compact AI-generated summary.

```ini
PERSIA_COMPRESSION_STRATEGY=sandwich
PERSIA_COMPRESSION_TRIGGER=0.80        # compress at 80% full
PERSIA_COMPRESSION_PRESERVE_FIRST=2   # keep first 2 turns
PERSIA_COMPRESSION_PRESERVE_LAST=6    # keep last 6 turns
PERSIA_COMPRESSION_SUMMARY_TOKENS=600 # summary max length
```

### History (aggressive)
Keeps only the last N turns, discarding everything older.

```ini
PERSIA_COMPRESSION_STRATEGY=history
PERSIA_COMPRESSION_PRESERVE_LAST=10
PERSIA_COMPRESSION_TRIGGER=0.85
```

### None
No compression. Session ends when context window is full.

```ini
PERSIA_COMPRESSION_STRATEGY=none
```

---

## 10. Tips & Tricks

### Be specific about paths
```
# Too vague
"find my config file"

# Much better
"find all .conf files under /etc that were modified in the last 7 days"
```

### Chain operations naturally
Persia executes multi-step tasks autonomously:
```
"check what's on port 8080, find which process owns it, and show me its logs from journald"
```

### Use /save for important sessions
Before starting a complex task:
```
/save pre-refactor-session.json
```

### Load a saved session to continue later
```
persia
/load pre-refactor-session.json
```

### Run headless with a prompt file
Create `task.txt`:
```
Scan ~/projects for any Python files that import requests but don't
have a timeout parameter in their requests.get() or requests.post() calls.
List them with the line numbers.
```
Then run:
```bash
persia run task.txt
```

### Pipe output to a file
```bash
persia --no-banner --no-stream ask "summarize /var/log/syslog errors from today" > summary.txt
```

### Use Ollama for fully offline operation
```ini
PERSIA_API_KEY=ollama
PERSIA_BASE_URL=http://localhost:11434/v1
PERSIA_MODEL=llama3.2
PERSIA_ALLOW_WEB=false   # fully offline
```

### Custom personas via system prompt
```ini
PERSIA_SYSTEM_PROMPT=You are a senior Linux sysadmin. Be terse, use CLI tools, and always show the exact commands you run.
```

### Limit exposure on shared machines
```ini
PERSIA_ALLOW_SHELL=false
PERSIA_ALLOW_FILE_WRITE=false
PERSIA_FIREWALL_DEFAULT=ask
```

### Debug mode to see everything
```bash
persia --verbose
# or
PERSIA_LOG_LEVEL=debug persia
```

### Increase steps for complex tasks
```bash
PERSIA_MAX_STEPS=50 persia ask "refactor all Python files in ~/projects/myapp to use f-strings instead of % formatting"
```

---

## 11. Extending with Custom Tools

Add your own tools by creating a new tool file and registering it in the CLI.

**Example: `persia/tools/mytools.py`**
```python
from pylemura.types.tools import FunctionTool, ToolContext
from typing import Any

async def _my_tool(params: Any, ctx: ToolContext) -> str:
    name = params.get("name", "world")
    return f"Hello, {name}!"

def make_my_tools() -> list:
    return [
        FunctionTool(
            name="hello",
            description="Greet someone by name.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"},
                },
                "required": ["name"],
            },
            func=_my_tool,
        )
    ]
```

Then register in `persia/tools/__init__.py`:
```python
from .mytools import make_my_tools
```

And add to the tool list in `cli.py`'s `run_repl` / `run_once`:
```python
tools.extend(make_my_tools())
```

The agent will automatically discover and use your tool when relevant.

---

## 12. Troubleshooting

### "No API key configured"
```bash
persia configure
# or
export PERSIA_API_KEY=your_key_here
# or add to .env in your working directory
```

### Authentication failed (401)
- Verify your key is correct and not expired
- Check that `PERSIA_BASE_URL` matches your provider
- For Ollama: use `PERSIA_API_KEY=ollama` (any non-empty string)

### Rate limit (429)
Reduce parallel requests or upgrade your API plan. Add a delay by reducing `PERSIA_MAX_STEPS`.

### Context overflow
Increase `PERSIA_MAX_TOKENS` to match your model's actual window, or lower `PERSIA_COMPRESSION_TRIGGER` to compress earlier.

### Tool timeout
Increase `PERSIA_SHELL_TIMEOUT` for long-running commands:
```ini
PERSIA_SHELL_TIMEOUT=120
```

### Clipboard not working on Linux
```bash
sudo apt install xclip
# or
sudo apt install xsel
```

### Desktop notifications not working on Linux
```bash
sudo apt install libnotify-bin
```

### Enable debug logs
```bash
PERSIA_LOG_LEVEL=debug persia
```
