# Changelog

All notable changes to the Substance Designer MCP Plugin are documented here.

---

## [1.0.0] — 2026-02-19 — First Public Release

### Plugin (v3.1.0)
- Complete MCP integration for Adobe Substance 3D Designer 15.x
- 16 MCP tools (11 core + 5 recipe/builder tools)
- Thread-safe Qt dispatch via Signal/Slot queued connection
- PySide6 path injection (SD ships its own PySide6, not in sys.path)
- Length-prefix TCP framing protocol (4-byte big-endian + JSON)
- Fresh-socket-per-command connection model (no stale state)

### Recipe System (v5.0 — 79 recipes)
- **Pro architecture family**: pro_granite, pro_limestone, pro_sandstone, pro_basalt, pro_slate, pro_steel, pro_iron, pro_copper, pro_concrete, pro_concrete_aged, pro_concrete_smooth (37–44 nodes each)
- **Core materials**: wood×5, rock×6, metal×7, organic×9, soil×5, water_ice×4, gems×5
- **Specialty**: concrete, brick, lava, asphalt, plaster, fabric, tile, specialty
- **Heightmap styles** (8): cliff, rock, sand, cracked, mud, mountain, cobblestone, terrain
- **MainShape** reconstruction (exact Javier Perez architecture, 11 nodes from live data)
- Javier Perez node chain: clouds_2 → slope_blur×2 → edge_detect → flood_fill → flood_fill_to_gradient_2 → multi_directional_warp×2 → directionalwarp×3 → highpass → histogram_scan
- All 79 recipes validated: 0 port failures, 0 crashes

### Bridge Server (v2.0.0)
- BUG-B01: `_send_lock` no longer held across retry loop — prevents 360-second deadlock
- BUG-B03: Default port corrected to 9881 (was 9880)
- BUG-B04: `directionalwarp` warp-map port corrected to `inputintensity` (was `inputgradient`)
- BUG-B05: FastMCP lifespan set at constructor, not post-construction
- BUG-B06: `ctx: Context` kept for FastMCP 1.4.1+ compatibility
- BUG-B07: `None` results return `"{}"` not `"null"`; NaN/Inf handled via `_json_safe`
- BUG-B08: Retry logic applies to connection failures only, not SD operation timeouts
- Async serialization via `threading.Lock` + `asyncio.to_thread`

### Critical Bug Fixes (SD 15.x)
- `SDValueInt2/3/4` on float params crashes SD silently → `_infer_type` always returns float2/3/4 for lists
- `SDValueFloat` on enum/int SD properties crashes SD silently → `_coerce_type()` reads actual SD type
- `_set_node_params` reads property type via `getType().getId()` and coerces accordingly
- `build_heightmap_graph`: builders return dict, not tuple — fixed unpacking
- `SDPackage.deleteResource()` does not exist — correct API is `resource.delete()`

### Confirmed SD 15.0.3 API Facts
- Library node outputs ≠ `"unique_filter_output"` (each has its own ID)
- `SDUsage.sNew()` hangs SD 15 permanently — removed
- `newNode(unknown_def)` hangs SD 15 permanently — validated before call
- `arrange_nodes()` destroys all connections — use `move_node()` instead
- `directionalwarp` warp-map input = `inputintensity` (NOT `inputgradient`)

---

## Internal Versions (not publicly released)

- **v3.1.0** (2026-02-18): SD crash fixes, build_heightmap bug fix, SD API notes
- **v3.0.0** (2026-02-15): Full recipe engine, smart builder, 34 initial materials
- **v2.x.x** (2026-02-10): PySide6 injection, Signal/Slot dispatcher
- **v1.x.x** (2026-02-01): Initial prototype
