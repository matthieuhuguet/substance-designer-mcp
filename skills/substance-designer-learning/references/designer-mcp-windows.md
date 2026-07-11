# Substance Designer MCP On Windows

Use this reference when the task involves installing, repairing, or verifying the local Substance 3D Designer MCP.

## Correct Target

Use Substance 3D Designer, not Substance Painter.

Expected MCP server name:

`substance_designer`

Common wrong server name to remove or avoid:

`substance_painter`

## Current Workstation Defaults

These paths were used successfully on this Windows workstation:

- Workspace: `G:\open AI codex\substance 3d`
- MCP repo: `https://github.com/matthieuhuguet/substance-designer-mcp.git`
- Server directory: `G:\open AI codex\substance 3d\server`
- Designer executable: `G:\SteamLibrary\steamapps\common\Substance 3D Designer 2026\Adobe Substance 3D Designer.exe`
- User plugin directory: `C:\Users\Administrator\Documents\Allegorithmic\Substance Designer\python\sduserplugins\sd_mcp_plugin`
- MCP TCP port: `9881`
- Verified Designer version: `16.0.4`
- Verified plugin version: `3.3.0`

## Codex MCP Config Shape

The Codex config entry should look like:

```toml
[mcp_servers.substance_designer]
command = 'C:\Users\Administrator\AppData\Roaming\Python\Python311\Scripts\uv.exe'
args = ['run', '--directory', 'G:\open AI codex\substance 3d\server', 'python', 'sd_mcp_bridge.py', '--port', '9881']
startup_timeout_sec = 120
```

## Verification Steps

1. Confirm Designer is running.

```powershell
Get-Process | Where-Object { $_.ProcessName -eq 'Adobe Substance 3D Designer' }
```

2. Confirm the MCP plugin is listening.

```powershell
Get-NetTCPConnection -LocalPort 9881 -ErrorAction SilentlyContinue
```

3. Confirm Codex can call the MCP.

Use `mcp__substance_designer.get_scene_info`.

Expected success includes:

- `sd_version`
- `plugin_version`
- `packages`
- `current_graph`

## Restart Recovery

If `get_scene_info` returns connection refused, start Designer and wait for the port:

```powershell
$exe = 'G:\SteamLibrary\steamapps\common\Substance 3D Designer 2026\Adobe Substance 3D Designer.exe'
Start-Process -FilePath $exe
```

Then poll port `9881` before retrying MCP calls.

## Loading An Existing SBS Package

If Designer starts with no packages loaded, use `execute_sd_code`:

```python
path = r"G:\open AI codex\substance 3d\SD_Playlist_Deep_Study.sbs"
pkg = pkg_mgr.loadUserPackage(path, True, True)
print("loaded", pkg.getFilePath())
```

Then call `get_scene_info`.

## Known Constraints

- Run Substance Designer MCP operations sequentially.
- Some library nodes may not be discoverable in a fresh Designer session; use atomic nodes or recipes when possible.
- For library nodes, do not guess port names. Create the node and call `get_node_info`.
- If recipe application reports failed library nodes, inspect the generated graph and report the failure count.
