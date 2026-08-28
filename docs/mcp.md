# MCP server

The platform's research tools are exposed over the
[Model Context Protocol](https://modelcontextprotocol.io), so any
MCP-compatible AI client (Claude Desktop, Claude Code, and others) can use
them directly. The design doc (§11) specified this as a demonstration of a
portable tool interface: the same functions that power the pipeline, usable
by any agent.

## Tools

| Tool | What it does | Needs |
|---|---|---|
| `search_web` | Ranked public search results with URLs and snippets | `SEARCH_API_KEY` |
| `crawl_page_text` | Cleaned page text + retrieval metadata; optional headless-browser rendering for JS pages | — |
| `extract_pricing` | Structured tiers/prices/billing from an official pricing page; refuses to guess; rendered fallback | `ANTHROPIC_API_KEY` |
| `profile_product` | Structured product profile grounded in the product's own site (~30s, a few cents) | both keys |
| `discover_competitors` | Up to 5 competitors, three discovery strategies + website verification (~1-2 min, ~10 cents) | both keys |

## Run it

```bash
cd backend && uv run python mcp_server.py   # stdio transport
```

Keys come from `backend/.env` (see `.env.example`).

## Connect a client

**Claude Code** — this repo ships `.mcp.json`, so opening the repo in Claude
Code offers the server automatically. Or register it manually:

```bash
claude mcp add competitive-intelligence -- uv run --project /path/to/repo/backend python /path/to/repo/backend/mcp_server.py
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "competitive-intelligence": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/repo/backend",
               "python", "/path/to/repo/backend/mcp_server.py"]
    }
  }
}
```

Then ask the client something like *"use the competitive-intelligence tools
to find competitors for posthog.com and pull Amplitude's pricing"* and watch
it drive the platform's toolchain.
