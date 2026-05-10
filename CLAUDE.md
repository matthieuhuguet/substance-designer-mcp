# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A two-component MCP (Model Context Protocol) integration that lets AI clients control Adobe Substance 3D Designer 15.x via natural language. An AI client sends JSON-RPC over stdio to the bridge server, which relays commands over TCP to a plugin running inside SD's Python interpreter.

## Development Commands

```bash
# Install bridge dependencies
cd server/
uv sync

# Run the bridge server (SD must already be running)
uv run python sd_mcp_bridge.py --port 9881

# Run connection test (requires SD running with plugin loaded)
cd tests/
python test_connection.py

# Run stdio MCP test (requires SD running)
cd server/
python ../tests/test_mcp_stdio.py
```

There is no build step — this is pure Python. No automated test runner is configured; tests in `tests/` require a live Substance Designer instance on `localhost:9881`.

## Architecture

```
AI Client (Claude / Cursor)
        │  stdio  (JSON-RPC / MCP protocol)
        ▼
server/sd_mcp_bridge.py      ← FastMCP server, Python 3.12+, uv-managed
        │  TCP localhost:9881  (length-prefix framing)
        ▼
plugin/__init__.py            ← SD plugin, Python 3.11 (SD's interpreter)
        │  sd.api
        ▼
Adobe Substance 3D Designer 15.x
```

### Bridge (`server/sd_mcp_bridge.py`)

- Exposes ~23 MCP tools via `FastMCP`. Each tool is an `async def` that calls `_async_send()`.
- `_async_send` → `asyncio.to_thread(_send)` → `_send_command_locked()` which opens a **fresh TCP socket per command**, sends a framed JSON command, receives a framed JSON response, and closes the socket.
- A `threading.Lock` is held only during the socket send/receive (not across retries) — this prevents a 360-second deadlock on timeout.
- Retries on connection errors only (up to 2 retries); timeouts are not retried.
- Wire protocol: `[4-byte big-endian length][UTF-8 JSON payload]`

### Plugin (`plugin/__init__.py`)

- Loaded by SD at startup from the `sduserplugins/` directory.
- Starts a TCP server on port 9881 in a daemon thread (`SDMCPServer`).
- All SD API calls are dispatched to Qt's main thread via a `Signal/Slot` queued connection (`_Invoker` / `MainThreadDispatcher`). This is mandatory — the SD API is not thread-safe.
- `CommandHandler` maps command type strings to handler methods.
- `_safe_connect()` validates port IDs before calling SD (wrong port ID = crash).
- `_set_node_params()` reads the actual SD property type via `getType().getId()` and coerces Python values accordingly — mixing SDValueInt into a float param crashes SD silently.

### Recipe System (`plugin/recipes.py`, `plugin/sd_documentation.py`)

- `RECIPE_REGISTRY`: dict of named material recipes (79 entries). Each recipe is a dict with `nodes` (node specs with `id_alias`, `definition_id`/`library_keyword`, `parameters`, `position`) and `connections` (alias → alias wiring).
- `HEIGHTMAP_RECIPES`: dict of callables that accept `detail_level`, `scale`, `disorder` and return a recipe dict.
- `build_material_graph` / `build_heightmap_graph` delegate to `create_batch_graph` after looking up the recipe.
- `sd_documentation.py` is a static knowledge base (no internet required) queried via the `list_documentation` tool.

## Critical SD 15.x Constraints

These are hard API limits — violating them hangs or crashes SD permanently (requiring restart):

- **ONE tool call at a time** — never issue parallel calls to any SD tool
- `SDUsage.sNew()` — hangs SD permanently; do not call it
- `graph.newNode(unknown_definition_id)` — hangs SD permanently; always validate against `graph.getNodeDefinitions()` first
- `arrange_nodes()` — destroys **all** connections; use `move_node()` instead
- Library node outputs are **never** `"unique_filter_output"` — always call `get_node_info` first to discover actual port IDs
- `directionalwarp` warp-map input port = `"inputintensity"` (NOT `"inputgradient"`)
- `SDValueInt2/3/4` applied to float-type parameters silently crashes SD — `_infer_type()` always returns float vectors for lists; use explicit `{"value": ..., "type": "int2"}` only when the SD property is confirmed as int2

## Key Conventions

**Node identification**: Atomic nodes (blend, levels, blur, etc.) all output from `"unique_filter_output"`. Library nodes (Cells, Perlin, clouds_2, etc.) have custom output names — always run `get_node_info` before connecting them.

**Value types**: Bare Python ints are treated as `"float"` by `_infer_type()` because most SD parameters are float. Pass `{"value": x, "type": "int"}` explicitly for integer enum parameters (e.g. `blendingmode`).

**Graph resolution**: When `graph_identifier=None`, the plugin uses the currently active graph in SD's UI. The bridge passes `None` when the parameter is omitted.

**Batch creation**: `create_batch_graph` is the core builder used internally by `build_material_graph` and `apply_recipe`. Node specs use `id_alias` as a reference key for wiring connections. Library nodes use `library_keyword` (auto-resolved to `pkg://` URL) or explicit `resource_url`.

**Port**: Both bridge and plugin default to `9881`. The old default `9880` (still appears in `tests/`) is incorrect — always use `9881`.

**Plugin install path** (Windows):
```
%USERPROFILE%\Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins\sd_mcp_plugin\
```
SD auto-loads all plugins from `sduserplugins/` on startup — no registration needed.
