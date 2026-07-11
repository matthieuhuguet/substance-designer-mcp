# Designer Study Workflow

Use this reference when turning a Substance 3D Designer tutorial, playlist, or timelapse into reusable learning output.

## Learning Order

Use this order for Designer playlists:

1. Fundamentals: graph flow, atomic nodes, PBR outputs.
2. Mask systems: edge masks, cavity masks, damage masks, directional masks, height range masks.
3. Material studies: wood, stone, brick, concrete, fabric, fantasy floors.
4. Polish: color variation, roughness lookdev, engine/material preview.

## Core Mental Model

Most Designer materials reduce to:

`large readable shape -> mask control -> edge treatment -> organic breakup -> micro surface -> PBR outputs`

Node-level shorthand:

`shape/pattern/tile -> levels/histogram -> bevel/blur -> warp/slope blur -> blend -> height -> normal/AO/roughness/baseColor`

Do not tune base color before the height map reads clearly.

## What To Extract From Tutorials

Extract these facts:

- Source title, channel, duration, and URL.
- Chapter or timestamp structure.
- Which parts are Designer-native.
- Which nodes or node families are repeated.
- What the author uses as the master map.
- Which masks are reused across height, roughness, and color.
- What can be practiced as a 10-node drill.

Avoid:

- Long transcript excerpts.
- Treating timelapse videos as precise step-by-step instructions.
- Mixing Painter/Photoshop operations into Designer node instructions without labeling them as transfer ideas.

## Drill Patterns

### Height To PBR

Purpose: teach that height is the master map.

Graph:

`source shape -> levels -> height`

Branch the height into:

- Normal node.
- Roughness Levels.
- BaseColor Blend opacity.
- AO or debug output if useful.

### Mask Reuse

Purpose: teach that a good mask should drive several material responses.

Graph:

`mask source -> levels -> shared mask`

Use the same mask for:

- Height detail.
- Normal generation.
- Base color blend opacity.
- Roughness contrast.
- Debug output.

### Histogram Roughness

Purpose: teach range extraction and roughness lookdev.

Graph:

`height -> high range mask`

`height -> low range mask`

Use high values for worn edges or highlights. Use low values for dirt, cavities, or rougher zones.

## Useful Designer Graph Names

Use descriptive graph names with underscores:

- `SD_Designer_Drill_01_Height_To_PBR`
- `SD_Designer_Drill_02_Mask_Reuse`
- `SD_Designer_Drill_03_Histogram_Roughness`
- `SD_Playlist_03_Designer_Fundamentals`
- `SD_Playlist_04_Masks_Cracks_Tips`

## Reporting

In the final answer, include:

- Saved `.sbs` path.
- Markdown note path.
- Graphs created or updated.
- MCP status and SD version if checked.
- Known limitations, such as unavailable library nodes or recipe failures.
