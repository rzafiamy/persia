"""System monitoring and management tools for Persia."""
from __future__ import annotations

import json
import os
import platform
from typing import Any

from pylemura.types.tools import FunctionTool
from pylemura.types.tools import ToolContext


async def _get_system_info(params: Any, ctx: ToolContext) -> str:
    """Get comprehensive system information."""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        cpu_count_physical = psutil.cpu_count(logical=False)

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disk_parts = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk_parts.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fs": part.fstype,
                    "total": f"{usage.total / 1024**3:.1f} GB",
                    "used": f"{usage.used / 1024**3:.1f} GB",
                    "free": f"{usage.free / 1024**3:.1f} GB",
                    "percent": f"{usage.percent}%",
                })
            except Exception:
                continue

        net = psutil.net_io_counters()
        boot_time = psutil.boot_time()

        import time
        uptime_secs = int(time.time() - boot_time)
        h, rem = divmod(uptime_secs, 3600)
        m, s = divmod(rem, 60)

        info = {
            "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "hostname": platform.node(),
            "python": platform.python_version(),
            "cpu_cores": f"{cpu_count_physical} physical / {cpu_count} logical",
            "cpu_usage": f"{cpu_percent}%",
            "memory_total": f"{mem.total / 1024**3:.1f} GB",
            "memory_used": f"{mem.used / 1024**3:.1f} GB ({mem.percent}%)",
            "memory_available": f"{mem.available / 1024**3:.1f} GB",
            "swap_used": f"{swap.used / 1024**3:.1f} GB / {swap.total / 1024**3:.1f} GB",
            "uptime": f"{h}h {m}m {s}s",
            "network_bytes_sent": f"{net.bytes_sent / 1024**2:.1f} MB",
            "network_bytes_recv": f"{net.bytes_recv / 1024**2:.1f} MB",
            "disks": disk_parts,
        }

        return json.dumps(info, indent=2)
    except ImportError:
        # Fallback without psutil
        info = {
            "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "hostname": platform.node(),
            "python": platform.python_version(),
            "cwd": os.getcwd(),
            "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        }
        return json.dumps(info, indent=2)


async def _list_processes(params: Any, ctx: ToolContext) -> str:
    """List running processes."""
    try:
        import psutil

        sort_by = params.get("sort_by", "cpu")  # cpu | memory | pid | name
        top_n = min(params.get("top_n", 20), 50)
        filter_name = params.get("filter_name", "")

        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "username"]):
            try:
                info = proc.info
                if filter_name and filter_name.lower() not in info["name"].lower():
                    continue
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort
        sort_key = {
            "cpu": lambda p: p.get("cpu_percent", 0) or 0,
            "memory": lambda p: p.get("memory_percent", 0) or 0,
            "pid": lambda p: p.get("pid", 0),
            "name": lambda p: (p.get("name") or "").lower(),
        }.get(sort_by, lambda p: p.get("cpu_percent", 0) or 0)

        procs.sort(key=sort_key, reverse=sort_by in ("cpu", "memory"))
        procs = procs[:top_n]

        if not procs:
            return f"No processes found matching '{filter_name}'" if filter_name else "No processes found"

        lines = [f"{'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  {'STATUS':10}  {'USER':12}  NAME"]
        lines.append("-" * 70)
        for p in procs:
            lines.append(
                f"{p.get('pid', '?'):>7}  "
                f"{(p.get('cpu_percent') or 0):>5.1f}%  "
                f"{(p.get('memory_percent') or 0):>5.1f}%  "
                f"{(p.get('status') or '?'):10}  "
                f"{(p.get('username') or '?')[:12]:12}  "
                f"{p.get('name', '?')}"
            )
        return "\n".join(lines)
    except ImportError:
        return "Error: psutil not available. Install with: pip install psutil"


async def _kill_process(params: Any, ctx: ToolContext) -> str:
    """Kill a process by PID or name."""
    try:
        import psutil
        import signal

        pid = params.get("pid")
        name = params.get("name", "")
        sig = params.get("signal", "TERM")  # TERM | KILL

        signal_map = {"TERM": signal.SIGTERM, "KILL": signal.SIGKILL, "HUP": signal.SIGHUP}
        sig_num = signal_map.get(sig.upper(), signal.SIGTERM)

        if pid:
            try:
                proc = psutil.Process(int(pid))
                proc_name = proc.name()
                proc.send_signal(sig_num)
                return f"Sent {sig} to PID {pid} ({proc_name})"
            except psutil.NoSuchProcess:
                return f"Error: No process with PID {pid}"
            except psutil.AccessDenied:
                return f"Error: Permission denied to kill PID {pid}"
        elif name:
            killed = []
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if name.lower() in proc.info["name"].lower():
                        proc.send_signal(sig_num)
                        killed.append(f"{proc.info['pid']} ({proc.info['name']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if killed:
                return f"Sent {sig} to: {', '.join(killed)}"
            return f"No processes found matching '{name}'"
        else:
            return "Error: provide either pid or name"
    except ImportError:
        return "Error: psutil not available"


async def _get_network_info(params: Any, ctx: ToolContext) -> str:
    """Get network interface information."""
    try:
        import psutil

        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True)

        result = {}
        for iface, addrs in interfaces.items():
            iface_info = {
                "addresses": [],
                "is_up": stats[iface].isup if iface in stats else False,
                "speed": f"{stats[iface].speed} Mbps" if iface in stats else "?",
            }
            for addr in addrs:
                iface_info["addresses"].append({
                    "family": str(addr.family).split(".")[-1],
                    "address": addr.address,
                    "netmask": addr.netmask,
                })
            if iface in counters:
                c = counters[iface]
                iface_info["bytes_sent"] = f"{c.bytes_sent / 1024**2:.1f} MB"
                iface_info["bytes_recv"] = f"{c.bytes_recv / 1024**2:.1f} MB"
            result[iface] = iface_info

        return json.dumps(result, indent=2)
    except ImportError:
        return "Error: psutil not available"


async def _check_port(params: Any, ctx: ToolContext) -> str:
    """Check if a port is in use and who is using it."""
    import asyncio
    import socket

    port = params.get("port")
    host = params.get("host", "localhost")

    if port is None:
        return "Error: port is required"

    # Check if port is open
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=2
        )
        writer.close()
        await writer.wait_closed()
        port_open = True
    except Exception:
        port_open = False

    result = f"Port {port} on {host}: {'OPEN' if port_open else 'CLOSED'}\n"

    # Check what's using it locally
    try:
        import psutil
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid) if conn.pid else None
                    result += f"Used by PID {conn.pid}"
                    if proc:
                        result += f" ({proc.name()})"
                    result += f" — status: {conn.status}\n"
                except Exception:
                    result += f"Used by PID {conn.pid}\n"
    except ImportError:
        pass

    return result.strip()


async def _get_current_user(params: Any, ctx: ToolContext) -> str:
    """Get current user information."""
    import pwd
    try:
        pw = pwd.getpwuid(os.getuid())
        info = {
            "username": pw.pw_name,
            "uid": pw.pw_uid,
            "gid": pw.pw_gid,
            "home": pw.pw_dir,
            "shell": pw.pw_shell,
            "gecos": pw.pw_gecos,
        }
    except Exception:
        info = {
            "username": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
            "home": str(os.path.expanduser("~")),
        }
    return json.dumps(info, indent=2)


def make_system_tools() -> list:
    """Create system monitoring and management tools."""
    return [
        FunctionTool(
            name="get_system_info",
            description=(
                "Get comprehensive system information: CPU, memory, disk, network, uptime, "
                "platform details. Use this to understand the current state of the user's machine."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            func=_get_system_info,
        ),
        FunctionTool(
            name="list_processes",
            description="List running processes sorted by CPU or memory usage.",
            parameters={
                "type": "object",
                "properties": {
                    "sort_by": {"type": "string", "enum": ["cpu", "memory", "pid", "name"], "description": "Sort order (default: cpu)", "default": "cpu"},
                    "top_n": {"type": "integer", "description": "Number of processes to show (max 50, default 20)", "default": 20},
                    "filter_name": {"type": "string", "description": "Filter processes by name substring"},
                },
                "required": [],
            },
            func=_list_processes,
        ),
        FunctionTool(
            name="kill_process",
            description="Send a signal to a process by PID or name. Use signal TERM for graceful shutdown, KILL to force-quit.",
            parameters={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID to kill"},
                    "name": {"type": "string", "description": "Process name to kill (kills all matching)"},
                    "signal": {"type": "string", "enum": ["TERM", "KILL", "HUP"], "description": "Signal to send (default: TERM)", "default": "TERM"},
                },
                "required": [],
            },
            func=_kill_process,
        ),
        FunctionTool(
            name="get_network_info",
            description="Get network interface information including IP addresses, speed, and traffic statistics.",
            parameters={"type": "object", "properties": {}, "required": []},
            func=_get_network_info,
        ),
        FunctionTool(
            name="check_port",
            description="Check if a network port is open/in use and identify which process is using it.",
            parameters={
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "Port number to check"},
                    "host": {"type": "string", "description": "Host to check (default: localhost)", "default": "localhost"},
                },
                "required": ["port"],
            },
            func=_check_port,
        ),
        FunctionTool(
            name="get_current_user",
            description="Get information about the current user (username, home dir, shell, UID).",
            parameters={"type": "object", "properties": {}, "required": []},
            func=_get_current_user,
        ),
    ]
