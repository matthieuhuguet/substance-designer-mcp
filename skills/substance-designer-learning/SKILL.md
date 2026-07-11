---
name: substance-designer-learning
description: Create and extend Substance 3D Designer learning workflows from tutorials, playlists, screenshots, or user prompts. Use when Codex needs to analyze Designer-specific material creation content, extract node/pattern/mask/PBR lessons, verify the Substance Designer MCP connection, build or modify .sbs practice graphs, save learning packages, or document Designer node workflows. This is for Substance 3D Designer, not Substance Painter.
---

# Substance Designer Learning

## Core Rule

Treat Substance 3D Designer work as graph learning, not transcript summarization. Extract reusable node logic, then create or update a `.sbs` practice graph when the MCP is available.

Use this skill only for Designer. If the task is Painter texturing, export presets, texture baking, or mesh painting, use a Painter-specific workflow instead.

## Relearning Focus

Keep this skill under active relearning for:

- Designer node graph thinking: shape, mask, bevel, warp, blend, height, normal, AO, roughness, and base color.
- Tutorial conversion: turn videos, playlists, screenshots, and notes into reusable graph drills.
- MCP operation: verify the local Designer bridge, build or update `.sbs` packages, and save evidence.
- Practice management: document graph names, node counts, failed nodes, next drills, and source links.

## Workflow

1. Identify the source.
   - For YouTube links or playlists, fetch metadata, chapters, captions, and descriptions with `yt-dlp` or browsing.
   - Do not download videos unless explicitly requested.
   - Do not reproduce captions or transcripts verbatim. Summarize workflow, node ideas, and timestamps.

2. Split the content by Designer relevance.
   - Designer-native: graph, nodes, height, masks, tile/pattern, blend, bevel, warp, normal, AO, roughness, base color.
   - Cross-tool but transferable: handpaint color logic, engine preview, roughness from albedo, stylized material read.
   - Non-Designer: Painter, 3DCoat, Photoshop, engine-only sections.

3. Convert lessons into a graph plan.
   - Use the chain: `shape -> mask -> bevel -> warp -> blend -> height -> normal/AO -> roughness -> baseColor`.
   - Keep height readable before adding color.
   - Reuse masks across height, color, and roughness instead of building unrelated maps.

4. Verify the Designer MCP.
   - Search/load the `mcp__substance_designer` tools if needed.
   - Call `get_scene_info`.
   - If connection is refused, start Substance 3D Designer and wait for the MCP port.
   - Make MCP calls sequentially. Do not run Designer MCP operations in parallel.

5. Build or update practice graphs.
   - Prefer `create_batch_graph` for short drill graphs with known atomic nodes.
   - Prefer `apply_recipe` for broad base materials, then tune colors, normal intensity, and roughness.
   - For library nodes, call `get_library_nodes`, create a test instance, then call `get_node_info` before connecting ports.
   - Save the package with `save_package` and verify with `get_scene_info`.

6. Document the result.
   - Write a concise learning note with source links, graph names, what each graph teaches, and exact next drills.
   - Keep source claims separate from inferred Designer practice advice.

## Reference Files

- Read `references/designer-study-workflow.md` when analyzing tutorials or creating learning notes.
- Read `references/designer-mcp-windows.md` when installing, repairing, or verifying the local Substance Designer MCP setup.

## Validation

Before finishing, verify:

- The `.sbs` package is saved on disk.
- `get_scene_info` shows the expected graph names and node counts.
- New Markdown notes link to the source videos or playlist.
- Any failed MCP recipe/library nodes are reported explicitly.
