"""Configuration management for Persia."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "persia"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").strip().lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, ""))
    except (ValueError, TypeError):
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, ""))
    except (ValueError, TypeError):
        return default


def _env_list(key: str) -> list[str]:
    """Parse a comma-separated env var into a list of non-empty strings."""
    val = os.environ.get(key, "").strip()
    return [x.strip() for x in val.split(",") if x.strip()] if val else []


@dataclass
class FirewallConfig:
    """Tool firewall settings."""
    default: str = "accept"          # accept | deny | ask
    ask_tools: list[str] = field(default_factory=lambda: ["delete_file", "kill_process"])
    deny_tools: list[str] = field(default_factory=list)
    allow_tools: list[str] = field(default_factory=list)


@dataclass
class BudgetConfig:
    """Tool execution budget (rate limiting)."""
    max_total_calls: int = 0          # 0 = unlimited
    per_tool: dict[str, int] = field(default_factory=dict)   # {tool_name: max_calls}
    max_tokens_per_tool: int = 8000   # max chars returned by any single tool call


@dataclass
class CompressionConfig:
    """Context compression settings."""
    strategy: str = "sandwich"        # sandwich | history | none
    trigger: float = 0.80             # compress when context is this % full
    preserve_first: int = 2
    preserve_last: int = 6
    summary_tokens: int = 600


@dataclass
class PersiaConfig:
    # ── Provider ──────────────────────────────────────────────────
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout: float = 30.0
    max_retries: int = 3

    # ── Context & tokens ──────────────────────────────────────────
    max_tokens: int = 16384
    max_completion_tokens: int = 4096
    max_steps: int = 20

    # ── Behaviour ─────────────────────────────────────────────────
    system_prompt: str = (
        "You are Persia, a powerful autonomous AI assistant running locally on the user's PC. "
        "You have access to filesystem tools, shell execution, system monitoring, web access, "
        "and clipboard management. You are proactive, helpful, and capable of performing "
        "complex multi-step tasks autonomously. When given a task, think step-by-step and "
        "use your tools effectively to complete it. Always be concise in your text responses "
        "but thorough in your actions. Warn the user before performing destructive operations."
    )
    streaming: bool = True
    show_tool_calls: bool = True
    max_history: int = 50
    log_level: str = "warn"           # debug | info | warn | error

    # ── Tool categories ───────────────────────────────────────────
    allow_shell: bool = True
    allow_file_write: bool = True
    allow_web: bool = True
    allow_desktop: bool = True

    # ── Shell safety ──────────────────────────────────────────────
    shell_timeout: int = 30
    python_timeout: int = 30

    # ── Advanced pylemura settings ────────────────────────────────
    firewall: FirewallConfig = field(default_factory=FirewallConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    compression: CompressionConfig = field(default_factory=CompressionConfig)

    @classmethod
    def load(cls) -> "PersiaConfig":
        """Load config from file, .env files, and environment variables."""
        cfg = cls()

        # 1. JSON config file
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                for k, v in data.items():
                    if k == "firewall" and isinstance(v, dict):
                        for fk, fv in v.items():
                            if hasattr(cfg.firewall, fk):
                                setattr(cfg.firewall, fk, fv)
                    elif k == "budget" and isinstance(v, dict):
                        for bk, bv in v.items():
                            if hasattr(cfg.budget, bk):
                                setattr(cfg.budget, bk, bv)
                    elif k == "compression" and isinstance(v, dict):
                        for ck, cv in v.items():
                            if hasattr(cfg.compression, ck):
                                setattr(cfg.compression, ck, cv)
                    elif hasattr(cfg, k):
                        setattr(cfg, k, v)
            except Exception:
                pass

        # 2. .env files — config dir first, then cwd (cwd wins)
        for env_file in [CONFIG_DIR / ".env", Path.cwd() / ".env"]:
            if env_file.exists():
                try:
                    for line in env_file.read_text().splitlines():
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key:
                            os.environ.setdefault(key, value)
                except Exception:
                    pass

        # 3. Environment variables — provider
        _provider_map = [
            ("PERSIA_API_KEY", "api_key"),
            ("OPENAI_API_KEY", "api_key"),
            ("LEMURA_API_KEY", "api_key"),
            ("PERSIA_BASE_URL", "base_url"),
            ("OPENAI_BASE_URL", "base_url"),
            ("LEMURA_BASE_URL", "base_url"),
            ("PERSIA_MODEL", "model"),
            ("OPENAI_MODEL", "model"),
            ("LEMURA_MODEL", "model"),
        ]
        for env_key, attr in _provider_map:
            val = os.environ.get(env_key)
            if val and (attr != "api_key" or not cfg.api_key):
                setattr(cfg, attr, val)

        # 4. All other PERSIA_* env vars
        cfg.timeout = _env_float("PERSIA_TIMEOUT", cfg.timeout)
        cfg.max_retries = _env_int("PERSIA_MAX_RETRIES", cfg.max_retries)
        cfg.max_tokens = _env_int("PERSIA_MAX_TOKENS", cfg.max_tokens)
        cfg.max_completion_tokens = _env_int("PERSIA_MAX_COMPLETION_TOKENS", cfg.max_completion_tokens)
        cfg.max_steps = _env_int("PERSIA_MAX_STEPS", cfg.max_steps)
        cfg.streaming = _env_bool("PERSIA_STREAMING", cfg.streaming)
        cfg.show_tool_calls = _env_bool("PERSIA_SHOW_TOOL_CALLS", cfg.show_tool_calls)
        cfg.max_history = _env_int("PERSIA_MAX_HISTORY", cfg.max_history)
        cfg.log_level = os.environ.get("PERSIA_LOG_LEVEL", cfg.log_level).lower()
        cfg.allow_shell = _env_bool("PERSIA_ALLOW_SHELL", cfg.allow_shell)
        cfg.allow_file_write = _env_bool("PERSIA_ALLOW_FILE_WRITE", cfg.allow_file_write)
        cfg.allow_web = _env_bool("PERSIA_ALLOW_WEB", cfg.allow_web)
        cfg.allow_desktop = _env_bool("PERSIA_ALLOW_DESKTOP", cfg.allow_desktop)
        cfg.shell_timeout = _env_int("PERSIA_SHELL_TIMEOUT", cfg.shell_timeout)
        cfg.python_timeout = _env_int("PERSIA_PYTHON_TIMEOUT", cfg.python_timeout)

        if os.environ.get("PERSIA_SYSTEM_PROMPT"):
            cfg.system_prompt = os.environ["PERSIA_SYSTEM_PROMPT"]

        # Firewall
        if os.environ.get("PERSIA_FIREWALL_DEFAULT"):
            cfg.firewall.default = os.environ["PERSIA_FIREWALL_DEFAULT"].lower()
        ask = _env_list("PERSIA_FIREWALL_ASK_TOOLS")
        if ask:
            cfg.firewall.ask_tools = ask
        deny = _env_list("PERSIA_FIREWALL_DENY_TOOLS")
        if deny:
            cfg.firewall.deny_tools = deny
        allow = _env_list("PERSIA_FIREWALL_ALLOW_TOOLS")
        if allow:
            cfg.firewall.allow_tools = allow

        # Budget
        cfg.budget.max_total_calls = _env_int("PERSIA_BUDGET_MAX_TOTAL_CALLS", cfg.budget.max_total_calls)
        cfg.budget.max_tokens_per_tool = _env_int("PERSIA_MAX_TOKENS_PER_TOOL", cfg.budget.max_tokens_per_tool)
        per_tool_raw = os.environ.get("PERSIA_BUDGET_PER_TOOL", "").strip()
        if per_tool_raw:
            for entry in per_tool_raw.split(","):
                if ":" in entry:
                    tname, _, tlimit = entry.partition(":")
                    try:
                        cfg.budget.per_tool[tname.strip()] = int(tlimit.strip())
                    except ValueError:
                        pass

        # Compression
        if os.environ.get("PERSIA_COMPRESSION_STRATEGY"):
            cfg.compression.strategy = os.environ["PERSIA_COMPRESSION_STRATEGY"].lower()
        cfg.compression.trigger = _env_float("PERSIA_COMPRESSION_TRIGGER", cfg.compression.trigger)
        cfg.compression.preserve_first = _env_int("PERSIA_COMPRESSION_PRESERVE_FIRST", cfg.compression.preserve_first)
        cfg.compression.preserve_last = _env_int("PERSIA_COMPRESSION_PRESERVE_LAST", cfg.compression.preserve_last)
        cfg.compression.summary_tokens = _env_int("PERSIA_COMPRESSION_SUMMARY_TOKENS", cfg.compression.summary_tokens)

        return cfg

    def save(self) -> None:
        """Save config to JSON file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "max_tokens": self.max_tokens,
            "max_completion_tokens": self.max_completion_tokens,
            "max_steps": self.max_steps,
            "system_prompt": self.system_prompt,
            "streaming": self.streaming,
            "show_tool_calls": self.show_tool_calls,
            "max_history": self.max_history,
            "log_level": self.log_level,
            "allow_shell": self.allow_shell,
            "allow_file_write": self.allow_file_write,
            "allow_web": self.allow_web,
            "allow_desktop": self.allow_desktop,
            "shell_timeout": self.shell_timeout,
            "python_timeout": self.python_timeout,
            "firewall": {
                "default": self.firewall.default,
                "ask_tools": self.firewall.ask_tools,
                "deny_tools": self.firewall.deny_tools,
                "allow_tools": self.firewall.allow_tools,
            },
            "budget": {
                "max_total_calls": self.budget.max_total_calls,
                "per_tool": self.budget.per_tool,
                "max_tokens_per_tool": self.budget.max_tokens_per_tool,
            },
            "compression": {
                "strategy": self.compression.strategy,
                "trigger": self.compression.trigger,
                "preserve_first": self.compression.preserve_first,
                "preserve_last": self.compression.preserve_last,
                "summary_tokens": self.compression.summary_tokens,
            },
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2))

    def is_configured(self) -> bool:
        return bool(self.api_key)


def setup_config_interactive(cfg: PersiaConfig) -> PersiaConfig:
    """Interactively set up config if not already configured."""
    from rich.prompt import Confirm, Prompt
    from .display import console, render_info

    console.print("\n[bold bright_magenta]Welcome to Persia! Let's set up your configuration.[/bold bright_magenta]\n")

    api_key = Prompt.ask(
        "[cyan]Enter your API key (OpenAI-compatible)[/cyan]",
        password=True,
        default=cfg.api_key or "",
    )
    if api_key:
        cfg.api_key = api_key

    base_url = Prompt.ask(
        "[cyan]API base URL[/cyan]",
        default=cfg.base_url,
    )
    cfg.base_url = base_url

    model = Prompt.ask(
        "[cyan]Default model[/cyan]",
        default=cfg.model,
    )
    cfg.model = model

    if Confirm.ask("[cyan]Save configuration?[/cyan]", default=True):
        cfg.save()
        render_info(f"Config saved to {CONFIG_FILE}")

    return cfg
