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


@dataclass
class PersiaConfig:
    # LLM settings
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    max_tokens: int = 16384
    max_completion_tokens: int = 4096
    max_steps: int = 20

    # Behavior
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

    # Feature flags
    allow_shell: bool = True
    allow_file_write: bool = True
    allow_web: bool = True

    @classmethod
    def load(cls) -> "PersiaConfig":
        """Load config from file, falling back to env vars and defaults."""
        cfg = cls()

        # Load from file if exists
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                for k, v in data.items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
            except Exception:
                pass

        # Override with environment variables
        env_map = {
            "PERSIA_API_KEY": "api_key",
            "PERSIA_BASE_URL": "base_url",
            "PERSIA_MODEL": "model",
            "OPENAI_API_KEY": "api_key",
            "OPENAI_BASE_URL": "base_url",
            "OPENAI_MODEL": "model",
            "LEMURA_API_KEY": "api_key",
            "LEMURA_BASE_URL": "base_url",
            "LEMURA_MODEL": "model",
        }
        for env_key, attr in env_map.items():
            val = os.environ.get(env_key)
            if val and (attr != "api_key" or not cfg.api_key):
                setattr(cfg, attr, val)

        return cfg

    def save(self) -> None:
        """Save config to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "max_completion_tokens": self.max_completion_tokens,
            "max_steps": self.max_steps,
            "system_prompt": self.system_prompt,
            "streaming": self.streaming,
            "show_tool_calls": self.show_tool_calls,
            "allow_shell": self.allow_shell,
            "allow_file_write": self.allow_file_write,
            "allow_web": self.allow_web,
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
        "[cyan]Enter your OpenAI API key (or compatible)[/cyan]",
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
