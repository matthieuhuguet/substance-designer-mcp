"""
SD MCP Documentation Knowledge Base v1.0
==========================================
Complete embedded reference for Substance 3D Designer nodes, parameters,
ports, concepts and workflow — accessible via the `list_documentation` MCP tool.

This file is a STATIC knowledge base. It does NOT require internet access.
All data sourced from:
  - Adobe Substance 3D Designer official documentation
  - Live SD 15.0.3 API introspection (confirmed port names)
  - pro SubstanceGraph1 analysis (512 nodes, real-world patterns)
  - SD MCP plugin empirical testing

Usage via MCP:
  list_documentation(category="atomic_nodes")
  list_documentation(category="library_nodes", filter="blur")
  list_documentation(category="parameters")
  list_documentation(category="workflow")
  list_documentation(category="concepts")
  list_documentation(category="blend_modes")
  list_documentation(category="port_reference")
  list_documentation(category="shortcuts")
  list_documentation(category="connection_patterns")
  list_documentation(category="pbr_outputs")
  list_documentation(category="all")
"""

# ════════════════════════════════════════════════════════════════════════════
# CATEGORIES INDEX
# ════════════════════════════════════════════════════════════════════════════

CATEGORIES = {
    "atomic_nodes":        "All atomic/built-in compositing nodes with ports & parameters",
    "library_nodes":       "Library generator and filter nodes (noise, patterns, filters)",
    "parameters":          "Common node parameter IDs, types and value ranges",
    "workflow":            "Recommended workflows, step order, and SD MCP rules",
    "concepts":            "Core SD concepts: PBR, graphs, instances, subgraphs",
    "blend_modes":         "All blend mode integers with names and descriptions",
    "port_reference":      "Complete input/output port ID reference for all known nodes",
    "shortcuts":           "Substance Designer keyboard shortcuts",
    "connection_patterns": "Proven node connection patterns from professional graphs",
    "pbr_outputs":         "PBR output types, usages, and color space requirements",
    "node_categories":     "Overview of all node categories in the SD library",
    "all":                 "Return all documentation (large response)",
}


# ════════════════════════════════════════════════════════════════════════════
# ATOMIC NODES — Full reference
# ════════════════════════════════════════════════════════════════════════════

ATOMIC_NODES = {
    "blend": {
        "definition_id": "sbs::compositing::blend",
        "display_name": "Blend",
        "category": "Compositing",
        "description": (
            "Composites two images together using a blend mode. "
            "Foreground ('source') is blended onto background ('destination') "
            "with optional grayscale mask ('opacity'). "
            "Equivalent to Photoshop layer blending."
        ),
        "inputs": {
            "source":      {"type": "color|grayscale", "description": "Foreground layer (top)"},
            "destination": {"type": "color|grayscale", "description": "Background layer (bottom)"},
            "opacity":     {"type": "grayscale",       "description": "Blend mask (white=full blend, black=no blend)"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Blended result"},
        },
        "parameters": {
            "blendingmode": {"type": "int",   "default": 0,   "description": "Blend mode (0=Copy/Normal, 1=Add, 2=Subtract, 3=Multiply, 9=Overlay, 10=Screen, 11=Soft Light, 12=Hard Light, 13=Divide, 14=Difference)"},
            "opacitymult":  {"type": "float", "default": 1.0, "description": "Global opacity multiplier (0-1, applied on top of the mask)"},
            "alphaBlending":{"type": "int",   "default": 0,   "description": "Alpha blending mode (0=straight, 1=premultiplied)"},
        },
        "tips": [
            "Use opacity=grayscale mask for selective blending",
            "blendingmode=0 (Copy) pastes source on top of destination",
            "blendingmode=1 (Add) brightens; great for ambient occlusion layering",
            "blendingmode=14 (Difference) shows differences between two images",
        ],
    },

    "levels": {
        "definition_id": "sbs::compositing::levels",
        "display_name": "Levels",
        "category": "Adjustment",
        "description": (
            "Remaps the input value range to a new output range. "
            "Works like Photoshop Levels. Essential for contrast control, "
            "range clamping, and histogram reshaping."
        ),
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Image to remap"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Levels-adjusted image"},
        },
        "parameters": {
            "levelinlow":   {"type": "float4", "default": [0,0,0,0],     "description": "Input black point per channel (RGBA), 0=no clamp"},
            "levelinhigh":  {"type": "float4", "default": [1,1,1,1],     "description": "Input white point per channel (RGBA), 1=no clamp"},
            "leveloutlow":  {"type": "float4", "default": [0,0,0,0],     "description": "Output black point"},
            "levelouthigh": {"type": "float4", "default": [1,1,1,1],     "description": "Output white point"},
            "level_mid":    {"type": "float4", "default": [0.5,0.5,0.5,0.5], "description": "Midpoint gamma (0.5=linear)"},
        },
        "tips": [
            "For grayscale, all 4 RGBA channels are identical",
            "levelinlow > levelinhigh inverts the image",
            "Use to expand small value ranges to full 0-1",
            "Chain multiple levels for multi-stage range remapping",
        ],
    },

    "normal": {
        "definition_id": "sbs::compositing::normal",
        "display_name": "Normal",
        "category": "Material",
        "description": (
            "Converts a heightmap (grayscale) to a tangent-space normal map. "
            "Essential for PBR workflows. Output is an RGB normal map."
        ),
        "inputs": {
            "input1": {"type": "grayscale", "description": "Height map input (0=low, 1=high)"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color", "description": "Tangent-space normal map (RGB)"},
        },
        "parameters": {
            "intensity": {"type": "float", "default": 1.0, "description": "Normal map intensity/strength (higher=more pronounced normals)"},
            "invertg":   {"type": "bool",  "default": False, "description": "Invert G channel (for DirectX vs OpenGL normal convention)"},
            "normal_format": {"type": "int", "default": 0, "description": "0=OpenGL (Y-up), 1=DirectX (Y-down)"},
        },
        "tips": [
            "Always connect a height map — NOT an already-converted normal map",
            "intensity=1.0 is physically correct for most cases",
            "Use invertg=True for DirectX engines (Unreal Engine)",
            "Chain: height → Normal → output(usage='normal')",
        ],
    },

    "blur": {
        "definition_id": "sbs::compositing::blur",
        "display_name": "Blur (Fast)",
        "category": "Filter",
        "description": (
            "Fast Gaussian blur. Less quality than blur_hq_grayscale library node "
            "but faster. Good for quick softening."
        ),
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Image to blur"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Blurred image"},
        },
        "parameters": {
            "intensity": {"type": "float", "default": 1.0, "description": "Blur radius (0=no blur, 10=heavy blur)"},
        },
        "tips": [
            "For warp maps: prefer blur_hq_grayscale (library node) — cleaner result",
            "intensity is relative to output size",
        ],
    },

    "sharpen": {
        "definition_id": "sbs::compositing::sharpen",
        "display_name": "Sharpen",
        "category": "Filter",
        "description": "Enhances edge contrast to sharpen an image.",
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Image to sharpen"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Sharpened image"},
        },
        "parameters": {
            "intensity": {"type": "float", "default": 1.0, "description": "Sharpening intensity"},
        },
        "tips": ["Excessive sharpening causes ringing artifacts on normal maps"],
    },

    "warp": {
        "definition_id": "sbs::compositing::warp",
        "display_name": "Warp",
        "category": "Filter",
        "description": (
            "Distorts an image using a gradient (direction) map. "
            "The warp map's RGB channels encode XY displacement direction."
        ),
        "inputs": {
            "input1":        {"type": "color|grayscale", "description": "Image to warp/distort"},
            "inputgradient": {"type": "color",           "description": "Gradient/direction warp map (RGB)"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Warped image"},
        },
        "parameters": {
            "intensity": {"type": "float", "default": 1.0, "description": "Warp intensity/strength"},
        },
        "tips": [
            "WARP PORT: to_input='inputgradient' (not 'inputintensity' — that's directionalwarp!)",
            "Normal maps work well as warp maps — encode XY gradient",
            "Use blur_hq_grayscale on warp map for smooth distortion",
        ],
    },

    "directionalwarp": {
        "definition_id": "sbs::compositing::directionalwarp",
        "display_name": "Directional Warp",
        "category": "Filter",
        "description": (
            "Warps an image along a single direction using a grayscale intensity map. "
            "More controlled than warp — good for directional flow effects."
        ),
        "inputs": {
            "input1":         {"type": "color|grayscale", "description": "Image to warp"},
            "inputintensity": {"type": "grayscale",       "description": "Intensity map (grayscale — NOT a gradient!)"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Directionally warped image"},
        },
        "parameters": {
            "intensity": {"type": "float", "default": 1.0,  "description": "Global warp strength"},
            "angle":     {"type": "float", "default": 0.0,  "description": "Warp direction in degrees (0=right, 90=up)"},
        },
        "tips": [
            "CRITICAL: warp map port is 'inputintensity' NOT 'inputgradient'",
            "Great for rock/cliff grain direction, wood fiber, fabric weave",
            "Cascade 2-3 directionalwarp with different angles for organic feel",
            "clouds_2 → directionalwarp is a classic pattern",
        ],
    },

    "transformation": {
        "definition_id": "sbs::compositing::transformation",
        "display_name": "Transformation 2D",
        "category": "Transform",
        "description": "Applies 2D affine transformation: scale, rotation, offset. Supports tiling.",
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Image to transform"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Transformed image"},
        },
        "parameters": {
            "matrix22": {"type": "float4", "default": [1,0,0,1],   "description": "2x2 transformation matrix [m00,m01,m10,m11] for scale/rotation"},
            "offset":   {"type": "float2", "default": [0.5, 0.5],  "description": "Translation offset [x,y] in UV space (0.5=center)"},
            "mipmap":   {"type": "int",    "default": 0,            "description": "Mipmap mode for filtering"},
        },
        "tips": [
            "matrix22=[2,0,0,2] doubles the scale (zooms out 2x)",
            "matrix22=[cos(a),-sin(a),sin(a),cos(a)] for rotation angle a",
            "offset=[0,0] = top-left anchor, [0.5,0.5] = center",
        ],
    },

    "distance": {
        "definition_id": "sbs::compositing::distance",
        "display_name": "Distance",
        "category": "Filter",
        "description": (
            "Computes distance field from white areas of the input. "
            "Each pixel value = normalized distance to nearest white pixel. "
            "Works best on binary (black/white) input."
        ),
        "inputs": {
            "input1": {"type": "grayscale", "description": "Binary mask (white=source shapes)"},
        },
        "outputs": {
            "unique_filter_output": {"type": "grayscale", "description": "Distance gradient field"},
        },
        "parameters": {
            "max_distance": {"type": "float", "default": 0.1, "description": "Maximum distance (0-1 relative to image size)"},
            "invert":       {"type": "bool",  "default": False, "description": "Invert input before computing distance"},
        },
        "tips": [
            "Great for generating edge gradients from flood_fill results",
            "Chain: flood_fill → distance for per-shape gradients",
            "Use with blend to create soft borders around shapes",
        ],
    },

    "grayscaleconversion": {
        "definition_id": "sbs::compositing::grayscaleconversion",
        "display_name": "Grayscale Conversion",
        "category": "Channel",
        "description": "Converts a color (RGB/RGBA) image to grayscale using weighted channel mixing.",
        "inputs": {
            "input1": {"type": "color", "description": "Color image to convert"},
        },
        "outputs": {
            "unique_filter_output": {"type": "grayscale", "description": "Grayscale result"},
        },
        "parameters": {
            "channelsweights": {"type": "float4", "default": [0.299, 0.587, 0.114, 0.0],
                                "description": "RGBA channel weights (default=BT.601 luminance)"},
        },
        "tips": [
            "Default weights match human perceived luminance",
            "Use [1,0,0,0] to extract only red channel",
            "Use [0,1,0,0] for green channel (good for roughness from AO)",
        ],
    },

    "curve": {
        "definition_id": "sbs::compositing::curve",
        "display_name": "Curve",
        "category": "Adjustment",
        "description": "Non-linear value remapping via bezier curve control points. More flexible than Levels.",
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Image to apply curve to"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Curve-adjusted image"},
        },
        "parameters": {
            "curvesrgb": {"type": "string", "default": "", "description": "RGB curve control points (JSON format)"},
            "curvesr":   {"type": "string", "default": "", "description": "Red channel curve"},
            "curvesg":   {"type": "string", "default": "", "description": "Green channel curve"},
            "curvesb":   {"type": "string", "default": "", "description": "Blue channel curve"},
            "curvesa":   {"type": "string", "default": "", "description": "Alpha channel curve"},
        },
        "tips": ["Prefer Levels for simple linear remapping (faster, less error-prone)"],
    },

    "hsl": {
        "definition_id": "sbs::compositing::hsl",
        "display_name": "HSL",
        "category": "Adjustment",
        "description": "Adjusts Hue, Saturation, and Luminosity of a color image.",
        "inputs": {
            "input1": {"type": "color", "description": "Color image"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color", "description": "HSL-adjusted image"},
        },
        "parameters": {
            "hue":        {"type": "float", "default": 0.5, "description": "Hue shift (0-1, 0.5=no shift, 0/1=full rotation)"},
            "saturation": {"type": "float", "default": 0.5, "description": "Saturation (0=grayscale, 0.5=no change, 1=max saturation)"},
            "luminosity": {"type": "float", "default": 0.5, "description": "Luminosity (0=black, 0.5=no change, 1=white)"},
        },
        "tips": [
            "0.5 is NEUTRAL for all parameters (no change)",
            "hue=0.0 and hue=1.0 are the same (full rotation)",
            "Use with an HBR gradient for color variation",
        ],
    },

    "shuffle": {
        "definition_id": "sbs::compositing::shuffle",
        "display_name": "Channel Shuffle",
        "category": "Channel",
        "description": "Reorders or duplicates color channels. Can also copy one channel to all.",
        "inputs": {
            "input1": {"type": "color", "description": "Source image"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color", "description": "Channel-shuffled image"},
        },
        "parameters": {
            "outputcolor": {"type": "int4", "default": [0,1,2,3], "description": "Output RGBA mapping: [R_source, G_source, B_source, A_source] where 0=R,1=G,2=B,3=A"},
        },
        "tips": [
            "[0,0,0,3] copies red channel to RGB (makes it grayscale-displayed as color)",
            "Used to pack multiple grayscale maps into RGBA channels",
        ],
    },

    "emboss": {
        "definition_id": "sbs::compositing::emboss",
        "display_name": "Emboss",
        "category": "Filter",
        "description": "Creates an emboss/relief effect by simulating directional lighting on a surface.",
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Image to emboss"},
        },
        "outputs": {
            "unique_filter_output": {"type": "grayscale", "description": "Embossed (lit) image"},
        },
        "parameters": {
            "intensity": {"type": "float", "default": 1.0, "description": "Emboss depth"},
            "light_angle":{"type": "float", "default": 0.0, "description": "Light direction angle in degrees"},
            "highlight_color": {"type": "color", "default": [1,1,1,1], "description": "Highlight color"},
            "shadow_color":    {"type": "color", "default": [0,0,0,1], "description": "Shadow color"},
        },
        "tips": ["Good for generating cavity/wear masks from height maps"],
    },

    "passthrough": {
        "definition_id": "sbs::compositing::passthrough",
        "display_name": "Passthrough",
        "category": "Utility",
        "description": "Passes image through unchanged. Used for routing/organization.",
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Input image"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Identical to input"},
        },
        "parameters": {},
        "tips": [
            "Heavy use in professional graphs (52 passthroughs in pro graph)",
            "Use for signal routing clarity and sub-graph organization",
            "Does NOT change pixel values",
        ],
    },

    "uniform": {
        "definition_id": "sbs::compositing::uniform",
        "display_name": "Uniform Color",
        "category": "Generator",
        "description": "Generates a solid color or grayscale image.",
        "inputs": {},
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Solid color image"},
        },
        "parameters": {
            "outputcolor": {"type": "color", "default": [0.5, 0.5, 0.5, 1.0], "description": "The solid color to output (RGBA 0-1)"},
        },
        "tips": [
            "For pure white: outputcolor=[1,1,1,1]",
            "For pure black: outputcolor=[0,0,0,1]",
            "Use as base layer for blend nodes",
        ],
    },

    "gradient": {
        "definition_id": "sbs::compositing::gradient",
        "display_name": "Gradient Map",
        "category": "Material",
        "description": "Maps grayscale values to colors via a gradient ramp. Used to colorize height/AO maps.",
        "inputs": {
            "input1":   {"type": "grayscale", "description": "Grayscale image to colorize"},
            "gradient": {"type": "gradient",  "description": "Color gradient ramp definition"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color", "description": "Colorized image"},
        },
        "parameters": {
            "gradient": {"type": "gradient", "default": "black_to_white", "description": "Gradient ramp (set in UI or via gradient format)"},
        },
        "tips": [
            "Use to colorize grayscale base materials",
            "Chain: height → levels → gradient → baseColor output",
        ],
    },

    "output": {
        "definition_id": "sbs::compositing::output",
        "display_name": "Output",
        "category": "Output",
        "description": "Graph output node. Marks the final result of a processing chain for a specific PBR usage.",
        "inputs": {
            "inputNodeOutput": {"type": "color|grayscale", "description": "Final image to output"},
        },
        "outputs": {},
        "parameters": {
            "label": {"type": "string", "default": "output", "description": "Usage label (baseColor, normal, roughness, metallic, ambientOcclusion, height, emissive, opacity)"},
        },
        "tips": [
            "Use create_output_node(usage='baseColor') instead of create_node for proper PBR setup",
            "Connect port: to_input='inputNodeOutput'",
            "One output node per PBR channel",
        ],
    },

    "pixelprocessor": {
        "definition_id": "sbs::compositing::pixelprocessor",
        "display_name": "Pixel Processor",
        "category": "Advanced",
        "description": "Per-pixel math using a visual function graph. Extremely powerful for custom operations.",
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Primary input"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Processed image"},
        },
        "parameters": {
            "per_component": {"type": "bool", "default": True, "description": "Process each RGBA channel independently"},
        },
        "tips": [
            "Requires internal function graph — set via execute_sd_code",
            "Used for custom math ops not available in atomic nodes",
        ],
    },

    "fxmaps": {
        "definition_id": "sbs::compositing::fxmaps",
        "display_name": "FX-Map",
        "category": "Advanced",
        "description": "Scatter and iterate patterns procedurally using a quadtree structure. The most powerful pattern generator.",
        "inputs": {
            "input1": {"type": "color|grayscale", "description": "Input pattern/stamp"},
        },
        "outputs": {
            "unique_filter_output": {"type": "color|grayscale", "description": "Scattered pattern"},
        },
        "parameters": {
            "iterations": {"type": "int", "default": 1, "description": "Number of scattering passes"},
        },
        "tips": [
            "Requires internal quadtree function graph",
            "Used for tile_sampler-like patterns with full procedural control",
            "Very CPU intensive — use sparingly",
        ],
    },

    "input_color": {
        "definition_id": "sbs::compositing::input_color",
        "display_name": "Input Color",
        "category": "Input",
        "description": "Exposes a color parameter as a graph input. Allows external control of the graph.",
        "inputs": {},
        "outputs": {
            "unique_filter_output": {"type": "color", "description": "The exposed color value"},
        },
        "parameters": {
            "label":   {"type": "string", "default": "input_color", "description": "Parameter label visible externally"},
            "default": {"type": "color",  "default": [0.5,0.5,0.5,1.0], "description": "Default color value"},
        },
        "tips": ["Use to make graph parameters tweakable from Painter, Stager, etc."],
    },

    "input_grayscale": {
        "definition_id": "sbs::compositing::input_grayscale",
        "display_name": "Input Grayscale",
        "category": "Input",
        "description": "Exposes a grayscale float parameter as a graph input.",
        "inputs": {},
        "outputs": {
            "unique_filter_output": {"type": "grayscale", "description": "The exposed grayscale value"},
        },
        "parameters": {
            "label":   {"type": "string", "default": "input_grayscale", "description": "Parameter label"},
            "default": {"type": "float",  "default": 0.5, "description": "Default value (0-1)"},
        },
        "tips": ["Use for roughness, metallic, or intensity controls"],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# LIBRARY NODES — Confirmed from SD 15.0.3
# ════════════════════════════════════════════════════════════════════════════

LIBRARY_NODES = {
    # ── Noise Generators ──────────────────────────────────────────────────
    "clouds_2": {
        "identifier": "clouds_2",
        "display_name": "Clouds 2",
        "category": "Noise",
        "description": (
            "The primary professional noise generator. Produces multi-octave "
            "cloud/fractal noise. Heavy use in expert graphs (41 instances in "
            "pro 512-node graph). More natural than Perlin."
        ),
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "key_parameters": {
            "scale":      {"type": "float", "default": 1.0, "description": "Overall scale"},
            "disorder":   {"type": "float", "default": 0.5, "description": "Randomness/turbulence"},
            "pattern":    {"type": "int",   "default": 0,   "description": "Cloud pattern variant"},
            "randomseed": {"type": "int",   "default": 0,   "description": "Random seed"},
        },
        "tips": [
            "Best overall noise for rock, concrete, soil, organic materials",
            "Chain: clouds_2 → slope_blur → directionalwarp for organic surfaces",
            "clouds_2 → multi_directional_warp → blend is a pro signature pattern",
        ],
    },

    "perlin_noise": {
        "identifier": "perlin_noise",
        "display_name": "Perlin Noise",
        "category": "Noise",
        "description": "Classic Perlin noise. Smooth gradient noise for organic, flowing surfaces.",
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "key_parameters": {
            "scale":      {"type": "int",   "default": 4,   "description": "Noise scale (1-12)"},
            "disorder":   {"type": "float", "default": 1.0, "description": "Turbulence"},
            "randomseed": {"type": "int",   "default": 0,   "description": "Random seed"},
        },
        "tips": ["Good secondary noise when mixed with clouds_2"],
    },

    "cells_1": {
        "identifier": "cells_1",
        "display_name": "Cells 1",
        "category": "Noise",
        "description": "Voronoi/cell noise. Generates organic cell-like patterns. Good for skin, stone, cracked surfaces.",
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "key_parameters": {
            "scale":      {"type": "int",   "default": 4, "description": "Cell density"},
            "randomseed": {"type": "int",   "default": 0, "description": "Random seed"},
        },
        "tips": ["Combine with distance node for smooth Voronoi gradients"],
    },

    "crystal_1": {
        "identifier": "crystal_1",
        "display_name": "Crystal 1",
        "category": "Noise",
        "description": "Angular fracture/crystal noise. Excellent for rock fractures, gemstones, ice.",
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "key_parameters": {
            "scale":      {"type": "float", "default": 1.0, "description": "Scale"},
            "randomseed": {"type": "int",   "default": 0,   "description": "Random seed"},
        },
        "tips": ["9 uses in pro graph for rock fracture detail"],
    },

    "tile_sampler": {
        "identifier": "tile_sampler",
        "display_name": "Tile Sampler",
        "category": "Pattern",
        "description": (
            "Tiles an input pattern with randomization of position, rotation, "
            "scale, and color. Professional brick/tile layout tool."
        ),
        "output_id": "output",
        "outputs": {
            "output": "color|grayscale",
        },
        "key_parameters": {
            "pattern_width":  {"type": "int",   "default": 1,   "description": "Tile X count"},
            "pattern_height": {"type": "int",   "default": 1,   "description": "Tile Y count"},
            "x_amount":       {"type": "int",   "default": 4,   "description": "Tiles per row"},
            "y_amount":       {"type": "int",   "default": 4,   "description": "Tiles per column"},
            "scale":          {"type": "float", "default": 1.0, "description": "Overall scale"},
            "rotation":       {"type": "float", "default": 0.0, "description": "Random rotation amount"},
        },
        "tips": ["5 uses in pro graph", "Connect an input shape for custom tile shapes"],
    },

    "polygon_2": {
        "identifier": "polygon_2",
        "display_name": "Polygon 2",
        "category": "Pattern",
        "description": "Generates a regular polygon shape (triangle to hexagon and beyond).",
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "key_parameters": {
            "sides": {"type": "int",   "default": 6,   "description": "Number of sides (3=triangle, 4=square, 6=hexagon)"},
            "size":  {"type": "float", "default": 0.5, "description": "Shape size (0-1)"},
        },
        "tips": [],
    },

    "gradient_linear_1": {
        "identifier": "gradient_linear_1",
        "display_name": "Gradient Linear 1",
        "category": "Gradient",
        "description": "Simple linear gradient from black to white.",
        "output_id": "Simple_Gradient",
        "outputs": {"Simple_Gradient": "grayscale"},
        "key_parameters": {
            "gradient": {"type": "gradient", "default": "black_to_white", "description": "Gradient ramp"},
        },
        "tips": ["Output ID is 'Simple_Gradient' — NOT 'output' or 'unique_filter_output'"],
    },

    "gradient_axial": {
        "identifier": "gradient_axial",
        "display_name": "Gradient Axial",
        "category": "Gradient",
        "description": "Directional linear gradient with angle control.",
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "key_parameters": {
            "angle": {"type": "float", "default": 0.0, "description": "Gradient angle"},
        },
        "tips": [],
    },

    # ── Filter Nodes ──────────────────────────────────────────────────────
    "blur_hq_grayscale": {
        "identifier": "blur_hq_grayscale",
        "display_name": "Blur HQ Grayscale",
        "category": "Filter",
        "description": (
            "High-quality Gaussian blur for grayscale images. "
            "Preferred over atomic blur for warp maps and smooth gradients."
        ),
        "output_id": "Blur_HQ",
        "outputs": {"Blur_HQ": "grayscale"},
        "key_parameters": {
            "intensity": {"type": "float", "default": 1.0, "description": "Blur radius"},
            "quality":   {"type": "int",   "default": 0,   "description": "Quality level (0=fast, 1=medium, 2=high)"},
        },
        "tips": [
            "Output is 'Blur_HQ' NOT 'output'",
            "14 uses in pro graph — always preferred for warp prep",
            "Chain before directionalwarp/warp for clean distortion",
        ],
    },

    "slope_blur_grayscale_2": {
        "identifier": "slope_blur_grayscale_2",
        "display_name": "Slope Blur Grayscale 2",
        "category": "Filter",
        "description": (
            "Blurs an image along its own gradient direction (slope). "
            "Creates directional smearing following the local slope. "
            "Key node for rock/cliff/organic surfaces."
        ),
        "output_id": "Slope_Blur",
        "outputs": {"Slope_Blur": "grayscale"},
        "inputs": {
            "Source":   "grayscale (image to blur)",
            "Gradient": "grayscale (optional: external gradient to use instead of self)",
        },
        "key_parameters": {
            "intensity":  {"type": "float", "default": 1.0, "description": "Blur strength"},
            "samples":    {"type": "int",   "default": 1,   "description": "Quality samples (higher=smoother but slower)"},
            "mode":       {"type": "int",   "default": 0,   "description": "0=Blur, 1=Min, 2=Max"},
        },
        "tips": [
            "Output is 'Slope_Blur' NOT 'output'",
            "22 uses in pro graph — signature pattern for rock detail",
            "clouds_2 → slope_blur → slope_blur creates layered surface detail",
            "Cascade 2 slope_blurs with different intensities for complexity",
        ],
    },

    "invert_grayscale": {
        "identifier": "invert_grayscale",
        "display_name": "Invert Grayscale",
        "category": "Filter",
        "description": "Inverts grayscale values (1-x for each pixel).",
        "output_id": "Invert_Grayscale",
        "outputs": {"Invert_Grayscale": "grayscale"},
        "key_parameters": {},
        "tips": [
            "Output is 'Invert_Grayscale' NOT 'output'",
            "10 uses in pro graph for mask inversion",
        ],
    },

    "non_uniform_blur_grayscale": {
        "identifier": "non_uniform_blur_grayscale",
        "display_name": "Non Uniform Blur Grayscale",
        "category": "Filter",
        "description": "Anisotropic (directional) blur with independent X/Y control. More powerful than standard blur.",
        "output_id": "Non_Uniform_Blur",
        "outputs": {"Non_Uniform_Blur": "grayscale"},
        "inputs": {
            "Source": "grayscale (image to blur)",
            "Effect": "grayscale (optional mask for local blur control)",
        },
        "key_parameters": {
            "Intensity":   {"type": "float", "default": 1.0,  "description": "Overall blur radius"},
            "Anisotropy":  {"type": "float", "default": 0.0,  "description": "0=circular, 1=fully directional"},
            "Asymmetry":   {"type": "float", "default": 0.0,  "description": "Blur asymmetry along direction"},
            "Angle":       {"type": "float", "default": 0.0,  "description": "Blur angle in degrees"},
            "Samples":     {"type": "int",   "default": 16,   "description": "Quality samples"},
        },
        "tips": [
            "Output is 'Non_Uniform_Blur' NOT 'output'",
            "Input ports: 'Source' (not 'input1'), 'Effect' (optional)",
            "Good for grain direction in wood, metal, fabric",
        ],
    },

    "edge_detect": {
        "identifier": "edge_detect",
        "display_name": "Edge Detect",
        "category": "Filter",
        "description": (
            "Detects edges/ridges in a grayscale image. Returns a grayscale "
            "mask of high-contrast areas. Critical for ridge/cavity masking."
        ),
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "inputs": {
            "input": "grayscale (source image)",
        },
        "key_parameters": {
            "edge_width":     {"type": "float", "default": 2.0,  "description": "Width of detected edges"},
            "edge_roundness": {"type": "float", "default": 0.0,  "description": "Edge roundness (0=sharp, 1=round)"},
            "invert":         {"type": "bool",  "default": False, "description": "Invert result"},
            "tolerance":      {"type": "float", "default": 0.0,  "description": "Detection sensitivity"},
        },
        "tips": [
            "Input port is 'input' NOT 'input1'",
            "24 uses in pro graph — key for ridge masks",
            "Chain: clouds_2 → slope_blur → edge_detect → blend",
            "edge_detect → flood_fill is a classic seeding pattern",
        ],
    },

    "flood_fill": {
        "identifier": "flood_fill",
        "display_name": "Flood Fill",
        "category": "Filter",
        "description": (
            "Assigns a unique random color to each connected region (island) "
            "in the input. Input should be a binary mask of shape outlines. "
            "Enables per-island variation."
        ),
        "output_id": "output",
        "outputs": {"output": "color"},
        "inputs": {
            "mask":          "grayscale (optional mask)",
            "profileOverride": "grayscale (override profile per region)",
        },
        "key_parameters": {
            "profile":  {"type": "int", "default": 0, "description": "Fill profile type"},
            "advanced": {"type": "bool", "default": False, "description": "Enable advanced options"},
        },
        "tips": [
            "23 uses in pro graph — essential for variation",
            "edge_detect → flood_fill: edges define island boundaries",
            "Output is COLOR (each island has unique color, not grayscale!)",
            "Connect to flood_fill_to_gradient_2 or flood_fill_to_grayscale after",
        ],
    },

    "flood_fill_to_gradient_2": {
        "identifier": "flood_fill_to_gradient_2",
        "display_name": "Flood Fill to Gradient 2",
        "category": "Filter",
        "description": "Converts a flood fill output to a directional gradient per island. Creates smooth gradient ramps within each filled region.",
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "inputs": {
            "input":       "color (flood_fill output)",
            "angle_input": "grayscale (optional angle variation per island)",
        },
        "key_parameters": {
            "angle":           {"type": "float", "default": 0.0, "description": "Gradient angle"},
            "angle_variation": {"type": "float", "default": 0.0, "description": "Random angle variation per island"},
        },
        "tips": [
            "18 uses in pro graph — classic flood_fill → gradient_2 chain",
            "Input port: 'input' (not 'input1')",
            "Output: grayscale gradient per island (great for shape variation)",
        ],
    },

    "flood_fill_to_grayscale": {
        "identifier": "flood_fill_to_grayscale",
        "display_name": "Flood Fill to Grayscale",
        "category": "Filter",
        "description": "Converts a flood fill output to a random grayscale value per island.",
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "inputs": {
            "input": "color (flood_fill output)",
        },
        "key_parameters": {
            "luminance_adjustement": {"type": "float", "default": 0.5, "description": "Mean luminance"},
            "luminance_random":      {"type": "float", "default": 0.5, "description": "Luminance variation range"},
        },
        "tips": [
            "7 uses in pro graph",
            "Input port: 'input' (not 'input1')",
            "Creates per-island grayscale variation for blend masks",
        ],
    },

    "multi_directional_warp_grayscale": {
        "identifier": "multi_directional_warp_grayscale",
        "display_name": "Multi Directional Warp Grayscale",
        "category": "Filter",
        "description": (
            "Warps a grayscale image in multiple directions simultaneously. "
            "More complex distortion than directionalwarp. "
            "Key node in pro professional rock/concrete recipes."
        ),
        "output_id": "output",
        "outputs": {"output": "grayscale"},
        "inputs": {
            "input":           "grayscale (image to warp)",
            "intensity_input": "grayscale (optional variable intensity map)",
        },
        "key_parameters": {
            "intensity":   {"type": "float", "default": 1.0, "description": "Warp strength"},
            "warp_angle":  {"type": "float", "default": 0.0, "description": "Primary warp angle"},
            "mode":        {"type": "int",   "default": 0,   "description": "Warp mode"},
            "directions":  {"type": "int",   "default": 4,   "description": "Number of warp directions"},
        },
        "tips": [
            "26 uses in pro graph — key complexity node",
            "Cascade 2× for much richer surface detail",
            "clouds_2 → multi_dir_warp → multi_dir_warp is signature chain",
            "Input ports: 'input', 'intensity_input'",
        ],
    },

    "highpass_grayscale": {
        "identifier": "highpass_grayscale",
        "display_name": "Highpass Grayscale",
        "category": "Filter",
        "description": (
            "Extracts high-frequency detail by subtracting a blurred version "
            "from the original. Returns only the fine surface detail."
        ),
        "output_id": "Highpass",
        "outputs": {"Highpass": "grayscale"},
        "inputs": {
            "Source": "grayscale (source image)",
        },
        "key_parameters": {
            "Radius": {"type": "float", "default": 2.0, "description": "Highpass radius (detail scale to extract)"},
        },
        "tips": [
            "Output is 'Highpass' NOT 'output'",
            "Input port is 'Source' NOT 'input1'",
            "5 uses in pro graph for micro-detail extraction",
            "Chain at end of stack: main_shape → ... → highpass → blend(Add) for detail overlay",
        ],
    },

    "histogram_scan": {
        "identifier": "histogram_scan",
        "display_name": "Histogram Scan",
        "category": "Filter",
        "description": (
            "Remaps histogram by scanning from a position with contrast control. "
            "Creates sharp or soft thresholds in grayscale images. "
            "More powerful than Levels for threshold operations."
        ),
        "output_id": "Output",
        "outputs": {"Output": "grayscale"},
        "inputs": {
            "Input_1": "grayscale (source image)",
        },
        "key_parameters": {
            "Position":       {"type": "float", "default": 0.5, "description": "Scan threshold position (0-1)"},
            "Contrast":       {"type": "float", "default": 0.0, "description": "Output contrast (0=soft, 1=hard binary)"},
            "Invert_Position":{"type": "bool",  "default": False,"description": "Invert threshold position"},
        },
        "tips": [
            "Output is 'Output' (capital O), input is 'Input_1'",
            "6 uses in pro graph at final stage",
            "Contrast=1.0 → binary mask; Contrast=0.0 → smooth gradient",
            "Perfect for controlling how much of a noise shape is visible",
        ],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# BLEND MODES
# ════════════════════════════════════════════════════════════════════════════

BLEND_MODES_DOC = {
    0:  {"name": "Copy / Normal",    "description": "Source replaces destination (alpha-aware)"},
    1:  {"name": "Add",              "description": "Adds pixel values — brightens. Max=1."},
    2:  {"name": "Subtract",         "description": "Subtracts source from destination. Min=0."},
    3:  {"name": "Multiply",         "description": "Multiplies values — darkens. Black kills output."},
    4:  {"name": "Max (Lighten)",    "description": "Takes the brighter of the two pixels"},
    5:  {"name": "Min (Darken)",     "description": "Takes the darker of the two pixels"},
    6:  {"name": "Switch",           "description": "Switches between source/destination based on mask"},
    7:  {"name": "Divide",           "description": "Divides destination by source"},
    8:  {"name": "Dodge",            "description": "Brightens destination based on source"},
    9:  {"name": "Overlay",          "description": "Multiplies darks, screens lights — contrast boost"},
    10: {"name": "Screen",           "description": "Opposite of Multiply — brightens"},
    11: {"name": "Soft Light",       "description": "Subtle overlay — gentle contrast"},
    12: {"name": "Hard Light",       "description": "Strong overlay — heavy contrast"},
    13: {"name": "Linear Light",     "description": "Add+Overlay combination"},
    14: {"name": "Difference",       "description": "Absolute difference — shows changes"},
    15: {"name": "Luminosity",       "description": "Keeps source luminosity, destination hue/saturation"},
    16: {"name": "Color",            "description": "Keeps source hue+saturation, destination luminosity"},
    17: {"name": "Hue",              "description": "Keeps source hue, destination saturation+luminosity"},
    18: {"name": "Saturation",       "description": "Keeps source saturation, destination hue+luminosity"},
}


# ════════════════════════════════════════════════════════════════════════════
# PORT REFERENCE — Complete known port IDs
# ════════════════════════════════════════════════════════════════════════════

PORT_REFERENCE = {
    "atomic_nodes": {
        "blend":               {"inputs": ["source", "destination", "opacity"],    "output": "unique_filter_output"},
        "levels":              {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "curve":               {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "hsl":                 {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "blur":                {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "sharpen":             {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "warp":                {"inputs": ["input1", "inputgradient"],              "output": "unique_filter_output"},
        "directionalwarp":     {"inputs": ["input1", "inputintensity"],             "output": "unique_filter_output"},
        "normal":              {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "transformation":      {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "distance":            {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "grayscaleconversion": {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "shuffle":             {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "emboss":              {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "passthrough":         {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "uniform":             {"inputs": [],                                        "output": "unique_filter_output"},
        "gradient":            {"inputs": ["input1", "gradient"],                   "output": "unique_filter_output"},
        "pixelprocessor":      {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "fxmaps":              {"inputs": ["input1"],                               "output": "unique_filter_output"},
        "input_color":         {"inputs": [],                                        "output": "unique_filter_output"},
        "input_grayscale":     {"inputs": [],                                        "output": "unique_filter_output"},
        "output":              {"inputs": ["inputNodeOutput"],                       "output": None},
    },
    "library_nodes": {
        "clouds_2":                         {"inputs": [],             "output": "output"},
        "perlin_noise":                     {"inputs": [],             "output": "output"},
        "cells_1":                          {"inputs": [],             "output": "output"},
        "crystal_1":                        {"inputs": [],             "output": "output"},
        "gradient_linear_1":                {"inputs": [],             "output": "Simple_Gradient"},
        "gradient_axial":                   {"inputs": [],             "output": "output"},
        "polygon_2":                        {"inputs": [],             "output": "output"},
        "blur_hq_grayscale":                {"inputs": ["Source"],     "output": "Blur_HQ"},
        "slope_blur_grayscale_2":           {"inputs": ["Source", "Gradient"], "output": "Slope_Blur"},
        "invert_grayscale":                 {"inputs": ["Source"],     "output": "Invert_Grayscale"},
        "non_uniform_blur_grayscale":       {"inputs": ["Source", "Effect"], "output": "Non_Uniform_Blur"},
        "edge_detect":                      {"inputs": ["input"],      "output": "output"},
        "flood_fill":                       {"inputs": ["mask", "profileOverride"], "output": "output"},
        "flood_fill_to_gradient_2":         {"inputs": ["input", "angle_input"], "output": "output"},
        "flood_fill_to_grayscale":          {"inputs": ["input"],      "output": "output"},
        "multi_directional_warp_grayscale": {"inputs": ["input", "intensity_input"], "output": "output"},
        "highpass_grayscale":               {"inputs": ["Source"],     "output": "Highpass"},
        "histogram_scan":                   {"inputs": ["Input_1"],    "output": "Output"},
        "tile_sampler":                     {"inputs": ["input"],      "output": "output"},
    },
    "critical_notes": [
        "Library node output IDs are NEVER 'unique_filter_output'",
        "warp warp-map port: 'inputgradient' (takes color/RGB gradient)",
        "directionalwarp warp-map port: 'inputintensity' (takes grayscale)",
        "blur_hq_grayscale input: 'Source' (not 'input1'), output: 'Blur_HQ'",
        "slope_blur input: 'Source' (not 'input1'), output: 'Slope_Blur'",
        "histogram_scan input: 'Input_1', output: 'Output' (capital O)",
        "edge_detect input: 'input' (lowercase, not 'input1')",
        "flood_fill outputs COLOR not grayscale",
        "flood_fill_to_gradient_2 and flood_fill_to_grayscale input: 'input'",
        "gradient_linear_1 output: 'Simple_Gradient'",
    ],
}


# ════════════════════════════════════════════════════════════════════════════
# PBR OUTPUTS
# ════════════════════════════════════════════════════════════════════════════

PBR_OUTPUTS = {
    "baseColor": {
        "usage":       "baseColor",
        "type":        "color",
        "description": "Albedo/base color. Linear sRGB, no lighting information.",
        "color_space": "sRGB",
        "value_range": "0-1 per channel",
        "tips": ["No AO baked in for PBR", "Keep metallic areas dark (black for pure metal)"],
    },
    "normal": {
        "usage":       "normal",
        "type":        "color",
        "description": "Tangent-space normal map. R=X, G=Y, B=Z directions.",
        "color_space": "Linear",
        "value_range": "0-1 (remapped from -1 to 1 normal vectors)",
        "default_flat": [0.5, 0.5, 1.0],
        "tips": [
            "Neutral normal (flat surface) = [0.5, 0.5, 1.0]",
            "OpenGL: G=up, DirectX: G=down (use invertg param)",
            "Chain: height → Normal node → output(normal)",
        ],
    },
    "roughness": {
        "usage":       "roughness",
        "type":        "grayscale",
        "description": "Surface roughness. 0=mirror/smooth, 1=matte/rough.",
        "color_space": "Linear",
        "value_range": "0.0 (mirror) to 1.0 (matte)",
        "tips": ["Metal=0.1-0.3, plastic=0.3-0.6, concrete=0.6-0.9"],
    },
    "metallic": {
        "usage":       "metallic",
        "type":        "grayscale",
        "description": "Metallic/dielectric mask. 1=metal, 0=non-metal (binary for most engines).",
        "color_space": "Linear",
        "value_range": "0 or 1 (binary for PBR metal/rough workflow)",
        "tips": ["Most materials are 0 (pure dielectric)", "Rust/weathering uses partial values (0.1-0.4)"],
    },
    "height": {
        "usage":       "height",
        "type":        "grayscale",
        "description": "Height/displacement map. 0=lowest, 1=highest.",
        "color_space": "Linear",
        "value_range": "0.0 to 1.0",
        "tips": ["Used by tessellation engines", "Middle grey (0.5) = flat surface"],
    },
    "ambientOcclusion": {
        "usage":       "ambientOcclusion",
        "type":        "grayscale",
        "description": "Ambient occlusion. 1=fully lit, 0=fully occluded/dark.",
        "color_space": "Linear",
        "value_range": "0.0 to 1.0",
        "tips": ["Generate from height using distance or cavity extraction", "White=exposed, Black=occluded"],
    },
    "emissive": {
        "usage":       "emissive",
        "type":        "color",
        "description": "Self-illumination color. Values > 1.0 for HDR emissive (physically bright).",
        "color_space": "Linear",
        "value_range": "0+ (can exceed 1 for HDR)",
        "tips": ["Black/zero = no emission (most materials)", "Use sparingly"],
    },
    "opacity": {
        "usage":       "opacity",
        "type":        "grayscale",
        "description": "Transparency mask. 1=opaque, 0=transparent.",
        "color_space": "Linear",
        "value_range": "0.0 to 1.0",
        "tips": ["Requires transparency-enabled material in engine"],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# CONNECTION PATTERNS — Proven professional chains
# ════════════════════════════════════════════════════════════════════════════

CONNECTION_PATTERNS = {
    "pro_perez_signature": {
        "description": "Core patterns from pro 512-node professional graph (MeshModeler)",
        "patterns": [
            {
                "name": "Cloud-driven slope flow",
                "chain": ["clouds_2", "slope_blur_grayscale_2", "slope_blur_grayscale_2"],
                "description": "Noise driving directional slope blur (cascaded). Primary texture base.",
                "frequency": "41×clouds + 22×slope_blur in graph",
            },
            {
                "name": "Multi-directional warp stack",
                "chain": ["clouds_2", "multi_directional_warp_grayscale", "multi_directional_warp_grayscale"],
                "description": "Noise warped in multiple directions for organic complexity.",
                "frequency": "26×multi_dir_warp in graph",
            },
            {
                "name": "Flood fill variation",
                "chain": ["edge_detect", "flood_fill", "flood_fill_to_gradient_2"],
                "description": "Edge-seeded flood fill → per-island gradient for shape variation.",
                "frequency": "18× in graph",
            },
            {
                "name": "Highpass detail overlay",
                "chain": ["...", "highpass_grayscale", "blend(Add)"],
                "description": "Extract fine detail and add it back as a detail pass.",
                "frequency": "5×highpass in graph",
            },
            {
                "name": "Histogram threshold",
                "chain": ["...", "histogram_scan"],
                "description": "Final value range control with soft/hard threshold.",
                "frequency": "6×histogram_scan at output stages",
            },
            {
                "name": "Blend mask layering",
                "chain": ["levels", "blend"],
                "description": "Remap a mask with levels then use as blend opacity.",
                "frequency": "22×levels→blend",
            },
        ],
    },

    "classic_pbr_chain": {
        "description": "Standard PBR material output chain",
        "patterns": [
            {
                "name": "Height to Normal",
                "chain": ["height_source", "normal", "output(normal)"],
                "ports": "height→input1 → normal→inputNodeOutput",
            },
            {
                "name": "Grayscale to color (gradient)",
                "chain": ["grayscale_source", "gradient", "hsl", "output(baseColor)"],
                "description": "Colorize a grayscale with gradient, then adjust hue",
            },
            {
                "name": "AO from height",
                "chain": ["height", "levels(darken)", "blend(Multiply, AO)", "output(ambientOcclusion)"],
                "description": "Quick AO approximation",
            },
        ],
    },

    "warp_combos": {
        "description": "Effective warp combinations",
        "patterns": [
            {
                "name": "Smooth directional warp",
                "chain": ["noise", "blur_hq_grayscale", "directionalwarp"],
                "note": "Blur the noise first for smooth warp map → clean result",
            },
            {
                "name": "Multi-pass cloud warp",
                "chain": ["clouds_2", "directionalwarp(angle=0)", "directionalwarp(angle=90)", "directionalwarp(angle=45)"],
                "note": "Cascade 3 directional warps with different angles",
            },
            {
                "name": "Shape warp with floods",
                "chain": ["shape", "edge_detect", "flood_fill", "flood_fill_to_gradient_2", "warp"],
                "note": "Per-island gradient drives warp for varied distortion",
            },
        ],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# WORKFLOW RULES
# ════════════════════════════════════════════════════════════════════════════

WORKFLOW = {
    "sd_mcp_rules": [
        "ONE CALL AT A TIME — never parallel SD tool calls, always wait for each response",
        "STEP ORDER: get_scene_info → create_graph → create_node(s) → get_node_info (lib nodes) → connect_nodes → get_graph_info → open_graph",
        "newNode(unknown_def) HANGS SD 15 permanently — always validate first",
        "SDUsage.sNew() HANGS SD 15 — removed from plugin, never re-add",
        "arrange_nodes() DESTROYS ALL connections — never use, use move_node() instead",
        "Library node output IDs ≠ 'unique_filter_output' — always get_node_info first",
        "directionalwarp warp map port = 'inputintensity' (NOT 'inputgradient')",
        "connect_nodes with wrong port ID crashes SD 15 — plugin validates before calling SD",
        "Library nodes CANNOT be duplicated via duplicate_node — use create_instance_node again",
        "Graph names are auto-sanitized: spaces→underscores, must start with letter",
        "SD 15: SDValueInt2/3/4 on float params crashes SD silently — use float vectors",
        "SD must be started BEFORE Claude Code for MCP tools to work",
    ],
    "recommended_workflow": [
        "1. get_scene_info — verify SD is connected and packages are loaded",
        "2. create_graph — create a new graph with a descriptive name",
        "3. For atomic nodes: create_node(definition_id='sbs::compositing::...')",
        "4. For library nodes: get_library_nodes(filter_text='keyword') to get pkg:// URL",
        "5. create_instance_node(resource_url='pkg://...') for library nodes",
        "6. get_node_info(node_id) — discover exact port IDs for library nodes",
        "7. connect_nodes one by one — specify from_output and to_input explicitly",
        "8. set_parameter for any needed adjustments",
        "9. get_graph_info — verify the complete graph structure",
        "10. open_graph — display the graph in SD editor",
        "11. save_package — save the .sbs file",
    ],
    "node_creation_methods": {
        "atomic_node":   "create_node(definition_id='sbs::compositing::blend')",
        "output_node":   "create_output_node(usage='baseColor')",
        "library_node":  "create_instance_node(resource_url='pkg:///cells_1?dependency=...')",
        "batch":         "create_batch_graph(graph_name, nodes=[...], connections=[...])",
        "recipe":        "build_material_graph(graph_name, recipe_name='steel')",
        "heightmap":     "build_heightmap_graph(graph_name, style='cliff')",
    },
}


# ════════════════════════════════════════════════════════════════════════════
# SHORTCUTS
# ════════════════════════════════════════════════════════════════════════════

SHORTCUTS = {
    "graph_view": {
        "F":             "Frame all nodes",
        "A":             "Frame selected nodes",
        "Delete":        "Delete selected nodes",
        "Ctrl+D":        "Duplicate selected",
        "Ctrl+G":        "Group selected nodes",
        "Ctrl+A":        "Select all",
        "Escape":        "Deselect all",
        "Alt+Click":     "Add node from search",
        "Space":         "Open node search",
        "Ctrl+Z":        "Undo",
        "Ctrl+Y":        "Redo",
        "Ctrl+S":        "Save package",
        "Tab":           "Open node search",
        "1":             "Zoom to 100%",
        "2":             "Zoom to 200%",
        "Alt+Drag":      "Pan the graph",
        "Scroll":        "Zoom in/out",
        "Middle+Drag":   "Pan the graph",
    },
    "2d_view": {
        "F":         "Fit image in view",
        "R/G/B/A":   "Show only R/G/B/A channel",
        "C":         "Show combined RGBA",
        "Ctrl+C":    "Copy color under cursor",
        "+/-":       "Zoom in/out",
    },
    "3d_view": {
        "F":             "Focus on mesh",
        "Alt+LeftDrag":  "Rotate camera",
        "Alt+RightDrag": "Zoom camera",
        "Alt+MiddleDrag":"Pan camera",
        "R":             "Reset camera",
    },
    "explorer": {
        "F2":        "Rename resource",
        "Delete":    "Delete resource",
        "Ctrl+N":    "New graph",
        "Enter":     "Open selected resource",
    },
    "property_panel": {
        "Enter":     "Confirm value edit",
        "Escape":    "Cancel value edit",
        "Ctrl+Z":    "Undo last param change",
    },
}


# ════════════════════════════════════════════════════════════════════════════
# CONCEPTS
# ════════════════════════════════════════════════════════════════════════════

CONCEPTS = {
    "substance_graph": {
        "name": "Substance Graph (SBS Compositing Graph)",
        "description": (
            "A node-based procedural graph that generates textures non-destructively. "
            "All nodes are procedural — changing parameters re-generates outputs in real-time. "
            "Graphs can be published as .sbsar (baked, distributable) or used live in SD."
        ),
        "key_facts": [
            "Output resolution set via $outputsize parameter (log2 format: 11=2048)",
            "Graphs can be instanced in other graphs as sub-graphs",
            "Parameters can be exposed for external control (Painter, Stager, etc.)",
            "Color space: linear by default; sRGB for baseColor output",
        ],
    },
    "sbsar": {
        "name": "SBSAR (Substance Archive)",
        "description": "Compiled, distributable version of a Substance graph. Smaller, faster, used in engines.",
        "key_facts": [
            "Generated via File > Export > SBSAR",
            "Exposes only graph outputs and exposed parameters",
            "No source node graph visible — protects IP",
            "Supported by: UE5, Unity, Blender, Modo, 3ds Max, etc.",
        ],
    },
    "instance_node": {
        "name": "Instance Node",
        "description": "A node that instances another graph (either library or custom). Creates a reusable sub-graph.",
        "key_facts": [
            "Created via create_instance_node(resource_url='pkg://...')",
            "Library nodes are all instance nodes of built-in SD library graphs",
            "Custom graphs can be instanced in other graphs for modular workflows",
            "get_node_info() reveals the exact port IDs of any instance node",
        ],
    },
    "parameter_exposure": {
        "name": "Exposed Parameter",
        "description": "A graph-level parameter visible and tweakable from outside the graph.",
        "key_facts": [
            "Created via input_color or input_grayscale nodes",
            "Visible in Properties panel when graph is selected",
            "Accessible in SBSAR by end applications (Painter, engines, etc.)",
            "Use to make material properties tweakable (roughness, color, etc.)",
        ],
    },
    "inheritance": {
        "name": "Parameter Inheritance",
        "description": "Sub-graphs inherit $outputsize and $randomseed from parent graph unless overridden.",
        "key_facts": [
            "Child graph uses parent resolution by default",
            "Override by setting $outputsize on specific nodes",
            "Useful for multi-resolution outputs in one graph",
        ],
    },
    "output_size": {
        "name": "Output Size ($outputsize)",
        "description": "Resolution of the graph output in log2 format.",
        "values": {
            9:  "512×512",
            10: "1024×1024",
            11: "2048×2048",
            12: "4096×4096",
            13: "8192×8192",
        },
        "set_via": "set_graph_output_size(width_log2=11, height_log2=11)",
    },
    "pbr_workflow": {
        "name": "PBR Metal/Roughness Workflow",
        "description": "Standard physically-based rendering workflow for game engines and VFX.",
        "required_outputs": ["baseColor", "normal", "roughness", "metallic"],
        "optional_outputs": ["height", "ambientOcclusion", "emissive", "opacity"],
        "tips": [
            "All textures in LINEAR color space except baseColor (sRGB)",
            "build_material_graph() generates all 6 PBR outputs automatically",
            "Roughness and metallic are grayscale (0-1)",
            "Normal map flat value = [0.5, 0.5, 1.0]",
        ],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# NODE CATEGORIES OVERVIEW
# ════════════════════════════════════════════════════════════════════════════

NODE_CATEGORIES = {
    "atomic_compositing": {
        "description": "Built-in compositing nodes. Always available, no library required.",
        "nodes": list(ATOMIC_NODES.keys()),
        "prefix": "sbs::compositing::",
    },
    "noise_generators": {
        "description": "Library noise nodes. Generate procedural noise textures.",
        "nodes": ["clouds_2", "perlin_noise", "cells_1", "crystal_1", "gaussian_noise",
                  "white_noise_1", "brownian_motion", "fractal_sum_1", "voronoi_1",
                  "anisotropic_noise", "moisture_1", "swirl_1"],
    },
    "pattern_generators": {
        "description": "Library pattern nodes. Generate structured geometric patterns.",
        "nodes": ["polygon_2", "tile_sampler", "brick_generator_1", "tile_generator_1",
                  "shape_splatter_1", "circle_burst_1", "weave_generator_1",
                  "scratches_generator_1", "grunge_map_001", "stains_1"],
    },
    "gradient_generators": {
        "description": "Library gradient nodes.",
        "nodes": ["gradient_linear_1", "gradient_axial", "gradient_circular_1",
                  "gradient_map", "gradient_radial_1"],
    },
    "filter_nodes": {
        "description": "Library filter nodes. Transform and process existing images.",
        "nodes": ["blur_hq_grayscale", "slope_blur_grayscale_2", "non_uniform_blur_grayscale",
                  "edge_detect", "flood_fill", "flood_fill_to_gradient_2",
                  "flood_fill_to_grayscale", "multi_directional_warp_grayscale",
                  "highpass_grayscale", "histogram_scan", "invert_grayscale",
                  "make_it_tile_photo", "histogram_shift", "histogram_range",
                  "rgba_split", "rgba_merge", "normal_blend", "normal_sobel"],
    },
    "material_filters": {
        "description": "Library nodes for material-specific operations.",
        "nodes": ["height_to_normal_world_units", "normal_to_height", "curvature_smooth",
                  "ambient_occlusion_2", "bent_normals", "light_map"],
    },
}


# ════════════════════════════════════════════════════════════════════════════
# PARAMETERS REFERENCE
# ════════════════════════════════════════════════════════════════════════════

PARAMETERS_REFERENCE = {
    "common_graph_params": {
        "$outputsize": {"type": "int2",  "description": "Resolution as log2 [w,h], e.g. [11,11]=2048×2048"},
        "$format":     {"type": "int",   "description": "Output format (0=auto, 1=8bit, 2=16bit, 3=32bit)"},
        "$pixelsize":  {"type": "float2","description": "Pixel size in world units"},
        "$pixelratio": {"type": "float", "description": "Pixel aspect ratio"},
        "$tiling":     {"type": "int",   "description": "Tiling mode (0=no tiling, 3=xy tiling)"},
        "$randomseed": {"type": "int",   "description": "Global random seed for procedural variation"},
        "$time":       {"type": "float", "description": "Time for animated graphs"},
    },
    "common_node_params": {
        "intensity":       {"type": "float", "range": "0-10+", "description": "Strength/amount of effect"},
        "blendingmode":    {"type": "int",   "range": "0-18",  "description": "Blend mode (see blend_modes)"},
        "opacitymult":     {"type": "float", "range": "0-1",   "description": "Blend opacity multiplier"},
        "hue":             {"type": "float", "range": "0-1",   "description": "Hue shift (0.5=neutral)"},
        "saturation":      {"type": "float", "range": "0-1",   "description": "Saturation (0.5=neutral)"},
        "luminosity":      {"type": "float", "range": "0-1",   "description": "Luminosity (0.5=neutral)"},
        "levelinlow":      {"type": "float4","range": "0-1×4", "description": "Levels input low (per RGBA channel)"},
        "levelinhigh":     {"type": "float4","range": "0-1×4", "description": "Levels input high"},
        "leveloutlow":     {"type": "float4","range": "0-1×4", "description": "Levels output low"},
        "levelouthigh":    {"type": "float4","range": "0-1×4", "description": "Levels output high"},
        "outputcolor":     {"type": "color", "range": "0-1×4", "description": "Solid color (RGBA) for uniform node"},
        "channelsweights": {"type": "float4","range": "0-1×4", "description": "Channel weights for grayscale conversion"},
        "matrix22":        {"type": "float4","range": "any",   "description": "2x2 transform matrix [m00,m01,m10,m11]"},
        "offset":          {"type": "float2","range": "0-1",   "description": "UV offset for transformation"},
        "angle":           {"type": "float", "range": "0-360", "description": "Angle in degrees"},
        "scale":           {"type": "float", "range": "0.1-10","description": "Scale factor"},
        "randomseed":      {"type": "int",   "range": "0+",    "description": "Random seed for procedural variation"},
        "invertg":         {"type": "bool",  "range": "0/1",   "description": "Invert G channel of normal map"},
    },
    "value_types": {
        "float":    "Single float value (e.g., 0.5)",
        "int":      "Integer value (e.g., 4)",
        "bool":     "Boolean True/False",
        "string":   "Text string",
        "float2":   "2-component vector [x, y]",
        "float3":   "3-component vector [x, y, z]",
        "float4":   "4-component vector [x, y, z, w] or [r, g, b, a]",
        "color":    "RGBA color [r, g, b, a] all 0-1",
        "int2":     "2-component integer vector",
        "int3":     "3-component integer vector",
        "int4":     "4-component integer vector",
    },
}


# ════════════════════════════════════════════════════════════════════════════
# MAIN QUERY FUNCTION
# ════════════════════════════════════════════════════════════════════════════

def query_documentation(category="all", filter_text="", node_name=""):
    """
    Query the SD documentation knowledge base.

    Args:
        category:    One of the CATEGORIES keys (or 'all')
        filter_text: Optional substring filter (case-insensitive)
        node_name:   Optional specific node name for detailed lookup

    Returns:
        dict with documentation data
    """
    cat = category.lower().strip()
    ft  = filter_text.lower().strip()

    # ── Specific node lookup ───────────────────────────────────────────────
    if node_name:
        nn = node_name.lower().replace(" ", "_").replace("-", "_")
        if nn in ATOMIC_NODES:
            return {"type": "atomic_node", "data": ATOMIC_NODES[nn]}
        if nn in LIBRARY_NODES:
            return {"type": "library_node", "data": LIBRARY_NODES[nn]}
        # Try partial match
        matches = {}
        for k, v in ATOMIC_NODES.items():
            if nn in k or nn in v.get("display_name", "").lower():
                matches[k] = v
        for k, v in LIBRARY_NODES.items():
            if nn in k or nn in v.get("display_name", "").lower():
                matches[k] = v
        if matches:
            return {"type": "node_search_results", "query": node_name, "data": matches}
        return {"error": "Node '{}' not found. Use filter_text or check the node name.".format(node_name)}

    def _filter(data_dict):
        """Apply filter_text to a dict of items."""
        if not ft:
            return data_dict
        result = {}
        for k, v in data_dict.items():
            key_match = ft in k.lower()
            val_str   = str(v).lower()
            if key_match or ft in val_str:
                result[k] = v
        return result

    # ── Category dispatch ──────────────────────────────────────────────────
    if cat == "all":
        return {
            "available_categories": CATEGORIES,
            "atomic_nodes":         _filter(ATOMIC_NODES),
            "library_nodes":        _filter(LIBRARY_NODES),
            "blend_modes":          BLEND_MODES_DOC,
            "port_reference":       PORT_REFERENCE,
            "pbr_outputs":          PBR_OUTPUTS,
            "workflow":             WORKFLOW,
            "concepts":             CONCEPTS,
            "shortcuts":            SHORTCUTS,
            "connection_patterns":  CONNECTION_PATTERNS,
            "node_categories":      NODE_CATEGORIES,
            "parameters":           PARAMETERS_REFERENCE,
            "note": "This is a large response. Use category= to filter: " + ", ".join(CATEGORIES.keys()),
        }

    if cat in ("atomic_nodes", "atomic"):
        return {"category": "atomic_nodes", "count": len(ATOMIC_NODES),
                "data": _filter(ATOMIC_NODES)}

    if cat in ("library_nodes", "library"):
        return {"category": "library_nodes", "count": len(LIBRARY_NODES),
                "data": _filter(LIBRARY_NODES)}

    if cat in ("blend_modes", "blending"):
        return {"category": "blend_modes", "data": BLEND_MODES_DOC}

    if cat in ("port_reference", "ports"):
        return {"category": "port_reference", "data": _filter(PORT_REFERENCE)}

    if cat in ("pbr_outputs", "pbr", "outputs"):
        return {"category": "pbr_outputs", "data": _filter(PBR_OUTPUTS)}

    if cat in ("workflow", "rules"):
        return {"category": "workflow", "data": WORKFLOW}

    if cat in ("concepts", "concept"):
        return {"category": "concepts", "data": _filter(CONCEPTS)}

    if cat in ("shortcuts", "keybindings", "hotkeys"):
        return {"category": "shortcuts", "data": _filter(SHORTCUTS)}

    if cat in ("connection_patterns", "patterns", "chains"):
        return {"category": "connection_patterns", "data": CONNECTION_PATTERNS}

    if cat in ("node_categories", "categories"):
        return {"category": "node_categories", "data": _filter(NODE_CATEGORIES)}

    if cat in ("parameters", "params"):
        return {"category": "parameters", "data": PARAMETERS_REFERENCE}

    # ── Unknown category ───────────────────────────────────────────────────
    return {
        "error": "Unknown category '{}'. Available: {}".format(category, list(CATEGORIES.keys())),
        "available_categories": CATEGORIES,
    }
