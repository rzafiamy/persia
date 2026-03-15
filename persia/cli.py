"""Main CLI entry point for Persia."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.prompt import Confirm, Prompt

from .config import PersiaConfig, setup_config_interactive
from .display import (
    StreamingDisplay,
    console,
    make_thinking_spinner,
    print_banner,
    print_help,
    render_assistant_message,
    render_divider,
    render_error,
    render_history,
    render_info,
    render_success,
    render_system_status,
    render_tool_call,
    render_tool_result,
    render_tools_table,
    render_user_message,
    render_warning,
)

# ─── Prompt Toolkit Setup ─────────────────────────────────────────────────────

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style as PTStyle

    HISTORY_FILE = Path.home() / ".config" / "persia" / "input_history"
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    _PT_STYLE = PTStyle.from_dict(
        {
            "prompt": "#cc99ff bold",
            "": "#ffffff",
        }
    )
    _HAS_PROMPT_TOOLKIT = True
except ImportError:
    _HAS_PROMPT_TOOLKIT = False


def _get_prompt_input(session: Optional[object] = None) -> str:
    """Get user input with prompt_toolkit if available, else fallback."""
    prompt_text = "You › "
    if _HAS_PROMPT_TOOLKIT and session:
        try:
            return session.prompt(
                HTML(f"<prompt>{prompt_text}</prompt>"),
                style=_PT_STYLE,
                auto_suggest=AutoSuggestFromHistory(),
                multiline=False,
            )
        except KeyboardInterrupt:
            raise
        except EOFError:
            raise
        except Exception:
            pass
    return input(prompt_text)


# ─── Trace & Tool Callback Handler ───────────────────────────────────────────


class PersiaTraceHandler:
    """Handles trace events from pylemura for rich display."""

    def __init__(self, show_tools: bool = True):
        self.show_tools = show_tools
        self._tool_start_times: dict[str, float] = {}

    def __call__(self, event) -> None:
        import time
        import json as _json

        if not self.show_tools:
            return

        if event.type == "tool_call":
            tool_name = event.name
            try:
                args = _json.loads(event.data.get("arguments", "{}"))
            except Exception:
                args = {}
            render_tool_call(tool_name, args)
            self._tool_start_times[tool_name] = time.time()

        elif event.type == "tool_result":
            tool_name = event.name
            result = str(event.data.get("result", ""))
            is_error = "error" in result.lower()[:20]
            render_tool_result(tool_name, result, success=not is_error)


# ─── Session Commands ─────────────────────────────────────────────────────────


def handle_slash_command(
    cmd: str,
    agent,
    cfg: PersiaConfig,
) -> tuple[bool, bool]:
    """
    Handle /commands in the REPL.
    Returns: (handled: bool, should_exit: bool)
    """
    parts = cmd.strip().split(None, 1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("/exit", "/quit", "/q"):
        return True, True

    if command in ("/help", "/?"):
        print_help()
        return True, False

    if command == "/clear":
        console.clear()
        print_banner(model=cfg.model)
        return True, False

    if command == "/reset":
        agent.reset()
        render_success("Conversation history cleared.")
        return True, False

    if command == "/history":
        history = agent.get_history()
        render_history(history)
        return True, False

    if command == "/tools":
        tools = agent.get_tools_info()
        render_tools_table(tools)
        return True, False

    if command == "/status":
        import platform
        history = agent.get_history()
        try:
            import psutil
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.2)
            status = {
                "Model": cfg.model,
                "Base URL": cfg.base_url,
                "Conversation turns": str(len(history)),
                "Max steps": str(cfg.max_steps),
                "Platform": f"{platform.system()} {platform.release()}",
                "CPU usage": f"{cpu}%",
                "Memory": f"{mem.percent}% ({mem.used//1024//1024} MB / {mem.total//1024//1024} MB)",
                "Python": platform.python_version(),
                "Shell tools": "enabled" if cfg.allow_shell else "disabled",
                "Web tools": "enabled" if cfg.allow_web else "disabled",
            }
        except ImportError:
            status = {
                "Model": cfg.model,
                "Base URL": cfg.base_url,
                "Conversation turns": str(len(history)),
                "Platform": platform.system(),
            }
        render_system_status(status)
        return True, False

    if command == "/model":
        if not arg:
            render_info(f"Current model: {cfg.model}")
            new_model = Prompt.ask("[cyan]New model name[/cyan]", default=cfg.model)
        else:
            new_model = arg.strip()
        if new_model and new_model != cfg.model:
            cfg.model = new_model
            agent.switch_model(new_model)
            render_success(f"Switched to model: {new_model}")
        return True, False

    if command == "/system":
        if not arg:
            render_info("Current system prompt:")
            console.print(f"[dim]{cfg.system_prompt}[/dim]")
            console.print()
        else:
            cfg.system_prompt = arg
            agent.set_system_prompt(arg)
            render_success("System prompt updated. Session reset.")
        return True, False

    if command == "/save":
        path = arg.strip() or f"persia_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            history = agent.get_history()
            save_data = {
                "model": cfg.model,
                "saved_at": datetime.now().isoformat(),
                "history": history,
            }
            Path(path).write_text(json.dumps(save_data, indent=2))
            render_success(f"Conversation saved to: {path}")
        except Exception as e:
            render_error("Failed to save", str(e))
        return True, False

    if command == "/load":
        path = arg.strip()
        if not path:
            render_warning("Usage: /load <filename>")
            return True, False
        try:
            data = json.loads(Path(path).read_text())
            history = data.get("history", [])
            agent.reset()
            agent.session.load_history(history)
            render_success(f"Loaded {len(history)} turns from: {path}")
        except Exception as e:
            render_error("Failed to load", str(e))
        return True, False

    if command == "/config":
        render_system_status({
            "Config file": str(Path.home() / ".config" / "persia" / "config.json"),
            "API key": "***" + cfg.api_key[-4:] if len(cfg.api_key) > 4 else "(not set)",
            "Base URL": cfg.base_url,
            "Model": cfg.model,
            "Max tokens": str(cfg.max_tokens),
            "Max steps": str(cfg.max_steps),
            "Shell tools": str(cfg.allow_shell),
            "Web tools": str(cfg.allow_web),
            "File write": str(cfg.allow_file_write),
        })
        return True, False

    return False, False


# ─── Async REPL Core ─────────────────────────────────────────────────────────


async def run_repl(cfg: PersiaConfig, verbose: bool = False) -> None:
    """Run the interactive REPL loop."""
    from .agent import PersiaAgent

    trace_handler = PersiaTraceHandler(show_tools=cfg.show_tool_calls)

    # Patch the session config to include trace callback
    original_system_prompt = cfg.system_prompt
    agent = PersiaAgent(cfg, verbose=verbose)

    # Inject trace handler — rebuild session with on_trace
    from pylemura import (
        OpenAICompatibleAdapter,
        OpenAICompatibleAdapterConfig,
        SessionManager,
        SandwichCompressionStrategy,
        SandwichCompressionConfig,
        DefaultLogger,
        LogLevel,
    )
    from pylemura.types.agent import SessionConfig
    from .tools import (
        make_filesystem_tools, make_shell_tools, make_system_tools,
        make_web_tools, make_clipboard_tools,
    )

    adapter_cfg = OpenAICompatibleAdapterConfig(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        default_model=cfg.model,
    )
    adapter = OpenAICompatibleAdapter(adapter_cfg)

    tools = []
    tools.extend(make_filesystem_tools())
    if cfg.allow_shell:
        tools.extend(make_shell_tools())
    tools.extend(make_system_tools())
    if cfg.allow_web:
        tools.extend(make_web_tools())
    tools.extend(make_clipboard_tools())

    compression = SandwichCompressionStrategy(
        SandwichCompressionConfig(
            preserve_first=2,
            preserve_last=6,
            trigger_ratio=0.80,
            priority=20,
            summary_max_tokens=600,
        )
    )

    logger = DefaultLogger(
        level=LogLevel.DEBUG if verbose else LogLevel.WARN,
        colorize=True,
    )

    session_cfg = SessionConfig(
        adapter=adapter,
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        max_completion_tokens=cfg.max_completion_tokens,
        max_steps=cfg.max_steps,
        tools=tools,
        system_prompt=cfg.system_prompt,
        compression_strategies=[compression],
        logger=logger,
        on_trace=trace_handler,
    )

    session = SessionManager(session_cfg)

    # Setup prompt_toolkit session
    pt_session = None
    if _HAS_PROMPT_TOOLKIT:
        pt_session = PromptSession(
            history=FileHistory(str(HISTORY_FILE)),
            auto_suggest=AutoSuggestFromHistory(),
            style=_PT_STYLE,
        )

    render_info("Type your message and press Enter. Type [bold]/help[/bold] for commands, [bold]/exit[/bold] to quit.")
    render_info(f"Streaming: {'on' if cfg.streaming else 'off'} | Tools: {len(tools)} available")
    console.print()

    while True:
        try:
            # Get user input
            user_input = _get_prompt_input(pt_session)
        except (KeyboardInterrupt, EOFError):
            console.print()
            render_info("Goodbye! ✦")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            # Create a thin agent wrapper for commands that need it
            class _AgentProxy:
                def reset(self): session.reset()
                def get_history(self): return [{"role": t.role, "content": str(t.content)} for t in session.get_history()]
                def get_tools_info(self): return [{"name": t.name, "description": t.description} for t in tools]
                def switch_model(self, model):
                    nonlocal session
                    cfg.model = model
                    # Rebuild session with new model
                    new_cfg = SessionConfig(
                        adapter=OpenAICompatibleAdapter(
                            OpenAICompatibleAdapterConfig(
                                base_url=cfg.base_url,
                                api_key=cfg.api_key,
                                default_model=model,
                            )
                        ),
                        model=model,
                        max_tokens=cfg.max_tokens,
                        max_completion_tokens=cfg.max_completion_tokens,
                        max_steps=cfg.max_steps,
                        tools=tools,
                        system_prompt=cfg.system_prompt,
                        compression_strategies=[compression],
                        logger=logger,
                        on_trace=trace_handler,
                    )
                    session = SessionManager(new_cfg)
                def set_system_prompt(self, prompt):
                    cfg.system_prompt = prompt
                    session.reset()

            handled, should_exit = handle_slash_command(user_input, _AgentProxy(), cfg)
            if should_exit:
                render_info("Goodbye! ✦")
                break
            if not handled:
                render_warning(f"Unknown command: {user_input.split()[0]}. Type /help for available commands.")
            continue

        # Display user message
        render_user_message(user_input)

        # Run agent
        try:
            if cfg.streaming:
                # Streaming mode
                display = StreamingDisplay(title="Persia")
                display.start()
                try:
                    async for chunk in session.stream(user_input):
                        if chunk.delta:
                            display.append(chunk.delta)
                    display.stop()
                except KeyboardInterrupt:
                    display.stop()
                    console.print()
                    render_warning("Request cancelled.")
                    continue
                except Exception as e:
                    display.stop()
                    raise e
            else:
                # Non-streaming mode with spinner
                spinner = make_thinking_spinner()
                with spinner:
                    task = spinner.add_task("thinking")
                    response = await session.run(user_input)
                render_assistant_message(response)

        except KeyboardInterrupt:
            console.print()
            render_warning("Request cancelled.")
            continue
        except Exception as e:
            err_str = str(e)
            if "api_key" in err_str.lower() or "authentication" in err_str.lower() or "401" in err_str:
                render_error(
                    "Authentication failed",
                    "Your API key may be invalid. Run: persia configure"
                )
            elif "rate_limit" in err_str.lower() or "429" in err_str:
                render_error("Rate limit exceeded", "Please wait a moment and try again.")
            elif "context" in err_str.lower() and "overflow" in err_str.lower():
                render_warning("Context window full — resetting conversation.")
                session.reset()
            elif "connection" in err_str.lower() or "timeout" in err_str.lower():
                render_error("Connection error", f"Could not reach {cfg.base_url}")
            else:
                render_error("Agent error", err_str[:200])

    await session.close()


# ─── Single Query Mode ────────────────────────────────────────────────────────


async def run_once(cfg: PersiaConfig, message: str, verbose: bool = False) -> None:
    """Run a single query and print the result."""
    from pylemura import (
        OpenAICompatibleAdapter,
        OpenAICompatibleAdapterConfig,
        SessionManager,
        SandwichCompressionStrategy,
        SandwichCompressionConfig,
        DefaultLogger,
        LogLevel,
    )
    from pylemura.types.agent import SessionConfig
    from .tools import (
        make_filesystem_tools, make_shell_tools, make_system_tools,
        make_web_tools, make_clipboard_tools,
    )

    adapter = OpenAICompatibleAdapter(
        OpenAICompatibleAdapterConfig(
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            default_model=cfg.model,
        )
    )

    tools = []
    tools.extend(make_filesystem_tools())
    if cfg.allow_shell:
        tools.extend(make_shell_tools())
    tools.extend(make_system_tools())
    if cfg.allow_web:
        tools.extend(make_web_tools())
    tools.extend(make_clipboard_tools())

    logger = DefaultLogger(level=LogLevel.DEBUG if verbose else LogLevel.WARN)

    trace_handler = PersiaTraceHandler(show_tools=cfg.show_tool_calls)

    session_cfg = SessionConfig(
        adapter=adapter,
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        max_completion_tokens=cfg.max_completion_tokens,
        max_steps=cfg.max_steps,
        tools=tools,
        system_prompt=cfg.system_prompt,
        logger=logger,
        on_trace=trace_handler,
    )

    session = SessionManager(session_cfg)

    try:
        if cfg.streaming:
            display = StreamingDisplay(title="Persia")
            display.start()
            async for chunk in session.stream(message):
                if chunk.delta:
                    display.append(chunk.delta)
            display.stop()
        else:
            spinner = make_thinking_spinner()
            with spinner:
                spinner.add_task("thinking")
                response = await session.run(message)
            render_assistant_message(response)
    except Exception as e:
        render_error("Error", str(e))
        sys.exit(1)
    finally:
        await session.close()


# ─── CLI Commands ─────────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option("--model", "-m", default=None, help="LLM model to use (overrides config)")
@click.option("--api-key", "-k", default=None, envvar="PERSIA_API_KEY", help="API key")
@click.option("--base-url", "-b", default=None, help="API base URL")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--no-stream", is_flag=True, help="Disable streaming output")
@click.option("--no-tools", is_flag=True, help="Hide tool call display")
@click.option("--no-banner", is_flag=True, help="Skip startup banner")
@click.pass_context
def cli(
    ctx: click.Context,
    model: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str],
    verbose: bool,
    no_stream: bool,
    no_tools: bool,
    no_banner: bool,
) -> None:
    """
    ✦ Persia — Autonomous AI Agent CLI

    Run without arguments to start the interactive REPL.
    Use 'persia ask "your question"' for a single query.
    """
    cfg = PersiaConfig.load()

    # Apply CLI overrides
    if model:
        cfg.model = model
    if api_key:
        cfg.api_key = api_key
    if base_url:
        cfg.base_url = base_url
    if no_stream:
        cfg.streaming = False
    if no_tools:
        cfg.show_tool_calls = False

    ctx.ensure_object(dict)
    ctx.obj["cfg"] = cfg
    ctx.obj["verbose"] = verbose
    ctx.obj["no_banner"] = no_banner

    if ctx.invoked_subcommand is None:
        # Enter interactive REPL
        if not cfg.is_configured():
            cfg = setup_config_interactive(cfg)
            if not cfg.is_configured():
                render_error("No API key configured.", "Run: persia configure")
                sys.exit(1)

        if not no_banner:
            print_banner(model=cfg.model)

        asyncio.run(run_repl(cfg, verbose=verbose))


@cli.command()
@click.argument("message", nargs=-1, required=True)
@click.pass_context
def ask(ctx: click.Context, message: tuple[str, ...]) -> None:
    """Ask a single question and get an answer.

    \b
    Examples:
      persia ask "list files in my Downloads folder"
      persia ask "what's my public IP?"
      persia ask "summarize the file ~/notes.txt"
    """
    cfg = ctx.obj["cfg"]
    verbose = ctx.obj["verbose"]
    no_banner = ctx.obj["no_banner"]

    if not cfg.is_configured():
        render_error("No API key configured.", "Run: persia configure")
        sys.exit(1)

    full_message = " ".join(message)

    if not no_banner:
        print_banner(model=cfg.model)

    asyncio.run(run_once(cfg, full_message, verbose=verbose))


@cli.command()
@click.pass_context
def configure(ctx: click.Context) -> None:
    """Interactively configure Persia (API key, model, etc.)."""
    cfg = ctx.obj.get("cfg", PersiaConfig.load())
    print_banner()
    setup_config_interactive(cfg)


@cli.command()
@click.pass_context
def tools(ctx: click.Context) -> None:
    """List all available tools."""
    from .tools import (
        make_filesystem_tools, make_shell_tools, make_system_tools,
        make_web_tools, make_clipboard_tools,
    )
    cfg = ctx.obj["cfg"]
    all_tools = []
    all_tools.extend(make_filesystem_tools())
    if cfg.allow_shell:
        all_tools.extend(make_shell_tools())
    all_tools.extend(make_system_tools())
    if cfg.allow_web:
        all_tools.extend(make_web_tools())
    all_tools.extend(make_clipboard_tools())

    render_tools_table([{"name": t.name, "description": t.description} for t in all_tools])


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show system and configuration status."""
    import platform
    cfg = ctx.obj["cfg"]
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.5)
        system_info = {
            "Platform": f"{platform.system()} {platform.release()}",
            "CPU": f"{cpu}%",
            "Memory": f"{mem.percent}% used ({mem.used//1024**2} MB / {mem.total//1024**2} MB)",
        }
    except ImportError:
        system_info = {"Platform": platform.system()}

    render_system_status({
        "Model": cfg.model,
        "API Base URL": cfg.base_url,
        "API Key": ("***" + cfg.api_key[-4:]) if len(cfg.api_key) >= 4 else ("(set)" if cfg.api_key else "(not configured)"),
        "Max tokens": str(cfg.max_tokens),
        "Max steps": str(cfg.max_steps),
        "Streaming": str(cfg.streaming),
        "Shell tools": str(cfg.allow_shell),
        "Web tools": str(cfg.allow_web),
        **system_info,
    })


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--model", "-m", default=None, help="Model override")
@click.pass_context
def run(ctx: click.Context, file: str, model: Optional[str]) -> None:
    """Run a prompt from a text file.

    \b
    Example:
      persia run my_prompt.txt
    """
    cfg = ctx.obj["cfg"]
    verbose = ctx.obj["verbose"]

    if model:
        cfg.model = model

    if not cfg.is_configured():
        render_error("No API key configured.", "Run: persia configure")
        sys.exit(1)

    message = Path(file).read_text().strip()
    if not message:
        render_error("File is empty.", file)
        sys.exit(1)

    render_info(f"Running prompt from: {file}")
    asyncio.run(run_once(cfg, message, verbose=verbose))


def main() -> None:
    """Entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
