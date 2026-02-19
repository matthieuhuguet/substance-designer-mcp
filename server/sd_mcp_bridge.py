#!/usr/bin/env python
"""
sd_mcp_bridge.py - Substance Designer MCP Bridge v2.0.0

Relay between Claude (stdio/FastMCP) and the SD plugin (TCP).

Architecture: Claude -> stdio -> this bridge -> TCP localhost:<port> -> SD plugin

Protocol: Length-prefix framing [4-byte big-endian length][JSON payload]
Connection: Fresh TCP socket per command (no persistent connection)

Fixes in v2.0.0:
  BUG-B01: _send_lock no longer held across full retry loop (prevents 360s deadlock)
  BUG-B03: Default port corrected to 9881 (was 9880)
  BUG-B04: directionalwarp warp input corrected to "inputintensity" (was "inputgradient")
  BUG-B05: FastMCP lifespan set at constructor, not post-construction attribute
  BUG-B06: ctx: Context kept for FastMCP compatibility (injection works in 1.4.1+)
  BUG-B07: None result returns "{}" not "null"; float nan/inf handled via SD plugin _json_safe
  BUG-B08: Retry logic documented correctly (retries connection errors only, not timeouts)

Usage:
    uv run --directory E:/Create/Build/DCC/MCP/SubstanceDesignerMCP/server \\
           python sd_mcp_bridge.py --port 9881
"""
import sys
import os
import json
import struct
import socket
import logging
import argparse
import asyncio
import time
import threading
from typing import Any, List, Optional
from contextlib import asynccontextmanager

# Ensure venv site-packages on path
script_dir = os.path.dirname(os.path.abspath(__file__))
venv_site = os.path.join(script_dir, '.venv', 'Lib', 'site-packages')
if os.path.exists(venv_site):
    sys.path.insert(0, venv_site)

from mcp.server.fastmcp import FastMCP, Context

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SD_MCP_Bridge")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TIMEOUT = 120          # SD can be slow on heavy operations
CONNECT_TIMEOUT = 5    # timeout for initial TCP connection
HEADER_SIZE = 4
MAX_RETRIES = 2        # only for connection failures, not SD operation timeouts
RETRY_DELAY = 1.0      # seconds between retry attempts

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_sd_port: int = 9881   # BUG-B03 fix: default matches SD plugin DEFAULT_PORTS
# BUG-B01 fix: lock is NOT held across the retry loop — only during the actual
# socket operation. This prevents a single timeout from blocking the bridge for
# 3 x 120 = 360 seconds. Each _send_command call acquires its own lock window.
_send_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Length-prefix protocol
# ---------------------------------------------------------------------------
def _send_framed(sock: socket.socket, data: bytes) -> None:
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes. Returns b"" on clean disconnect."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return b""
        buf += chunk
    return buf


def _recv_framed(sock: socket.socket, timeout: float) -> bytes:
    sock.settimeout(timeout)
    header = _recv_exact(sock, HEADER_SIZE)
    if not header:
        raise ConnectionAbortedError("Connection closed while reading header.")
    msg_len = struct.unpack(">I", header)[0]
    if msg_len == 0:
        return b""
    if msg_len > 100 * 1024 * 1024:
        raise ValueError(f"Message too large: {msg_len} bytes")
    payload = _recv_exact(sock, msg_len)
    if not payload:
        raise ConnectionAbortedError("Connection closed while reading payload.")
    return payload


# ---------------------------------------------------------------------------
# Send command — BUG-B01 fix: lock held only for the socket operation
# ---------------------------------------------------------------------------
def _send_command_locked(cmd_type: str, params: dict = None) -> dict:
    """
    Open fresh TCP connection, send one command, receive one response.
    Lock is acquired INSIDE this function for the duration of the socket op.
    This prevents a single timeout from holding the lock for 120+ seconds.
    """
    command = {"type": cmd_type, "params": params or {}}
    data_out = json.dumps(command).encode("utf-8")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(CONNECT_TIMEOUT)
    try:
        sock.connect(("localhost", _sd_port))
    except Exception as e:
        sock.close()
        raise ConnectionError(
            f"Cannot connect to Substance Designer on localhost:{_sd_port}. "
            f"Is SD running with the MCP plugin loaded? ({e})")

    # Acquire lock AFTER connection is established — only for the send/recv cycle
    with _send_lock:
        try:
            _send_framed(sock, data_out)
            response_bytes = _recv_framed(sock, TIMEOUT)
            if not response_bytes:
                return {"status": "error", "message": f"Empty response from SD on '{cmd_type}'."}
            return json.loads(response_bytes.decode("utf-8"))
        except socket.timeout:
            return {"status": "error",
                    "message": f"Timeout ({TIMEOUT}s) waiting for SD on '{cmd_type}'. "
                               f"SD may be busy — try again."}
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON from SD: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Communication error: {e}"}
        finally:
            try:
                sock.close()
            except Exception:
                pass


def _send(cmd_type: str, params: dict = None) -> str:
    """
    Send with retry for connection errors only.
    BUG-B01 fix: retry loop is OUTSIDE the lock (lock is inside _send_command_locked).
    BUG-B08 clarification: timeouts do NOT retry (would just re-queue a stuck SD op).
    Returns formatted result string for MCP tool response.
    """
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = _send_command_locked(cmd_type, params)
            if response.get("status") == "error":
                msg = response.get("message", "Unknown error")
                # Only retry on connection errors (SD not yet started, transient)
                is_connect_err = "Cannot connect" in msg or "connect" in msg.lower()
                if is_connect_err and attempt < MAX_RETRIES:
                    last_error = msg
                    logger.warning(f"Attempt {attempt+1} failed (connect): {msg}. Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    continue
                # Non-retryable errors (timeout, SD errors, validation) — return immediately
                return f"Error: {msg}"
            result = response.get("result")
            # BUG-B07 fix: None result returns "{}" not "null"
            if result is None:
                result = {}
            return json.dumps(result, indent=2)
        except ConnectionError as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                logger.warning(f"Attempt {attempt+1} failed (connection): {e}. Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            return f"Connection Error: {e}"
        except Exception as e:
            logger.error(f"Unexpected error in {cmd_type}: {e}", exc_info=True)
            return f"Error: {e}"
    return f"Error: All {MAX_RETRIES+1} attempts failed. Last: {last_error}"


async def _async_send(cmd_type: str, params: dict = None) -> str:
    return await asyncio.to_thread(_send, cmd_type, params)


# ---------------------------------------------------------------------------
# FastMCP Server — BUG-B05 fix: lifespan passed at constructor
# ---------------------------------------------------------------------------
@asynccontextmanager
async def _lifespan(app: FastMCP):
    logger.info(f"Substance Designer MCP Bridge v2.0.0 -> SD plugin on port {_sd_port}")
    logger.info("Ensure Substance Designer is running with the MCP plugin loaded.")
    yield {}
    logger.info("Substance Designer MCP bridge shutting down.")


# BUG-B05 fix: pass lifespan at construction (not post-construction attribute)
mcp = FastMCP("SubstanceDesignerMCP", lifespan=_lifespan)


# ======================================================================
# MCP TOOLS
# BUG-B06 note: ctx: Context kept — FastMCP 1.4.1+ injects it correctly.
# If a future version drops injection, remove ctx parameter from all tools.
# ======================================================================

@mcp.tool()
async def get_scene_info(ctx: Context) -> str:
    """
    Get info about loaded packages and graphs in Substance Designer.
    Returns packages, graphs, node counts, current graph, and SD version.
    """
    return await _async_send("get_scene_info")


@mcp.tool()
async def create_package(ctx: Context) -> str:
    """
    Create a new empty package in Substance Designer.
    Use save_package to save it to disk afterward.
    """
    return await _async_send("create_package")


@mcp.tool()
async def create_graph(ctx: Context,
                       package_index: int = 0,
                       graph_name: str = "MCP_Graph",
                       package_path: Optional[str] = None) -> str:
    """
    Create a new SBS Compositing Graph in Substance Designer.
    - package_index: which loaded package (0 = first/current)
    - graph_name: identifier for the new graph
    - package_path: optional full path to specific .sbs file

    IMPORTANT: graph_name should use only letters, digits, underscores.
    Spaces and special characters are automatically sanitized.
    """
    return await _async_send("create_graph", {
        "package_index": package_index,
        "graph_name": graph_name,
        "package_path": package_path,
    })


@mcp.tool()
async def delete_graph(ctx: Context,
                       graph_identifier: str,
                       package_index: int = 0) -> str:
    """Delete a graph from a package."""
    return await _async_send("delete_graph", {
        "graph_identifier": graph_identifier,
        "package_index": package_index,
    })


@mcp.tool()
async def open_graph(ctx: Context, graph_identifier: str) -> str:
    """Open a graph in the Substance Designer UI editor."""
    return await _async_send("open_graph", {"graph_identifier": graph_identifier})


@mcp.tool()
async def get_graph_info(ctx: Context,
                         graph_identifier: Optional[str] = None,
                         node_limit: int = 100,
                         include_connections: bool = True) -> str:
    """
    Get detailed info about a graph including all nodes and connections.
    - graph_identifier: graph identifier (None = current active graph)
    - node_limit: max nodes to return in detail (default 100; use 0 for summary/count only)
    - include_connections: whether to include connection data per node (default True)

    For large graphs (100+ nodes), use node_limit=0 to get just the count,
    then query specific nodes with get_node_info.
    """
    return await _async_send("get_graph_info", {
        "graph_identifier": graph_identifier,
        "node_limit": node_limit,
        "include_connections": include_connections,
    })


@mcp.tool()
async def list_node_definitions(ctx: Context,
                                filter_text: str = "",
                                graph_identifier: Optional[str] = None,
                                limit: int = 500) -> str:
    """
    List available node definitions in Substance Designer.
    - filter_text: search filter (e.g. 'blur', 'cells', 'perlin', 'blend')
    - graph_identifier: optional graph to query from
    - limit: max results (default 500)

    Common sbs::compositing:: definitions:
      uniform, blend, levels, normal, curve, hsl, gradient, blur, sharpen,
      warp, directionalwarp, emboss, transformation, distance, grayscaleconversion,
      shuffle, pixelprocessor, fxmaps, bitmap, output, input_color, input_grayscale
    """
    return await _async_send("list_node_definitions", {
        "filter_text": filter_text,
        "graph_identifier": graph_identifier,
        "limit": limit,
    })


@mcp.tool()
async def create_node(ctx: Context,
                      definition_id: str,
                      graph_identifier: Optional[str] = None,
                      position: Optional[List[float]] = None) -> str:
    """
    Create an atomic node in a Substance Designer graph.
    - definition_id: e.g. 'sbs::compositing::blend', 'sbs::compositing::levels'
    - graph_identifier: target graph (None = current active graph)
    - position: [x, y] position in graph editor

    Common definition_ids:
      sbs::compositing::uniform        - Solid color/grayscale
      sbs::compositing::blend          - Blend two inputs (modes: Copy=0, Add=1, Subtract=2, Multiply=3, etc.)
      sbs::compositing::levels         - Levels adjustment
      sbs::compositing::normal         - Height to Normal map
      sbs::compositing::curve          - Curve adjustment
      sbs::compositing::hsl            - Hue/Saturation/Luminosity
      sbs::compositing::blur           - Gaussian blur
      sbs::compositing::sharpen        - Sharpen
      sbs::compositing::warp           - Warp/distortion
      sbs::compositing::directionalwarp - Directional warp
      sbs::compositing::emboss         - Emboss
      sbs::compositing::transformation - 2D transform
      sbs::compositing::distance       - Distance field
      sbs::compositing::grayscaleconversion - RGB to grayscale
      sbs::compositing::shuffle        - Channel shuffle
      sbs::compositing::bitmap         - Bitmap input
      sbs::compositing::fxmaps         - FX-Map (pattern generator)
      sbs::compositing::pixelprocessor - Per-pixel math
      sbs::compositing::passthrough    - Pass-through
      sbs::compositing::input_color    - Color input parameter
      sbs::compositing::input_grayscale - Grayscale input parameter

    Returns node_id which is used in connect_nodes, set_parameter, etc.
    """
    return await _async_send("create_node", {
        "definition_id": definition_id,
        "graph_identifier": graph_identifier,
        "position": position,
    })


@mcp.tool()
async def create_instance_node(ctx: Context,
                               resource_url: str,
                               graph_identifier: Optional[str] = None,
                               position: Optional[List[float]] = None) -> str:
    """
    Create an instance of a library node (Cells, Perlin Noise, etc.).
    First use get_library_nodes to find the resource_url.
    - resource_url: URL like 'pkg:///cells_1?dependency=1563150890'
    - graph_identifier: target graph (None = current)
    - position: [x, y]

    IMPORTANT: After creating, call get_node_info(node_id) to find the exact
    output/input port IDs before connecting. Library nodes do NOT use
    'unique_filter_output' — they have custom output names.
    """
    return await _async_send("create_instance_node", {
        "resource_url": resource_url,
        "graph_identifier": graph_identifier,
        "position": position,
    })


@mcp.tool()
async def create_output_node(ctx: Context,
                             usage: str = "baseColor",
                             label: Optional[str] = None,
                             graph_identifier: Optional[str] = None,
                             position: Optional[List[float]] = None) -> str:
    """
    Create an output node with a specific PBR usage in Substance Designer.
    - usage: baseColor, normal, height, roughness, metallic, ambientOcclusion, emissive, opacity
    - label: display label (defaults to usage name)
    - graph_identifier: target graph (None = current)
    - position: [x, y]
    """
    return await _async_send("create_output_node", {
        "usage": usage,
        "label": label,
        "graph_identifier": graph_identifier,
        "position": position,
    })


@mcp.tool()
async def connect_nodes(ctx: Context,
                        from_node_id: str,
                        to_node_id: str,
                        from_output: str = "unique_filter_output",
                        to_input: str = "input1",
                        graph_identifier: Optional[str] = None) -> str:
    """
    Connect two nodes in a Substance Designer graph.
    - from_node_id: source node identifier (from create_node result)
    - to_node_id: destination node identifier
    - from_output: output slot on source (always 'unique_filter_output' for atomic nodes)
    - to_input: input slot - CRITICAL, must match target node type exactly:

    NODE TYPE              to_input
    blur               ->  "input1"
    levels             ->  "input1"
    normal             ->  "input1"
    curve              ->  "input1"
    hsl                ->  "input1"
    sharpen            ->  "input1"
    grayscaleconversion->  "input1"
    transformation     ->  "input1"
    emboss             ->  "input1"
    warp               ->  "input1" (image), "inputgradient" (warp map)
    directionalwarp    ->  "input1" (image), "inputintensity" (warp map — NOT inputgradient!)
    distance           ->  "input1"
    blend              ->  "source" (fg), "destination" (bg), "opacity" (mask)
    output             ->  "inputNodeOutput"

    For library nodes (Cells, Perlin, Polygon, etc.): ALWAYS run get_node_info
    first to discover exact input/output IDs. Never guess.

    - graph_identifier: target graph (None = current)
    """
    return await _async_send("connect_nodes", {
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "from_output": from_output,
        "to_input": to_input,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def disconnect_nodes(ctx: Context,
                           node_id: str,
                           input_id: str,
                           graph_identifier: Optional[str] = None) -> str:
    """
    Disconnect all connections to a specific input of a node.
    - node_id: target node
    - input_id: input property to disconnect (e.g. 'input1', 'source')
    - graph_identifier: target graph (None = current)
    """
    return await _async_send("disconnect_nodes", {
        "node_id": node_id,
        "input_id": input_id,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def set_parameter(ctx: Context,
                        node_id: str,
                        parameter_id: str,
                        value: Any,
                        value_type: str = "float",
                        graph_identifier: Optional[str] = None) -> str:
    """
    Set a parameter on a node in Substance Designer.
    - node_id: target node identifier
    - parameter_id: parameter name

    Common parameter IDs:
      '$outputsize'  - Resolution as int2, e.g. [11,11] for 2048x2048
      'intensity'    - Blur/sharpen/normal intensity (float)
      'blendingmode' - Blend mode (int): 0=Copy, 1=Add, 2=Subtract, 3=Multiply, 9=Overlay
      'opacitymult'  - Blend opacity multiplier (float 0-1)
      'outputcolor'  - Uniform color output (color [r,g,b,a])
      'levelinlow'   - Levels input low (float4)
      'levelinhigh'  - Levels input high (float4)
      'leveloutlow'  - Levels output low (float4)
      'levelouthigh' - Levels output high (float4)
      'hue'          - HSL hue shift (float 0-1, 0.5=no shift)
      'saturation'   - HSL saturation (float 0-1, 0.5=no change)
      'luminosity'   - HSL luminosity (float 0-1, 0.5=no change)
      'matrix22'     - Transformation matrix (float4)
      'offset'       - Transformation offset (float2)
      'channelsweights' - Grayscale channel weights (float4)

    - value: the value to set
    - value_type: 'float', 'int', 'bool', 'string', 'float2', 'float3', 'float4',
                  'color' (RGBA 0-1), 'int2', 'int3', 'int4'
    - graph_identifier: target graph (None = current)
    """
    return await _async_send("set_parameter", {
        "node_id": node_id,
        "parameter_id": parameter_id,
        "value": value,
        "value_type": value_type,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def get_node_info(ctx: Context,
                        node_id: str,
                        graph_identifier: Optional[str] = None) -> str:
    """
    Get detailed info about a node (properties, connections, position).
    - node_id: node identifier
    - graph_identifier: target graph (None = current)

    IMPORTANT: Call this for ANY library node before connecting it.
    The response includes exact input/output port IDs and whether it's a library node.
    """
    return await _async_send("get_node_info", {
        "node_id": node_id,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def delete_node(ctx: Context,
                      node_id: str,
                      graph_identifier: Optional[str] = None) -> str:
    """
    Delete a node from a Substance Designer graph.
    - node_id: node identifier to delete
    - graph_identifier: target graph (None = current)
    """
    return await _async_send("delete_node", {
        "node_id": node_id,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def move_node(ctx: Context,
                    node_id: str,
                    position: List[float],
                    graph_identifier: Optional[str] = None) -> str:
    """
    Move a node to a new position in the graph.
    - node_id: node to move
    - position: [x, y] new position
    - graph_identifier: target graph (None = current)

    PREFER move_node over arrange_nodes — arrange_nodes DESTROYS all connections in SD 15.
    """
    return await _async_send("move_node", {
        "node_id": node_id,
        "position": position,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def duplicate_node(ctx: Context,
                         node_id: str,
                         offset: Optional[List[float]] = None,
                         graph_identifier: Optional[str] = None) -> str:
    """
    Duplicate an ATOMIC node (creates a new node of the same type).
    - node_id: node to duplicate (must be atomic, not a library instance node)
    - offset: [dx, dy] position offset from original (default [100, 0])
    - graph_identifier: target graph (None = current)

    WARNING: Library nodes (Cells, Perlin, Polygon, etc.) CANNOT be duplicated
    via this method. Use create_instance_node with the same resource_url instead.
    """
    return await _async_send("duplicate_node", {
        "node_id": node_id,
        "offset": offset,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def set_graph_output_size(ctx: Context,
                                width_log2: int = 11,
                                height_log2: int = 11,
                                graph_identifier: Optional[str] = None) -> str:
    """
    Set the output resolution of a graph.
    - width_log2: log2 of width (9=512, 10=1024, 11=2048, 12=4096)
    - height_log2: log2 of height
    - graph_identifier: target graph (None = current)
    """
    return await _async_send("set_graph_output_size", {
        "width_log2": width_log2,
        "height_log2": height_log2,
        "graph_identifier": graph_identifier,
    })


@mcp.tool()
async def save_package(ctx: Context,
                       package_index: int = 0,
                       file_path: Optional[str] = None,
                       package_path: Optional[str] = None) -> str:
    """
    Save a package to disk.
    - package_index: which user package (0 = first)
    - file_path: if given, Save As to this path (.sbs) — directories created automatically
    - package_path: identify package by existing file path
    """
    return await _async_send("save_package", {
        "package_index": package_index,
        "file_path": file_path,
        "package_path": package_path,
    })


@mcp.tool()
async def get_library_nodes(ctx: Context,
                            filter_text: str = "",
                            limit: int = 200) -> str:
    """
    Get available library nodes from Substance Designer's built-in packages.
    Returns resource URLs for use with create_instance_node.
    - filter_text: search filter (e.g. 'cell', 'perlin', 'noise', 'grunge', 'polygon')
    - limit: max results

    After getting a URL, use create_instance_node(resource_url=url) to add it,
    then get_node_info(node_id) to discover its port IDs before connecting.
    """
    return await _async_send("get_library_nodes", {
        "filter_text": filter_text,
        "limit": limit,
    })


@mcp.tool()
async def arrange_nodes(ctx: Context,
                        graph_identifier: Optional[str] = None,
                        start_x: float = -1000,
                        start_y: float = 0,
                        node_spacing_x: float = 200,
                        node_spacing_y: float = 150) -> str:
    """
    Auto-arrange all nodes in a graph in a grid layout.
    - graph_identifier: target graph (None = current)
    - start_x, start_y: starting position
    - node_spacing_x, node_spacing_y: spacing between nodes

    WARNING: In SD 15, arrange_nodes DESTROYS all node connections.
    Use move_node() instead to reposition nodes without losing connections.
    Only use this tool when you don't mind reconnecting all nodes manually.
    """
    return await _async_send("arrange_nodes", {
        "graph_identifier": graph_identifier,
        "start_x": start_x,
        "start_y": start_y,
        "node_spacing_x": node_spacing_x,
        "node_spacing_y": node_spacing_y,
    })


@mcp.tool()
async def execute_sd_code(ctx: Context, code: str) -> str:
    """
    Execute arbitrary Python code in Substance Designer's main thread (safe).
    Variables available: sd, app, pkg_mgr, ui_mgr, open_in_editor
    Returns stdout, stderr, and any error.

    WARNING: No timeout protection. Blocking code will hang SD indefinitely.
    Keep code short, simple, and non-blocking.
    """
    return await _async_send("execute_code", {"code": code})


@mcp.tool()
async def create_batch_graph(ctx: Context,
                             graph_name: str,
                             package_index: int = 0,
                             nodes: Optional[List[dict]] = None,
                             connections: Optional[List[dict]] = None,
                             output_size_log2: int = 11,
                             open_in_editor: bool = True,
                             package_path: Optional[str] = None) -> str:
    """
    Create a complete graph from a descriptor in ONE call. Most efficient for complex graphs.

    nodes: list of node descriptors:
      {
        "id_alias": "my_blur",           # reference name for connections
        "definition_id": "sbs::compositing::blur",
        "position": [0, 0],              # optional
        "usage": "height",               # for output nodes only
        "label": "Height Output",        # for output nodes
        "resource_url": "pkg:///...",    # for library nodes (use get_library_nodes first)
        "parameters": {                  # optional parameter overrides
          "intensity": 10.0,             # shorthand (auto-detects float)
          "$outputsize": {"value": [11,11], "type": "int2"}  # explicit type
        }
      }

    connections: list of connection descriptors:
      {
        "from": "my_blur",                  # from node alias
        "to": "height_output",              # to node alias
        "from_output": "unique_filter_output",  # optional (default for atomic nodes)
        "to_input": "inputNodeOutput"       # required for output nodes
      }

    IMPORTANT for library nodes in batch:
      - Use "resource_url" (not "definition_id") for library nodes
      - You MUST know the output port IDs in advance
        (run create_instance_node + get_node_info first in test mode)
      - Batch does NOT validate library node port IDs automatically

    Returns: node_map {alias -> actual_node_id} + creation stats
    """
    return await _async_send("create_batch_graph", {
        "graph_name": graph_name,
        "package_index": package_index,
        "nodes": nodes or [],
        "connections": connections or [],
        "output_size_log2": output_size_log2,
        "open_in_editor": open_in_editor,
        "package_path": package_path,
    })


# ---------------------------------------------------------------------------
# Recipe tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_recipes(ctx: Context) -> str:
    """
    List all built-in material recipes available in the SD MCP plugin.
    Returns material recipes (metals, rocks, organic, soils, water/ice, gems)
    and heightmap styles (cliff, rock, sand, cracked, mountain, cobblestone).
    """
    return await _async_send("list_recipes", {})


@mcp.tool()
async def get_recipe_info(ctx: Context, recipe_name: str) -> str:
    """
    Get detailed info about a specific material recipe.
    recipe_name: e.g. 'steel', 'marble', 'gold', 'wood_oak', 'ice', 'diamond'
    """
    return await _async_send("get_recipe_info", {"recipe_name": recipe_name})


@mcp.tool()
async def build_material_graph(ctx: Context,
                                graph_name: str,
                                recipe_name: str,
                                package_index: int = 0,
                                overrides: Optional[dict] = None,
                                output_size_log2: int = 11,
                                open_in_editor: bool = True,
                                package_path: Optional[str] = None) -> str:
    """
    Build a complete PBR material graph from a named recipe in ONE call.

    Available recipes: steel, iron, copper, gold, silver, aluminum,
    granite, marble, sandstone, limestone, slate,
    wood, wood_oak, oak, moss, bone,
    sand, mud, gravel, clay,
    ice, snow, frost, water,
    diamond, ruby, sapphire, emerald, amethyst.

    Each recipe generates: Height + Normal + Roughness + AO + BaseColor + Metallic outputs.

    overrides: optional dict to override node parameters, keyed by node alias.
    output_size_log2: 10=1024, 11=2048, 12=4096
    """
    return await _async_send("build_material_graph", {
        "graph_name": graph_name,
        "recipe_name": recipe_name,
        "package_index": package_index,
        "overrides": overrides,
        "output_size_log2": output_size_log2,
        "open_in_editor": open_in_editor,
        "package_path": package_path,
    })


@mcp.tool()
async def build_heightmap_graph(ctx: Context,
                                 graph_name: str,
                                 style: str,
                                 package_index: int = 0,
                                 output_size_log2: int = 11,
                                 open_in_editor: bool = True,
                                 detail_level: int = 2,
                                 scale: float = 5.0,
                                 disorder: float = 0.5,
                                 package_path: Optional[str] = None) -> str:
    """
    Build a heightmap-only graph for terrain/rock/cliff.

    Available styles: cliff, rock, sand, cracked, mud, mountain, cobblestone, terrain.

    detail_level: 1=basic, 2=standard, 3=high detail
    scale: overall scale factor (1.0 to 10.0)
    disorder: amount of irregularity/warping (0.0 to 1.0)
    """
    return await _async_send("build_heightmap_graph", {
        "graph_name": graph_name,
        "style": style,
        "package_index": package_index,
        "output_size_log2": output_size_log2,
        "open_in_editor": open_in_editor,
        "detail_level": detail_level,
        "scale": scale,
        "disorder": disorder,
        "package_path": package_path,
    })


@mcp.tool()
async def apply_recipe(ctx: Context,
                        recipe_name: str,
                        graph_identifier: Optional[str] = None,
                        position_offset: Optional[List[float]] = None,
                        overrides: Optional[dict] = None) -> str:
    """
    Apply a recipe to an EXISTING graph (adds nodes + connections to current graph).
    Useful for layering multiple materials or adding detail passes.

    recipe_name: any key from list_recipes
    graph_identifier: target graph (None = current active graph)
    position_offset: [x, y] to offset all node positions (avoid overlapping with existing nodes)
    overrides: dict of node parameter overrides keyed by node alias
    """
    return await _async_send("apply_recipe", {
        "recipe_name": recipe_name,
        "graph_identifier": graph_identifier,
        "position_offset": position_offset,
        "overrides": overrides,
    })


@mcp.tool()
async def list_documentation(ctx: Context,
                              category: str = "all",
                              filter_text: str = "",
                              node_name: str = "",
                              action: str = "",
                              query: str = "") -> str:
    """
    Browse the SD MCP embedded documentation knowledge base.
    No internet required — all knowledge is built into the plugin.

    Available categories:
      all                — everything (large response, use filter_text)
      atomic_nodes       — built-in nodes: blend, levels, blur, normal, warp, etc.
      library_nodes      — library nodes: cells, perlin, flood_fill, histogram_scan, etc.
      blend_modes        — all blend mode integers and descriptions
      port_reference     — input/output port names for every node type
      pbr_outputs        — PBR output usage tags and conventions
      workflow           — step-by-step usage rules and best practices
      concepts           — SD concepts: recipes, pro recipes, graph structure
      shortcuts          — SD keyboard shortcuts
      connection_patterns — common node chains (e.g. height→normal→AO)
      node_categories    — node families and groupings
      parameters         — parameter reference for common nodes

    Special actions:
      action="categories"         → list all available categories
      action="search", query="X"  → search all docs for keyword X

    Examples:
      list_documentation(category="atomic_nodes", node_name="blend")
      list_documentation(category="port_reference")
      list_documentation(action="search", query="directionalwarp")
      list_documentation(category="workflow")
      list_documentation(category="pbr_outputs")
    """
    return await _async_send("list_documentation", {
        "category": category,
        "filter_text": filter_text,
        "node_name": node_name,
        "action": action,
        "query": query,
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global _sd_port

    parser = argparse.ArgumentParser(description="Substance Designer MCP Bridge v2.0.0")
    parser.add_argument("--port", type=int, default=9881,  # BUG-B03 fix: default is 9881
                        help="TCP port to connect to the SD plugin (default: 9881)")
    args = parser.parse_args()
    _sd_port = args.port

    logger.info(f"SD MCP Bridge v2.0.0 -> SD plugin on port {_sd_port}")
    mcp.run()


if __name__ == "__main__":
    main()
