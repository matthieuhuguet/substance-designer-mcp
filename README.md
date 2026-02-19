# Substance Designer MCP

**The first MCP (Model Context Protocol) integration for Adobe Substance 3D Designer.**

Control Substance Designer from any MCP-compatible AI client (Claude Code, Claude Desktop, Cursor) — create graphs, build nodes, connect them, set parameters, generate full PBR material graphs from a single prompt.

---

## What it does

- **Natural language → SD graph**: "Create a cracked concrete material" → 44-node PBR graph with height, normal, roughness, AO, baseColor, metallic outputs
- **79 built-in material recipes**: pro-grade materials using the same node architecture as professional SD artists
- **16 MCP tools**: get scene info, create/delete graphs, create nodes, connect nodes, set parameters, build full materials in one call
- **Library node support**: Clouds, Cells, Perlin Noise, Polygon, Edge Detect, Flood Fill, Multi-Directional Warp, etc.
- **Thread-safe**: All SD API calls dispatched to Qt main thread via Signal/Slot queued connection

---

## Architecture

```
AI Client (Claude / Cursor)
        │  stdio (MCP protocol)
        ▼
sd_mcp_bridge.py  (FastMCP server, Python 3.12)
        │  TCP localhost:9881 (length-prefix framing)
        ▼
SD Plugin __init__.py  (Python 3.11, runs inside SD)
        │  sd.api
        ▼
Adobe Substance 3D Designer 15.x
```

The bridge and plugin communicate with a simple length-prefix framing protocol: `[4-byte big-endian length][JSON payload]`. Each command uses a fresh TCP socket — no persistent connection, no stale state.

---

## Requirements

- **Adobe Substance 3D Designer 15.x** (tested on 15.0.3)
- **Python 3.12+** for the bridge (managed via [uv](https://github.com/astral-sh/uv))
- **uv** package manager: `pip install uv` or `winget install astral-sh.uv`
- An MCP-compatible client: [Claude Code](https://claude.ai/code), [Claude Desktop](https://claude.ai/desktop), or [Cursor](https://cursor.sh)

---

## Installation

### Step 1 — Install the SD Plugin

Copy the `plugin/` folder contents to your SD user scripts directory:

**Windows:**
```
%USERPROFILE%\Documents\Adobe\Adobe Substance 3D Designer\python\sduserplugins\sd_mcp_plugin\
```

The directory must contain:
```
sd_mcp_plugin/
├── __init__.py    ← main plugin (TCP listener, all MCP tools)
└── recipes.py     ← 79 material recipes
```

SD auto-loads all plugins from `sduserplugins/` on startup. No additional configuration needed.

### Step 2 — Install the Bridge Server

```bash
cd server/
uv sync   # installs mcp[cli] into .venv
```

Or with pip:
```bash
pip install "mcp[cli]>=1.4.1"
```

### Step 3 — Configure Your MCP Client

**Claude Code** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "substance_designer": {
      "command": "C:\\Users\\YOUR_USERNAME\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--directory",
        "C:\\PATH\\TO\\substance-designer-mcp\\server",
        "python",
        "sd_mcp_bridge.py",
        "--port",
        "9881"
      ]
    }
  }
}
```

See `config/` folder for Claude Desktop and Cursor examples.

### Step 4 — Start SD before your AI client

**SD must be running before the MCP bridge starts.** The plugin binds TCP port 9881 on SD startup. If SD is not running when Claude/Cursor launches, the bridge will fail to connect.

---

## Usage

Once connected, you can ask your AI client to:

```
Build a weathered steel material with surface oxidation
```
```
Create a cliff heightmap with high detail and disorder
```
```
Make a new graph called MyRock, add a clouds node and a slope blur, connect them
```
```
List all available material recipes
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_scene_info` | List all open packages and graphs |
| `create_graph` | Create a new compositing graph |
| `get_graph_info` | Get all nodes and connections in a graph |
| `list_node_definitions` | Search available node types |
| `create_node` | Create an atomic node (blend, levels, blur, etc.) |
| `create_instance_node` | Create a library node (Clouds, Cells, Perlin, etc.) |
| `create_output_node` | Create a PBR output (baseColor, normal, height, etc.) |
| `connect_nodes` | Connect two nodes via their ports |
| `disconnect_nodes` | Remove a connection |
| `set_parameter` | Set a node parameter |
| `get_node_info` | Get ports and parameters of a node |
| `delete_node` | Delete a node |
| `move_node` | Reposition a node |
| `duplicate_node` | Duplicate an atomic node |
| `delete_graph` | Delete a graph from a package |
| `open_graph` | Open a graph in the SD editor |
| `save_package` | Save the package to disk |
| `execute_sd_code` | Execute arbitrary Python in SD's context |
| **`build_material_graph`** | **Build a full PBR material in one call** |
| **`build_heightmap_graph`** | **Build a heightmap-only graph in one call** |
| **`list_recipes`** | **List all 79 available material recipes** |
| **`get_recipe_info`** | **Get details about a specific recipe** |
| **`apply_recipe`** | **Apply a recipe to an existing graph** |

### Material Recipes

```python
build_material_graph(graph_name="MySteel", recipe_name="pro_steel")
# → 37-node PBR graph: height + normal + roughness + AO + baseColor + metallic

build_heightmap_graph(graph_name="CliffHM", style="cliff", detail_level=3, scale=5.0, disorder=0.5)
# → 9-node heightmap graph
```

**Pro recipes (37–44 nodes, Javier Perez architecture):**
`pro_granite`, `pro_limestone`, `pro_sandstone`, `pro_basalt`, `pro_slate`,
`pro_steel`, `pro_iron`, `pro_copper`,
`pro_concrete`, `pro_concrete_aged`, `pro_concrete_smooth`

**Core materials:**
`steel`, `iron`, `copper`, `gold`, `silver`, `aluminum`, `brass`,
`granite`, `marble`, `sandstone`, `limestone`, `slate`, `basalt`,
`wood`, `wood_oak`, `moss`, `bone`, `leather`, `fabric_cotton`, `fabric_silk`, `fabric_wool`, `fabric_denim`, `fabric_burlap`,
`sand`, `mud`, `gravel`, `clay`, `soil`,
`ice`, `snow`, `frost`, `water`,
`diamond`, `ruby`, `sapphire`, `emerald`, `amethyst`,
`concrete`, `brick`, `lava`, `asphalt`, `plaster`, `tile`, `painted_metal`, `carbon_fiber`, `terracotta`, `obsidian`, ...

**Heightmap styles:**
`cliff`, `rock`, `sand`, `cracked`, `mud`, `mountain`, `cobblestone`, `terrain`

---

## Critical Rules (SD 15.x)

These are hard constraints of the SD 15.x API — violating them hangs or crashes SD:

- **ONE tool call at a time** — never parallel calls to SD tools
- `SDUsage.sNew()` **hangs SD 15 permanently** — removed from plugin
- `newNode(unknown_definition)` **hangs SD 15 permanently** — plugin validates before calling
- `arrange_nodes()` **destroys all connections** — use `move_node()` instead
- Library node outputs are **never** `"unique_filter_output"` — always call `get_node_info` first
- `directionalwarp` warp-map port = `"inputintensity"` (NOT `inputgradient`)
- Wrong port ID in `connect_nodes` = crash — plugin validates before calling SD

---

## Known Library Node Ports (SD 15.0.3)

| Node | Output | Key Inputs |
|------|--------|-----------|
| `clouds_2` | `output` | `scale`, `disorder` |
| `cells_1` | `output` | `scale`, `disorder` |
| `perlin_noise` | `output` | `scale`, `disorder` |
| `polygon_2` | `output` | `Sides`, `Scale`, `Gradient` |
| `gradient_linear_1` | `Simple_Gradient` | `Tiling`, `rotation` |
| `gradient_axial` | `output` | `point_1`, `point_2` |
| `slope_blur_grayscale_2` | `Slope_Blur` | `Samples`, `Source`, `Effect` |
| `blur_hq_grayscale` | `Blur_HQ` | `Intensity`, `Source` |
| `non_uniform_blur_grayscale` | `Non_Uniform_Blur` | `Intensity`, `Anisotropy`, `Source` |
| `edge_detect` | `output` | `edge_width`, `tolerance`, `input` |
| `flood_fill` | `output` | `mask` |
| `flood_fill_to_gradient_2` | `output` | `angle`, `input`, `angle_input` |
| `flood_fill_to_grayscale` | `output` | `luminance_random`, `input` |
| `multi_directional_warp_grayscale` | `output` | `intensity`, `directions`, `input`, `intensity_input` |
| `highpass_grayscale` | `Highpass` | `Radius`, `Source` |
| `histogram_scan` | `Output` | `Position`, `Contrast`, `Input_1` |
| `invert_grayscale` | `Invert_Grayscale` | `Source` |
| `crystal_1` | `output` | `scale`, `disorder` |

---

## Troubleshooting

**Bridge can't connect to SD:**
- Make sure SD is running and fully loaded before launching your AI client
- Check SD logs: `%LOCALAPPDATA%\Adobe\Adobe Substance 3D Designer\log.txt` (look for `[SD-MCP]`)
- Verify the plugin is in the correct `sduserplugins` directory

**SD hangs after a command:**
- A bad node definition was likely used. Restart SD.
- The plugin validates node definitions before calling SD, but library nodes need correct `pkg://` URLs.

**Wrong port:**
- Plugin listens on **9881** by default. Bridge must use `--port 9881`.

**Plugin not loading:**
- Delete `__pycache__/` in the plugin directory and restart SD.

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Author

Built by **matth** — first MCP integration for Substance Designer.

Architecture insights derived from deep analysis of professional Substance Designer graphs (Javier Perez workflow: clouds_2 → slope_blur → edge_detect → flood_fill → multi_directional_warp → directionalwarp chains).

---

## Contributing

PRs welcome. Key areas for improvement:
- More material recipes
- Color graph support (currently height/grayscale focused)
- Windows + macOS path handling for plugin install
- Auto-install script for the SD plugin
