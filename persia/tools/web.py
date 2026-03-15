"""Web access tools for Persia."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus, urlparse

from pylemura.types.tools import FunctionTool
from pylemura.types.tools import ToolContext


def _is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def _strip_html(html: str) -> str:
    """Strip HTML tags and clean up whitespace."""
    # Remove scripts and style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    html = re.sub(r"<[^>]+>", " ", html)
    # Decode common HTML entities
    entities = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&nbsp;": " "}
    for ent, char in entities.items():
        html = html.replace(ent, char)
    # Clean whitespace
    html = re.sub(r"\s{3,}", "\n\n", html)
    html = re.sub(r" {2,}", " ", html)
    return html.strip()


async def _fetch_url(params: Any, ctx: ToolContext) -> str:
    """Fetch content from a URL."""
    url = params.get("url", "").strip()
    raw = params.get("raw", False)
    max_chars = params.get("max_chars", 8000)
    timeout = params.get("timeout", 15)

    if not url:
        return "Error: url is required"
    if not _is_valid_url(url):
        return f"Error: Invalid URL: {url!r} (must start with http:// or https://)"

    try:
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Persia-AI/0.1; +https://github.com/persia-ai)",
            "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            text = resp.text

            if not raw and "html" in content_type.lower():
                text = _strip_html(text)

            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n[Truncated — showing {max_chars:,} of {len(text):,} chars]"

            return f"URL: {url}\nStatus: {resp.status_code}\nContent-Type: {content_type}\n\n{text}"

    except ImportError:
        return "Error: httpx not available. Install with: pip install httpx"
    except Exception as e:
        return f"Error fetching {url}: {e}"


async def _web_search(params: Any, ctx: ToolContext) -> str:
    """Search the web using DuckDuckGo."""
    query = params.get("query", "").strip()
    max_results = min(params.get("max_results", 5), 10)
    region = params.get("region", "wt-wt")

    if not query:
        return "Error: query is required"

    try:
        import httpx

        # Use DuckDuckGo HTML search (no API key needed)
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&kl={region}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Accept": "text/html",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "kl": region},
                headers=headers,
            )
            resp.raise_for_status()

        html = resp.text

        # Parse results using regex (avoid lxml dependency)
        results = []
        # Extract result blocks
        result_blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )

        for url, title, snippet in result_blocks[:max_results]:
            # Clean up
            title = _strip_html(title).strip()
            snippet = _strip_html(snippet).strip()
            # DuckDuckGo wraps URLs in redirect links
            if "uddg=" in url:
                m = re.search(r"uddg=([^&]+)", url)
                if m:
                    from urllib.parse import unquote
                    url = unquote(m.group(1))
            results.append({"title": title, "url": url, "snippet": snippet})

        if not results:
            return f"No results found for: {query!r}\n\nTry fetching DuckDuckGo directly or use a different query."

        output = f"Search results for: {query!r}\n\n"
        for i, r in enumerate(results, 1):
            output += f"[{i}] {r['title']}\n"
            output += f"    URL: {r['url']}\n"
            output += f"    {r['snippet']}\n\n"

        return output.strip()

    except ImportError:
        return "Error: httpx not available. Install with: pip install httpx"
    except Exception as e:
        return f"Error searching: {e}"


async def _download_file(params: Any, ctx: ToolContext) -> str:
    """Download a file from a URL."""
    url = params.get("url", "").strip()
    dest = params.get("destination", "")
    timeout = params.get("timeout", 60)

    if not url:
        return "Error: url is required"
    if not _is_valid_url(url):
        return f"Error: Invalid URL: {url!r}"

    if not dest:
        # Extract filename from URL
        from pathlib import Path
        filename = url.split("/")[-1].split("?")[0] or "download"
        dest = str(Path.cwd() / filename)

    try:
        import httpx
        from pathlib import Path

        dest_path = Path(dest).expanduser().resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        headers = {"User-Agent": "Mozilla/5.0 (compatible; Persia-AI/0.1)"}

        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

        size_str = f"{downloaded:,} bytes"
        if downloaded > 1024**2:
            size_str = f"{downloaded/1024**2:.1f} MB"
        elif downloaded > 1024:
            size_str = f"{downloaded/1024:.1f} KB"

        return f"Downloaded {size_str} to: {dest_path}"

    except ImportError:
        return "Error: httpx not available"
    except Exception as e:
        return f"Error downloading: {e}"


async def _get_ip_info(params: Any, ctx: ToolContext) -> str:
    """Get public IP and geolocation info."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://ipinfo.io/json")
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
    except ImportError:
        return "Error: httpx not available"
    except Exception as e:
        return f"Error getting IP info: {e}"


def make_web_tools() -> list:
    """Create web access tools."""
    return [
        FunctionTool(
            name="fetch_url",
            description=(
                "Fetch and read the content of a URL (web page, API endpoint, etc.). "
                "HTML is automatically stripped to plain text. Supports JSON APIs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch (must start with http:// or https://)"},
                    "raw": {"type": "boolean", "description": "Return raw HTML instead of plain text", "default": False},
                    "max_chars": {"type": "integer", "description": "Maximum characters to return (default 8000)", "default": 8000},
                    "timeout": {"type": "integer", "description": "Request timeout in seconds (default 15)", "default": 15},
                },
                "required": ["url"],
            },
            func=_fetch_url,
        ),
        FunctionTool(
            name="web_search",
            description=(
                "Search the web using DuckDuckGo. Returns titles, URLs, and snippets. "
                "No API key required. Great for researching topics, finding documentation, "
                "checking current information."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results to return (1-10, default 5)", "default": 5},
                },
                "required": ["query"],
            },
            func=_web_search,
        ),
        FunctionTool(
            name="download_file",
            description="Download a file from a URL and save it to disk.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to download"},
                    "destination": {"type": "string", "description": "Local path to save the file (default: filename from URL in current dir)"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)", "default": 60},
                },
                "required": ["url"],
            },
            func=_download_file,
        ),
        FunctionTool(
            name="get_ip_info",
            description="Get the current public IP address and geolocation information.",
            parameters={"type": "object", "properties": {}, "required": []},
            func=_get_ip_info,
        ),
    ]
