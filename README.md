# Persia ✦

**A powerful autonomous AI agent CLI for your PC — powered by [pylemura](https://github.com/rzafiamy/pylemura).**

[![PyPI version](https://img.shields.io/pypi/v/persia.svg?style=flat-square)](https://pypi.org/project/persia/)
[![License](https://img.shields.io/github/license/rzafiamy/persia?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org/)
[![pylemura](https://img.shields.io/badge/powered%20by-pylemura-purple?style=flat-square)](https://github.com/rzafiamy/pylemura)

---

Persia is a terminal-first autonomous AI assistant that runs on your machine. It gives an LLM full access to your filesystem, shell, system processes, clipboard, and the web — wrapped in a beautiful, streaming-capable CLI built with [Rich](https://github.com/Textualize/rich) and [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit).

```
  ✦  PERSIA  ✦
  Autonomous AI Agent CLI
  Model: Qwen3.5-4B
  v0.1.0
```

---

## ✨ Features

- **🤖 Autonomous agent** — ReAct loop powered by pylemura; chains tools automatically to complete complex tasks
- **🖥️ 30 built-in PC tools** — filesystem, shell, Python REPL, system monitor, web search, clipboard, notifications
- **🌊 Streaming responses** — token-by-token output with live Rich panel rendering
- **🔒 Safety layer** — shell firewall blocks dangerous commands; confirmations for destructive ops
- **🌐 Provider-agnostic** — works with OpenAI, Groq, Together, Mistral, Ollama, and any OpenAI-compatible API
- **📖 Conversation history** — persistent input history, `/save` / `/load` sessions
- **⚙️ Fully configurable** — `.env`, JSON config, or CLI flags; advanced pylemura settings exposed
- **🎨 Beautiful console UI** — panels, tables, syntax-highlighted code, live streaming display

---

## 🚀 Install

```bash
pip install persia
```

Or from source (editable):

```bash
git clone https://github.com/rzafiamy/persia
cd persia
pip install -e .
```

---

## ⚙️ Quick Setup

**1. Copy the example env file:**
```bash
cp .env.example .env
```

**2. Fill in your credentials:**
```ini
PERSIA_API_KEY=your_api_key_here
PERSIA_BASE_URL=https://api.openai.com/v1
PERSIA_MODEL=gpt-4o-mini
```

**3. Launch:**
```bash
persia
```

Or use the interactive setup wizard:
```bash
persia configure
```

---

## 🖥️ Usage

### Interactive REPL (default)

```bash
persia
```

Just type naturally. Persia understands plain English and will use its tools automatically.

### Single Query

```bash
persia ask "show me what's eating my CPU"
persia ask "find all TODO comments in ~/projects/myapp"
persia ask "download the latest nginx release notes"
```

### Other Commands

```bash
persia tools          # List all 30 available tools
persia status         # System info + config overview
persia configure      # Interactive setup wizard
persia run task.txt   # Run a prompt from a file
```

### CLI Flags

```bash
persia --model gpt-4o          # Override model for this session
persia --base-url http://localhost:11434/v1  # Use local Ollama
persia --no-stream             # Disable streaming output
persia --no-tools              # Hide tool call display
persia --verbose               # Enable debug logging
persia --no-banner             # Skip startup banner
```

---

## 🛠️ Built-in Tools (30)

| Category | Tools |
|---|---|
| **Filesystem** | `read_file` `write_file` `list_directory` `find_files` `search_in_files` `delete_file` `move_file` `copy_file` `create_directory` `get_file_info` |
| **Shell** | `run_command` `run_python` `get_env` `set_env` `which` |
| **System** | `get_system_info` `list_processes` `kill_process` `get_network_info` `check_port` `get_current_user` |
| **Web** | `web_search` `fetch_url` `download_file` `get_ip_info` |
| **Desktop** | `read_clipboard` `write_clipboard` `open_url` `open_file` `send_notification` |

---

## 💡 Example Tasks

```bash
# Sysadmin
persia ask "what process is using port 8080?"
persia ask "show me the top 10 memory-hungry processes"
persia ask "tail the last 50 lines of /var/log/syslog"

# Development
persia ask "find all Python files in ~/projects that import requests"
persia ask "run the tests in ./tests/ and summarize failures"
persia ask "create a git commit message for my staged changes"

# Research
persia ask "search for the latest Python 3.13 release notes and summarize"
persia ask "fetch https://api.github.com/repos/python/cpython/releases/latest"

# Automation
persia ask "rename all .jpeg files in ~/Downloads to .jpg"
persia ask "copy my clipboard content to a new file called notes.md"
persia ask "send me a desktop notification when my build script finishes"
```

---

## 📚 Documentation

See [DOCS.md](./DOCS.md) for the full guide including:
- Advanced configuration reference
- Tool firewall & security settings
- Connecting to local models (Ollama, LM Studio)
- Tips, tricks & power-user patterns
- Extending Persia with custom tools

---

## ⚙️ Configuration

Persia uses a layered configuration system (later sources override earlier ones):

```
Defaults → ~/.config/persia/config.json → ~/.config/persia/.env → ./.env → CLI flags
```

All settings can be set via `.env` variables. See [`.env.example`](./.env.example) for the complete reference.

---

## 🔌 Provider Examples

**OpenAI**
```ini
PERSIA_API_KEY=sk-...
PERSIA_BASE_URL=https://api.openai.com/v1
PERSIA_MODEL=gpt-4o
```

**Ollama (local)**
```ini
PERSIA_API_KEY=ollama
PERSIA_BASE_URL=http://localhost:11434/v1
PERSIA_MODEL=llama3.2
```

**Groq**
```ini
PERSIA_API_KEY=gsk_...
PERSIA_BASE_URL=https://api.groq.com/openai/v1
PERSIA_MODEL=llama-3.3-70b-versatile
```

**Together AI**
```ini
PERSIA_API_KEY=...
PERSIA_BASE_URL=https://api.together.xyz/v1
PERSIA_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
```

---

## 📝 License

MIT © 2026 — see [LICENSE](./LICENSE)

---

> Built on [pylemura](https://github.com/rzafiamy/pylemura) — a provider-agnostic agentic AI runtime for Python.
