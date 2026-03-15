"""Agent session setup for Persia."""
from __future__ import annotations

import asyncio
from typing import Optional

from pylemura import (
    DefaultLogger,
    LogLevel,
    OpenAICompatibleAdapter,
    OpenAICompatibleAdapterConfig,
    SessionManager,
    SandwichCompressionStrategy,
    SandwichCompressionConfig,
)
from pylemura.types.agent import SessionConfig

from .config import PersiaConfig
from .tools import (
    make_filesystem_tools,
    make_shell_tools,
    make_system_tools,
    make_web_tools,
    make_clipboard_tools,
)


class PersiaAgent:
    """Wrapper around pylemura SessionManager with Persia-specific configuration."""

    def __init__(self, cfg: PersiaConfig, verbose: bool = False):
        self.cfg = cfg
        self._session: Optional[SessionManager] = None
        self._verbose = verbose

    def _build_session(self) -> SessionManager:
        """Build and configure the agent session."""
        # LLM adapter
        adapter_cfg = OpenAICompatibleAdapterConfig(
            base_url=self.cfg.base_url,
            api_key=self.cfg.api_key,
            default_model=self.cfg.model,
        )
        adapter = OpenAICompatibleAdapter(adapter_cfg)

        # Tools
        tools = []
        tools.extend(make_filesystem_tools())
        if self.cfg.allow_shell:
            tools.extend(make_shell_tools())
        tools.extend(make_system_tools())
        if self.cfg.allow_web:
            tools.extend(make_web_tools())
        tools.extend(make_clipboard_tools())

        # Context compression
        compression = SandwichCompressionStrategy(
            SandwichCompressionConfig(
                preserve_first=2,
                preserve_last=6,
                trigger_ratio=0.80,
                priority=20,
                summary_max_tokens=600,
            )
        )

        # Logger
        logger = DefaultLogger(
            level=LogLevel.DEBUG if self._verbose else LogLevel.WARN,
            colorize=True,
        )

        session_cfg = SessionConfig(
            adapter=adapter,
            model=self.cfg.model,
            max_tokens=self.cfg.max_tokens,
            max_completion_tokens=self.cfg.max_completion_tokens,
            max_steps=self.cfg.max_steps,
            tools=tools,
            system_prompt=self.cfg.system_prompt,
            compression_strategies=[compression],
            logger=logger,
        )

        return SessionManager(session_cfg)

    @property
    def session(self) -> SessionManager:
        if self._session is None:
            self._session = self._build_session()
        return self._session

    async def run(self, message: str) -> str:
        """Run a single message through the agent."""
        return await self.session.run(message)

    async def stream(self, message: str):
        """Stream a message through the agent."""
        async for chunk in self.session.stream(message):
            yield chunk

    def reset(self) -> None:
        """Reset conversation history."""
        self.session.reset()

    async def close(self) -> None:
        """Cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None

    def get_history(self) -> list[dict]:
        """Get conversation history as list of dicts."""
        turns = self.session.get_history()
        result = []
        for turn in turns:
            result.append({
                "role": turn.role,
                "content": str(turn.content),
            })
        return result

    def get_tools_info(self) -> list[dict]:
        """Get list of available tools."""
        tools = []
        for tool in self.session.get_context().turns:
            pass  # handled differently

        # Get from session config tools
        all_tools = []
        all_tools.extend(make_filesystem_tools())
        if self.cfg.allow_shell:
            all_tools.extend(make_shell_tools())
        all_tools.extend(make_system_tools())
        if self.cfg.allow_web:
            all_tools.extend(make_web_tools())
        all_tools.extend(make_clipboard_tools())

        return [
            {"name": t.name, "description": t.description}
            for t in all_tools
        ]

    def switch_model(self, model: str) -> None:
        """Switch to a different model (rebuilds session)."""
        self.cfg.model = model
        if self._session:
            # Preserve history before rebuilding
            history = self.get_history()
            asyncio.get_event_loop().run_until_complete(self.close())
            self._session = self._build_session()
            # Restore history
            self.session.load_history([{"role": t["role"], "content": t["content"]} for t in history])

    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt (rebuilds session)."""
        self.cfg.system_prompt = prompt
        if self._session:
            asyncio.get_event_loop().run_until_complete(self.close())
