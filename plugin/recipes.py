"""
SD MCP Recipe System v5.0 — Professional Grade (pro Architecture)
Based on deep analysis of SubstanceGraph1 (512 nodes, pro / MeshModeler).

=== SubstanceGraph1 Node Type Distribution ===
  275  sbscompgraph_instance  (library nodes — the workhorse)
   80  blend                  (compositing, masking, layering)
   52  passthrough            (signal routing)
   35  levels                 (range remapping at every stage)
   28  directionalwarp        (detail variation — 4× more than warp)
   12  transformation         (tiling, rotation, scale variation)
    9  distance               (gradient from flood_fill boundaries)
    5  normal                 (PBR conversion at output)
    3  warp                   (large-scale displacement)
    2  blur                   (HQ blur for warp maps)

=== Top Library Nodes (by usage in pro graph) ===
   41  clouds_2               (primary noise generator — heavy use)
   26  multi_directional_warp_grayscale  (KEY: replaces simple warp)
   24  edge_detect            (KEY: ridge/cavity mask from shapes)
   23  flood_fill             (KEY: island detection for variation)
   22  slope_blur_grayscale_2 (directional flow along slopes)
   18  flood_fill_to_gradient_2  (gradient per flood-fill island)
   14  blur_hq_grayscale      (smooth maps for warp inputs)
   13  perlin_noise           (secondary noise)
   10  invert_grayscale       (inverts for mask combinations)
    9  crystal_1              (fracture/crack patterns)
    8  non_uniform_blur_grayscale  (anisotropic blur)
    7  flood_fill_to_grayscale    (grayscale variation per island)
    6  histogram_scan         (remap value ranges)
    5  gradient_linear_1      (directional gradients)
    5  tile_sampler           (tile-based patterns)
    5  highpass_grayscale     (detail/micro-surface extraction)

=== Key Connection Patterns (pro signature chains) ===
   38  blend → blend          (additive layering stacks)
   22  levels → blend         (remapped masks into blends)
   18  flood_fill → flood_fill_to_gradient_2  (per-island gradients)
   14  clouds_2 → slope_blur  (noise driven flow)
   14  edge_detect → blend    (edge masks into base)
   13  flood_fill_to_gradient_2 → blend  (gradient-based compositing)
   12  clouds_2 → directionalwarp  (clouds distort shapes)
    8  slope_blur → slope_blur  (cascaded slope blur)
    8  clouds_2 → multi_dir_warp  (clouds drive multi-dir warp)
    8  edge_detect → flood_fill  (edges seed flood fills)
    7  blend → multi_dir_warp  (blended noise into multi-dir warp)
    7  directionalwarp → multi_dir_warp  (cascaded warp)

Library Node Port Reference (confirmed from live SD 15.0.3 analysis):
  --- Noise generators (output="output") ---
  perlin_noise:               inputs=[scale, disorder, non_square_expansion]
  cells_1/cells_2:            inputs=[scale, disorder, non_square_expansion]
  clouds_2:                   inputs=[scale, disorder, non_square_expansion]
  crystal_1:                  inputs=[scale, disorder, non_square_expansion]
  --- Shape generators (output="output") ---
  polygon_2:                  inputs=[Tiling, Sides, Scale, Rotation, Curve, Gradient, InvertGradient]
  gradient_linear_1:          output=Simple_Gradient, inputs=[Tiling, rotation]
  gradient_axial:             output=output, inputs=[point_1, point_2]
  --- Blur/warp operators ---
  blur_hq_grayscale:          output=Blur_HQ,         inputs=[Intensity, Quality, Source]
  slope_blur_grayscale_2:     output=Slope_Blur,      inputs=[Samples, Intensity, mode, Source, Effect]
  non_uniform_blur_grayscale: output=Non_Uniform_Blur, inputs=[Intensity, Anisotropy, Asymmetry, Angle, Samples, Source, Effect]
  multi_directional_warp_grayscale: output=output,    inputs=[intensity, warp_angle, mode, directions, input, intensity_input]
  invert_grayscale:           output=Invert_Grayscale, inputs=[invert, Source]
  highpass_grayscale:         output=Highpass,         inputs=[Radius, Source]
  histogram_scan:             output=Output,           inputs=[Position, Contrast, Invert_Position, Input_1]
  --- Structural operators ---
  edge_detect:                output=output,           inputs=[edge_width, edge_roundness, invert, tolerance, input]
  flood_fill:                 output=output,           inputs=[profile, advanced, profileOverride, mask]
  flood_fill_to_gradient_2:   output=output,           inputs=[angle, angle_variation, input, angle_input, slope_input]
  flood_fill_to_grayscale:    output=output,           inputs=[luminance_adjustement, luminance_random, input, grayscale_input]
  --- Tiling ---
  tile_random:                output=output            inputs=[...]

Atomic Node Port Reference:
  blend:           source (fg), destination (bg), opacity (mask) -> unique_filter_output
  levels:          input1 -> unique_filter_output
  transformation:  input1 -> unique_filter_output
  warp:            input1 (image), inputgradient (warp map) -> unique_filter_output
  directionalwarp: input1 (image), inputintensity (warp map) -> unique_filter_output
  normal:          input1 -> unique_filter_output
  distance:        input1 -> unique_filter_output
  blur:            input1 -> unique_filter_output
  output:          inputNodeOutput (no output)
"""

# ─────────────────────────────────────────────────────────────────────────────
# Library node URL registry (confirmed from SD 15.0.3)
# ─────────────────────────────────────────────────────────────────────────────
LIB = {
    # Noise generators
    "perlin_noise":           "pkg:///perlin_noise?dependency=1563156574",
    "cells_1":                "pkg:///cells_1?dependency=1563150890",
    "cells_2":                "pkg:///cells_2?dependency=1563253418",
    "cells_4":                "pkg:///cells_4?dependency=1299276447",
    "clouds_2":               "pkg:///clouds_2?dependency=1563158662",
    "clouds_1":               "pkg:///clouds_1?dependency=1563662901",
    "crystal_1":              "pkg:///crystal_1?dependency=1563153565",
    "polygon_2":              "pkg:///polygon_2?dependency=1563151369",
    # Gradients
    "gradient_linear_1":      "pkg:///gradient_linear_1?dependency=1563150839",
    "gradient_axial":         "pkg:///gradient_axial?dependency=1563152648",
    # Blur / warp operators
    "blur_hq_grayscale":      "pkg:///blur_hq_grayscale?dependency=1299236171",
    "slope_blur_grayscale_2": "pkg:///slope_blur_grayscale_2?dependency=1563154333",
    "non_uniform_blur_grayscale": "pkg:///non_uniform_blur_grayscale?dependency=1502209989",
    "multi_directional_warp_grayscale": "pkg:///multi_directional_warp_grayscale?dependency=1563187562",
    "invert_grayscale":       "pkg:///invert_grayscale?dependency=1177447620",
    "highpass_grayscale":     "pkg:///highpass_grayscale?dependency=1563447639",
    "histogram_scan":         "pkg:///histogram_scan?dependency=1563254078",
    # Structural / flood-fill chain
    "edge_detect":            "pkg:///edge_detect?dependency=1563645680",
    "flood_fill":             "pkg:///flood_fill?dependency=1323881949",
    "flood_fill_to_gradient_2": "pkg:///flood_fill_to_gradient_2?dependency=1323881949",
    "flood_fill_to_grayscale":  "pkg:///flood_fill_to_grayscale?dependency=1323881949",
    # Tiling
    "tile_random":            "pkg:///tile_random?dependency=1508386588",
}


def _pbr_chain(height_alias, base_color_rgb=(0.5, 0.5, 0.5), roughness=0.7, metallic=0.0,
               shadow_factor=0.55, highlight_factor=1.25):
    """Build the PBR output chain — v2: proper 2-tone color blending via height mask.

    Base Color logic (pro approach):
      shadow_color  = base * shadow_factor   (dark areas: crevices, cavities)
      highlight_color = base * highlight_factor (bright areas: peaks, ridges)
      Blend(highlight_src, shadow_dst, height_mask) → height drives shadow→highlight gradient
      This gives realistic albedo variation matching real materials.

    Roughness: height-modulated — recessed areas are slightly rougher (more scatter).
    AO: height drives ambient occlusion (low height = dark occluded cavities).
    """
    r, g, b = base_color_rgb
    # Shadow color (darker, slightly desaturated for realism)
    sr = min(1.0, r * shadow_factor)
    sg = min(1.0, g * shadow_factor)
    sb = min(1.0, b * shadow_factor)
    # Highlight color (brighter, capped at 1.0)
    hr = min(1.0, r * highlight_factor)
    hg = min(1.0, g * highlight_factor)
    hb = min(1.0, b * highlight_factor)
    # Roughness range: low-roughness materials get more variation (peaks shinier)
    rl = max(0.0, roughness - 0.15)
    rh = min(1.0, roughness + 0.12)
    nodes = [
        {"id_alias": "out_height",    "definition_id": "sbs::compositing::output",  "usage": "height",            "label": "Height",            "position": [2400,    0]},
        {"id_alias": "pbr_normal",    "definition_id": "sbs::compositing::normal",   "position": [2400, -160],     "parameters": {"intensity": 3.5}},
        {"id_alias": "out_normal",    "definition_id": "sbs::compositing::output",  "usage": "normal",            "label": "Normal",            "position": [2600, -160]},
        # Roughness: height-driven (peaks slightly smoother than valleys)
        {"id_alias": "pbr_rough",     "definition_id": "sbs::compositing::levels",   "position": [2400, -320],     "parameters": {
            "levelinlow":   [0.0, 0.0, 0.0, 0.0],
            "levelinhigh":  [1.0, 1.0, 1.0, 1.0],
            "leveloutlow":  [rl,  rl,  rl,  rl],
            "levelouthigh": [rh,  rh,  rh,  rh],
        }},
        {"id_alias": "out_roughness", "definition_id": "sbs::compositing::output",  "usage": "roughness",         "label": "Roughness",         "position": [2600, -320]},
        # AO: recessed areas (low height) = dark; clamp input to lower half so AO is meaningful
        {"id_alias": "pbr_ao",        "definition_id": "sbs::compositing::levels",   "position": [2400, -480],     "parameters": {
            "levelinlow":   [0.0, 0.0, 0.0, 0.0],
            "levelinhigh":  [0.6, 0.6, 0.6, 0.6],
            "leveloutlow":  [0.0, 0.0, 0.0, 0.0],
            "levelouthigh": [1.0, 1.0, 1.0, 1.0],
        }},
        {"id_alias": "out_ao",        "definition_id": "sbs::compositing::output",  "usage": "ambientOcclusion",  "label": "Ambient Occlusion", "position": [2600, -480]},
        {"id_alias": "pbr_metallic",  "definition_id": "sbs::compositing::uniform",  "position": [2400, -640],     "parameters": {"outputcolor": [metallic, metallic, metallic, 1.0]}},
        {"id_alias": "out_metallic",  "definition_id": "sbs::compositing::output",  "usage": "metallic",          "label": "Metallic",          "position": [2600, -640]},
        # Base color — 2-tone: shadow uniform → destination, highlight uniform → source
        # height mask drives the blend: white height = highlight shows, black height = shadow shows
        {"id_alias": "pbr_shadow",    "definition_id": "sbs::compositing::uniform",  "position": [2000, -800],     "parameters": {"outputcolor": [sr, sg, sb, 1.0]}},
        {"id_alias": "pbr_highlight", "definition_id": "sbs::compositing::uniform",  "position": [2000, -960],     "parameters": {"outputcolor": [hr, hg, hb, 1.0]}},
        # Blend highlight (src) over shadow (dst) using height as mask → Copy mode (blendingmode=0)
        {"id_alias": "pbr_color",     "definition_id": "sbs::compositing::blend",    "position": [2200, -880],     "parameters": {"blendingmode": 0, "opacitymult": 1.0}},
        # Slight levels adjustment on basecolor to punch it in
        {"id_alias": "pbr_color_lvl", "definition_id": "sbs::compositing::levels",   "position": [2400, -880],     "parameters": {
            "levelinlow":   [0.0, 0.0, 0.0, 0.0],
            "levelinhigh":  [1.0, 1.0, 1.0, 1.0],
        }},
        {"id_alias": "out_basecolor", "definition_id": "sbs::compositing::output",  "usage": "baseColor",         "label": "Base Color",        "position": [2600, -880]},
    ]
    connections = [
        {"from": height_alias,    "to": "out_height",    "from_output": "unique_filter_output", "to_input": "inputNodeOutput"},
        {"from": height_alias,    "to": "pbr_normal",    "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pbr_normal",    "to": "out_normal",    "from_output": "unique_filter_output", "to_input": "inputNodeOutput"},
        {"from": height_alias,    "to": "pbr_rough",     "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pbr_rough",     "to": "out_roughness", "from_output": "unique_filter_output", "to_input": "inputNodeOutput"},
        {"from": height_alias,    "to": "pbr_ao",        "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pbr_ao",        "to": "out_ao",        "from_output": "unique_filter_output", "to_input": "inputNodeOutput"},
        {"from": "pbr_metallic",  "to": "out_metallic",  "from_output": "unique_filter_output", "to_input": "inputNodeOutput"},
        # 2-tone base color: highlight as source, shadow as destination, height as mask
        {"from": "pbr_highlight", "to": "pbr_color",     "from_output": "unique_filter_output", "to_input": "source"},
        {"from": "pbr_shadow",    "to": "pbr_color",     "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": height_alias,    "to": "pbr_color",     "from_output": "unique_filter_output", "to_input": "opacity"},
        {"from": "pbr_color",     "to": "pbr_color_lvl", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pbr_color_lvl", "to": "out_basecolor", "from_output": "unique_filter_output", "to_input": "inputNodeOutput"},
    ]
    return nodes, connections


def _make_recipe(nodes, connections, height_alias, color, roughness=0.7, metallic=0.0,
                 description="", shadow_factor=0.55, highlight_factor=1.25):
    pbr_nodes, pbr_conns = _pbr_chain(
        height_alias, base_color_rgb=color, roughness=roughness, metallic=metallic,
        shadow_factor=shadow_factor, highlight_factor=highlight_factor)
    return {
        "description": description,
        "nodes": nodes + pbr_nodes,
        "connections": connections + pbr_conns,
        "height_alias": height_alias,
        "color": color,
        "roughness": roughness,
        "metallic": metallic,
    }


# ─────────────────────────────────────────────────────────────────────────────
# WOOD RECIPES
# ─────────────────────────────────────────────────────────────────────────────

def _wood_base_recipe(name, description, perlin_scale=12, perlin_disorder=0.05,
                      warp_intensity=0.3, ring_scale=8, color=(0.42, 0.27, 0.13), roughness=0.75):
    nodes = [
        {"id_alias": "perlin_grain", "resource_url": LIB["perlin_noise"], "position": [-800, 0],
         "parameters": {"scale": {"value": perlin_scale, "type": "int"}, "disorder": {"value": perlin_disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "grain_transform", "definition_id": "sbs::compositing::transformation", "position": [-600, 0],
         "parameters": {"matrix22": [2.0, 0.0, 0.0, 0.25], "offset": [0.0, 0.0]}},
        {"id_alias": "perlin_rings", "resource_url": LIB["perlin_noise"], "position": [-800, 200],
         "parameters": {"scale": {"value": ring_scale, "type": "int"}, "disorder": {"value": 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "grain_blend", "definition_id": "sbs::compositing::blend", "position": [-400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.4}},
        {"id_alias": "ring_levels", "definition_id": "sbs::compositing::levels", "position": [-200, 0],
         "parameters": {"levelinlow": [0.2, 0.2, 0.2, 0.2], "levelinhigh": [0.8, 0.8, 0.8, 0.8]}},
        {"id_alias": "blur_warp_map", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "warp1", "definition_id": "sbs::compositing::warp", "position": [0, 0],
         "parameters": {"intensity": warp_intensity}},
        {"id_alias": "perlin_detail", "resource_url": LIB["perlin_noise"], "position": [200, 200],
         "parameters": {"scale": {"value": 32, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "blur_detail", "resource_url": LIB["blur_hq_grayscale"], "position": [400, 200],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "dir_warp", "definition_id": "sbs::compositing::directionalwarp", "position": [400, 0],
         "parameters": {"intensity": 0.15}},
        {"id_alias": "final_levels", "definition_id": "sbs::compositing::levels", "position": [600, 0],
         "parameters": {"levelinlow": [0.1, 0.1, 0.1, 0.1], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
    ]
    connections = [
        {"from": "perlin_grain", "to": "grain_transform", "from_output": "output", "to_input": "input1"},
        {"from": "perlin_rings", "to": "grain_blend", "from_output": "output", "to_input": "source"},
        {"from": "grain_transform", "to": "grain_blend", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "grain_blend", "to": "ring_levels", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "grain_transform", "to": "blur_warp_map", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "ring_levels", "to": "warp1", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "blur_warp_map", "to": "warp1", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "perlin_detail", "to": "blur_detail", "from_output": "output", "to_input": "Source"},
        {"from": "warp1", "to": "dir_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "blur_detail", "to": "dir_warp", "from_output": "Blur_HQ", "to_input": "inputintensity"},
        {"from": "dir_warp", "to": "final_levels", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "final_levels", color, roughness=roughness, metallic=0.0, description=description)


# ─────────────────────────────────────────────────────────────────────────────
# ROCK RECIPES — pro RockForm01 pattern
# ─────────────────────────────────────────────────────────────────────────────

def _rock_base_recipe(name, description, cells_scale=3, perlin_scale=6, polygon_sides=4,
                      warp_intensity=0.3, slope_samples=12, slope_intensity=0.31,
                      color=(0.38, 0.35, 0.32), roughness=0.85, metallic=0.0):
    nodes = [
        {"id_alias": "rock_polygon", "resource_url": LIB["polygon_2"], "position": [-2000, 0],
         "parameters": {"Tiling": {"value": 1, "type": "int"}, "Sides": {"value": polygon_sides, "type": "int"},
                        "Scale": {"value": 1.0, "type": "float"}, "Rotation": {"value": 0.0, "type": "float"}, "Gradient": {"value": 1.0, "type": "float"}}},
        {"id_alias": "rock_polygon_levels", "definition_id": "sbs::compositing::levels", "position": [-1800, 0],
         "parameters": {"levelinlow": [0.3, 0.3, 0.3, 0.3], "levelinhigh": [0.8, 0.8, 0.8, 0.8]}},
        {"id_alias": "rock_gradient", "resource_url": LIB["gradient_linear_1"], "position": [-1800, -120],
         "parameters": {"Tiling": {"value": 1, "type": "int"}, "rotation": {"value": 0, "type": "int"}}},
        {"id_alias": "rock_base_blend", "definition_id": "sbs::compositing::blend", "position": [-1600, 0],
         "parameters": {"blendingmode": 0, "opacitymult": 0.5}},
        {"id_alias": "rock_cells", "resource_url": LIB["cells_1"], "position": [-1600, -180],
         "parameters": {"scale": {"value": cells_scale, "type": "int"}, "disorder": {"value": 0.18, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "rock_cells_blend", "definition_id": "sbs::compositing::blend", "position": [-1400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.3}},
        {"id_alias": "rock_crystal", "resource_url": LIB["crystal_1"], "position": [-1000, 200],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": 0.0, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "rock_crystal_xform1", "definition_id": "sbs::compositing::transformation", "position": [-800, 200]},
        {"id_alias": "rock_crystal_xform2", "definition_id": "sbs::compositing::transformation", "position": [-600, 400]},
        {"id_alias": "blur_warp1", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 2.9, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "blur_warp2", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 400],
         "parameters": {"Intensity": {"value": 2.66, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "rock_perlin", "resource_url": LIB["perlin_noise"], "position": [-200, 200],
         "parameters": {"scale": {"value": perlin_scale, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "warp1", "definition_id": "sbs::compositing::warp", "position": [-400, 0],
         "parameters": {"intensity": warp_intensity}},
        {"id_alias": "slope_blur1", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": slope_samples, "type": "int"}, "Intensity": {"value": slope_intensity, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "dir_warp", "definition_id": "sbs::compositing::directionalwarp", "position": [100, 0],
         "parameters": {"intensity": 0.2}},
        {"id_alias": "rock_perlin2", "resource_url": LIB["perlin_noise"], "position": [300, 200],
         "parameters": {"scale": {"value": 1, "type": "int"}, "disorder": {"value": 0.0, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "blur_final", "resource_url": LIB["blur_hq_grayscale"], "position": [500, 200],
         "parameters": {"Intensity": {"value": 10.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "warp2", "definition_id": "sbs::compositing::warp", "position": [500, 0],
         "parameters": {"intensity": 0.25}},
        {"id_alias": "slope_blur2", "resource_url": LIB["slope_blur_grayscale_2"], "position": [700, -200],
         "parameters": {"Samples": {"value": 8, "type": "int"}, "Intensity": {"value": 0.43, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "rock_perlin3", "resource_url": LIB["perlin_noise"], "position": [500, -300],
         "parameters": {"scale": {"value": 5, "type": "int"}, "disorder": {"value": 0.0, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "dir_warp2", "definition_id": "sbs::compositing::directionalwarp", "position": [900, 0],
         "parameters": {"intensity": 0.3}},
        {"id_alias": "rock_invert", "resource_url": LIB["invert_grayscale"], "position": [1100, -200],
         "parameters": {"invert": {"value": True, "type": "bool"}}},
        {"id_alias": "rock_final", "definition_id": "sbs::compositing::blend", "position": [1300, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.3}},
    ]
    connections = [
        {"from": "rock_polygon", "to": "rock_polygon_levels", "from_output": "output", "to_input": "input1"},
        {"from": "rock_gradient", "to": "rock_base_blend", "from_output": "Simple_Gradient", "to_input": "source"},
        {"from": "rock_polygon_levels", "to": "rock_base_blend", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "rock_cells", "to": "rock_cells_blend", "from_output": "output", "to_input": "source"},
        {"from": "rock_base_blend", "to": "rock_cells_blend", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "rock_crystal", "to": "rock_crystal_xform1", "from_output": "output", "to_input": "input1"},
        {"from": "rock_crystal", "to": "rock_crystal_xform2", "from_output": "output", "to_input": "input1"},
        {"from": "rock_crystal_xform1", "to": "blur_warp1", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "rock_crystal_xform2", "to": "blur_warp2", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "rock_cells_blend", "to": "warp1", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "blur_warp1", "to": "warp1", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "warp1", "to": "slope_blur1", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "blur_warp2", "to": "slope_blur1", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "slope_blur1", "to": "dir_warp", "from_output": "Slope_Blur", "to_input": "input1"},
        {"from": "rock_perlin", "to": "dir_warp", "from_output": "output", "to_input": "inputintensity"},
        {"from": "rock_perlin2", "to": "blur_final", "from_output": "output", "to_input": "Source"},
        {"from": "dir_warp", "to": "warp2", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "blur_final", "to": "warp2", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "rock_perlin3", "to": "slope_blur2", "from_output": "output", "to_input": "Source"},
        {"from": "rock_perlin3", "to": "slope_blur2", "from_output": "output", "to_input": "Effect"},
        {"from": "slope_blur2", "to": "dir_warp2", "from_output": "Slope_Blur", "to_input": "input1"},
        {"from": "warp2", "to": "dir_warp2", "from_output": "unique_filter_output", "to_input": "inputintensity"},
        {"from": "dir_warp2", "to": "rock_invert", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "rock_invert", "to": "rock_final", "from_output": "Invert_Grayscale", "to_input": "source"},
        {"from": "warp2", "to": "rock_final", "from_output": "unique_filter_output", "to_input": "destination"},
    ]
    return _make_recipe(nodes, connections, "rock_final", color, roughness=roughness, metallic=metallic, description=description)


# ─────────────────────────────────────────────────────────────────────────────
# METAL RECIPES
# ─────────────────────────────────────────────────────────────────────────────

def _metal_base_recipe(name, description, perlin_scale=24, perlin_disorder=0.05,
                       scratch_intensity=0.1, color=(0.7, 0.7, 0.7), roughness=0.3, metallic=1.0):
    nodes = [
        {"id_alias": "metal_perlin", "resource_url": LIB["perlin_noise"], "position": [-800, 0],
         "parameters": {"scale": {"value": perlin_scale, "type": "int"}, "disorder": {"value": perlin_disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "metal_stretch", "definition_id": "sbs::compositing::transformation", "position": [-600, 0],
         "parameters": {"matrix22": [3.0, 0.0, 0.0, 0.1], "offset": [0.0, 0.0]}},
        {"id_alias": "metal_levels1", "definition_id": "sbs::compositing::levels", "position": [-400, 0],
         "parameters": {"levelinlow": [0.35, 0.35, 0.35, 0.35], "levelinhigh": [0.65, 0.65, 0.65, 0.65]}},
        {"id_alias": "metal_detail", "resource_url": LIB["perlin_noise"], "position": [-600, 200],
         "parameters": {"scale": {"value": max(1, perlin_scale * 2), "type": "int"}, "disorder": {"value": 0.02, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "blur_scratch", "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 200],
         "parameters": {"Intensity": {"value": 1.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "metal_dir_warp", "definition_id": "sbs::compositing::directionalwarp", "position": [-200, 0],
         "parameters": {"intensity": scratch_intensity}},
        {"id_alias": "metal_cells", "resource_url": LIB["cells_1"], "position": [0, 200],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": 0.05, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "metal_wear_blend", "definition_id": "sbs::compositing::blend", "position": [0, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.08}},
        {"id_alias": "metal_final", "definition_id": "sbs::compositing::levels", "position": [200, 0],
         "parameters": {"levelinlow": [0.05, 0.05, 0.05, 0.05], "levelinhigh": [0.95, 0.95, 0.95, 0.95],
                        "leveloutlow": [0.3, 0.3, 0.3, 0.3], "levelouthigh": [0.9, 0.9, 0.9, 0.9]}},
    ]
    connections = [
        {"from": "metal_perlin", "to": "metal_stretch", "from_output": "output", "to_input": "input1"},
        {"from": "metal_stretch", "to": "metal_levels1", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "metal_detail", "to": "blur_scratch", "from_output": "output", "to_input": "Source"},
        {"from": "metal_levels1", "to": "metal_dir_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "blur_scratch", "to": "metal_dir_warp", "from_output": "Blur_HQ", "to_input": "inputintensity"},
        {"from": "metal_cells", "to": "metal_wear_blend", "from_output": "output", "to_input": "source"},
        {"from": "metal_dir_warp", "to": "metal_wear_blend", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "metal_wear_blend", "to": "metal_final", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "metal_final", color, roughness=roughness, metallic=metallic, description=description)


# ─────────────────────────────────────────────────────────────────────────────
# ORGANIC RECIPES
# ─────────────────────────────────────────────────────────────────────────────

def _organic_base_recipe(name, description, clouds_scale=4, clouds_disorder=0.5,
                         cells_scale=6, cells_disorder=0.3, blend_weight=0.5,
                         detail_perlin_scale=16, slope_samples=8, slope_intensity=0.4,
                         color=(0.25, 0.45, 0.15), roughness=0.9, metallic=0.0):
    nodes = [
        {"id_alias": "org_clouds", "resource_url": LIB["clouds_2"], "position": [-800, 0],
         "parameters": {"scale": {"value": clouds_scale, "type": "int"}, "disorder": {"value": clouds_disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "org_cells", "resource_url": LIB["cells_1"], "position": [-800, 200],
         "parameters": {"scale": {"value": cells_scale, "type": "int"}, "disorder": {"value": cells_disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "org_blend1", "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 0, "opacitymult": blend_weight}},
        {"id_alias": "org_perlin", "resource_url": LIB["perlin_noise"], "position": [-400, 200],
         "parameters": {"scale": {"value": detail_perlin_scale, "type": "int"}, "disorder": {"value": 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "org_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-200, 200],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "org_warp", "definition_id": "sbs::compositing::warp", "position": [-400, 0],
         "parameters": {"intensity": 0.25}},
        {"id_alias": "org_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": slope_samples, "type": "int"}, "Intensity": {"value": slope_intensity, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "org_final", "definition_id": "sbs::compositing::levels", "position": [0, 0],
         "parameters": {"levelinlow": [0.1, 0.1, 0.1, 0.1], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
    ]
    connections = [
        {"from": "org_cells", "to": "org_blend1", "from_output": "output", "to_input": "source"},
        {"from": "org_clouds", "to": "org_blend1", "from_output": "output", "to_input": "destination"},
        {"from": "org_perlin", "to": "org_blur", "from_output": "output", "to_input": "Source"},
        {"from": "org_blend1", "to": "org_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "org_blur", "to": "org_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "org_warp", "to": "org_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "org_blur", "to": "org_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "org_slope", "to": "org_final", "from_output": "Slope_Blur", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "org_final", color, roughness=roughness, metallic=metallic, description=description)


# ─────────────────────────────────────────────────────────────────────────────
# WATER / ICE RECIPES
# ─────────────────────────────────────────────────────────────────────────────

def _water_recipe(description, color, roughness, metallic=0.0):
    nodes = [
        {"id_alias": "water_base", "resource_url": LIB["perlin_noise"], "position": [-800, 0],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "water_ripple", "resource_url": LIB["perlin_noise"], "position": [-800, 200],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "water_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 5.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "water_warp", "definition_id": "sbs::compositing::warp", "position": [-600, 0],
         "parameters": {"intensity": 0.5}},
        {"id_alias": "water_levels", "definition_id": "sbs::compositing::levels", "position": [-400, 0],
         "parameters": {"levelinlow": [0.35, 0.35, 0.35, 0.35], "levelinhigh": [0.65, 0.65, 0.65, 0.65],
                        "leveloutlow": [0.4, 0.4, 0.4, 0.4], "levelouthigh": [0.7, 0.7, 0.7, 0.7]}},
        {"id_alias": "water_ripple_fine", "resource_url": LIB["perlin_noise"], "position": [-400, 200],
         "parameters": {"scale": {"value": 32, "type": "int"}, "disorder": {"value": 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "water_blend_final", "definition_id": "sbs::compositing::blend", "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.15}},
        {"id_alias": "water_final", "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    connections = [
        {"from": "water_ripple", "to": "water_blur", "from_output": "output", "to_input": "Source"},
        {"from": "water_base", "to": "water_warp", "from_output": "output", "to_input": "input1"},
        {"from": "water_blur", "to": "water_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "water_warp", "to": "water_levels", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "water_ripple_fine", "to": "water_blend_final", "from_output": "output", "to_input": "source"},
        {"from": "water_levels", "to": "water_blend_final", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "water_blend_final", "to": "water_final", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "water_final", color, roughness=roughness, metallic=metallic, description=description)


def _ice_recipe(description, color, roughness, metallic=0.0):
    nodes = [
        {"id_alias": "ice_crystal", "resource_url": LIB["crystal_1"], "position": [-800, 0],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": 0.15, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ice_cells", "resource_url": LIB["cells_1"], "position": [-800, 200],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ice_blend1", "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.4}},
        {"id_alias": "ice_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "ice_warp", "definition_id": "sbs::compositing::warp", "position": [-400, 0],
         "parameters": {"intensity": 0.12}},
        {"id_alias": "ice_perlin", "resource_url": LIB["perlin_noise"], "position": [-200, 200],
         "parameters": {"scale": {"value": 12, "type": "int"}, "disorder": {"value": 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ice_detail_blend", "definition_id": "sbs::compositing::blend", "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.1}},
        {"id_alias": "ice_final", "definition_id": "sbs::compositing::levels", "position": [0, 0],
         "parameters": {"levelinlow": [0.2, 0.2, 0.2, 0.2], "levelinhigh": [0.85, 0.85, 0.85, 0.85],
                        "leveloutlow": [0.5, 0.5, 0.5, 0.5], "levelouthigh": [1.0, 1.0, 1.0, 1.0]}},
    ]
    connections = [
        {"from": "ice_cells", "to": "ice_blend1", "from_output": "output", "to_input": "source"},
        {"from": "ice_crystal", "to": "ice_blend1", "from_output": "output", "to_input": "destination"},
        {"from": "ice_cells", "to": "ice_blur", "from_output": "output", "to_input": "Source"},
        {"from": "ice_blend1", "to": "ice_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "ice_blur", "to": "ice_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "ice_perlin", "to": "ice_detail_blend", "from_output": "output", "to_input": "source"},
        {"from": "ice_warp", "to": "ice_detail_blend", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "ice_detail_blend", "to": "ice_final", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "ice_final", color, roughness=roughness, metallic=metallic, description=description)


# ─────────────────────────────────────────────────────────────────────────────
# GEM RECIPES
# ─────────────────────────────────────────────────────────────────────────────

def _gem_recipe(description, color, roughness=0.05, metallic=0.0):
    nodes = [
        {"id_alias": "gem_crystal", "resource_url": LIB["crystal_1"], "position": [-800, 0],
         "parameters": {"scale": {"value": 6, "type": "int"}, "disorder": {"value": 0.05, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "gem_polygon", "resource_url": LIB["polygon_2"], "position": [-800, 200],
         "parameters": {"Tiling": {"value": 1, "type": "int"}, "Sides": {"value": 6, "type": "int"},
                        "Scale": {"value": 0.9, "type": "float"}, "Gradient": {"value": 1.0, "type": "float"}}},
        {"id_alias": "gem_blend", "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.5}},
        {"id_alias": "gem_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 1.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "gem_warp", "definition_id": "sbs::compositing::warp", "position": [-400, 0],
         "parameters": {"intensity": 0.08}},
        {"id_alias": "gem_final", "definition_id": "sbs::compositing::levels", "position": [-200, 0],
         "parameters": {"levelinlow": [0.3, 0.3, 0.3, 0.3], "levelinhigh": [0.9, 0.9, 0.9, 0.9],
                        "leveloutlow": [0.6, 0.6, 0.6, 0.6], "levelouthigh": [1.0, 1.0, 1.0, 1.0]}},
    ]
    connections = [
        {"from": "gem_polygon", "to": "gem_blend", "from_output": "output", "to_input": "source"},
        {"from": "gem_crystal", "to": "gem_blend", "from_output": "output", "to_input": "destination"},
        {"from": "gem_crystal", "to": "gem_blur", "from_output": "output", "to_input": "Source"},
        {"from": "gem_blend", "to": "gem_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "gem_blur", "to": "gem_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "gem_warp", "to": "gem_final", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "gem_final", color, roughness=roughness, metallic=metallic, description=description)


# ─────────────────────────────────────────────────────────────────────────────
# SOIL RECIPES
# ─────────────────────────────────────────────────────────────────────────────

def _soil_base_recipe(description, color, roughness=0.92, metallic=0.0,
                      clouds_scale=3, cells_scale=8, disorder=0.5, crack_intensity=0.35):
    nodes = [
        {"id_alias": "soil_clouds", "resource_url": LIB["clouds_2"], "position": [-800, 0],
         "parameters": {"scale": {"value": clouds_scale, "type": "int"}, "disorder": {"value": disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "soil_cells", "resource_url": LIB["cells_2"], "position": [-800, 200],
         "parameters": {"scale": {"value": cells_scale, "type": "int"}, "disorder": {"value": disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "soil_blend", "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.4}},
        {"id_alias": "soil_perlin", "resource_url": LIB["perlin_noise"], "position": [-400, 200],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "soil_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-200, 200],
         "parameters": {"Intensity": {"value": 3.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "soil_warp", "definition_id": "sbs::compositing::warp", "position": [-400, 0],
         "parameters": {"intensity": crack_intensity}},
        {"id_alias": "soil_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": 6, "type": "int"}, "Intensity": {"value": 0.3, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "soil_final", "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    connections = [
        {"from": "soil_cells", "to": "soil_blend", "from_output": "output", "to_input": "source"},
        {"from": "soil_clouds", "to": "soil_blend", "from_output": "output", "to_input": "destination"},
        {"from": "soil_perlin", "to": "soil_blur", "from_output": "output", "to_input": "Source"},
        {"from": "soil_blend", "to": "soil_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "soil_blur", "to": "soil_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "soil_warp", "to": "soil_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "soil_blur", "to": "soil_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "soil_slope", "to": "soil_final", "from_output": "Slope_Blur", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "soil_final", color, roughness=roughness, metallic=metallic, description=description)


# ─────────────────────────────────────────────────────────────────────────────
# CONCRETE RECIPE — multi-pass warp + crack network
# ─────────────────────────────────────────────────────────────────────────────

def _concrete_recipe(description, color=(0.52, 0.50, 0.48), roughness=0.88, metallic=0.0,
                     crack_intensity=0.4, detail_scale=16, disorder=0.4):
    """Concrete: large Voronoi cells → crack warping → fine perlin surface detail.
    Uses 3 warp passes for multi-scale detail typical of poured concrete.
    """
    nodes = [
        # Layer 1: large cell structure (aggregate distribution)
        {"id_alias": "cc_cells_lg",  "resource_url": LIB["cells_2"],          "position": [-1400, 0],
         "parameters": {"scale": {"value": 3, "type": "int"}, "disorder": {"value": disorder * 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cc_lvl_lg",    "definition_id": "sbs::compositing::levels", "position": [-1200, 0],
         "parameters": {"levelinlow": [0.3, 0.3, 0.3, 0.3], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
        # Layer 2: perlin macro variation
        {"id_alias": "cc_perlin_macro", "resource_url": LIB["perlin_noise"],  "position": [-1400, 200],
         "parameters": {"scale": {"value": 2, "type": "int"}, "disorder": {"value": disorder * 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cc_blur_macro", "resource_url": LIB["blur_hq_grayscale"], "position": [-1200, 200],
         "parameters": {"Intensity": {"value": 8.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        # Blend large cell + macro perlin
        {"id_alias": "cc_blend1",    "definition_id": "sbs::compositing::blend",  "position": [-1000, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.3}},
        # Warp pass 1 — large-scale deformation (crack seed)
        {"id_alias": "cc_perlin_w1", "resource_url": LIB["perlin_noise"],    "position": [-1000, 300],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cc_blur_w1",   "resource_url": LIB["blur_hq_grayscale"], "position": [-800, 300],
         "parameters": {"Intensity": {"value": 5.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "cc_warp1",     "definition_id": "sbs::compositing::warp",   "position": [-800, 0],
         "parameters": {"intensity": crack_intensity * 0.6}},
        # Crack pattern — cells_2 at medium scale for crack network
        {"id_alias": "cc_cells_md",  "resource_url": LIB["cells_2"],          "position": [-600, 300],
         "parameters": {"scale": {"value": 6, "type": "int"}, "disorder": {"value": disorder * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cc_slope1",    "resource_url": LIB["slope_blur_grayscale_2"], "position": [-600, 0],
         "parameters": {"Samples": {"value": 10, "type": "int"}, "Intensity": {"value": 0.35, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        # Warp pass 2 — crack sharpening
        {"id_alias": "cc_blur_w2",   "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 300],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "cc_warp2",     "definition_id": "sbs::compositing::warp",   "position": [-400, 0],
         "parameters": {"intensity": crack_intensity * 0.4}},
        # Fine surface detail — small perlin for concrete grain/pores
        {"id_alias": "cc_perlin_fine", "resource_url": LIB["perlin_noise"],  "position": [-200, 300],
         "parameters": {"scale": {"value": detail_scale, "type": "int"}, "disorder": {"value": disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cc_blend2",    "definition_id": "sbs::compositing::blend",  "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.18}},
        # Warp pass 3 — final micro-deformation for surface realism
        {"id_alias": "cc_blur_w3",   "resource_url": LIB["blur_hq_grayscale"], "position": [0, 300],
         "parameters": {"Intensity": {"value": 1.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "cc_warp3",     "definition_id": "sbs::compositing::warp",   "position": [0, 0],
         "parameters": {"intensity": 0.08}},
        {"id_alias": "cc_final",     "definition_id": "sbs::compositing::levels", "position": [200, 0],
         "parameters": {"levelinlow": [0.1, 0.1, 0.1, 0.1], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
    ]
    connections = [
        {"from": "cc_cells_lg",     "to": "cc_lvl_lg",   "from_output": "output",             "to_input": "input1"},
        {"from": "cc_perlin_macro", "to": "cc_blur_macro","from_output": "output",             "to_input": "Source"},
        {"from": "cc_perlin_macro", "to": "cc_blend1",    "from_output": "output",             "to_input": "source"},
        {"from": "cc_lvl_lg",       "to": "cc_blend1",    "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "cc_perlin_w1",    "to": "cc_blur_w1",   "from_output": "output",             "to_input": "Source"},
        {"from": "cc_blend1",       "to": "cc_warp1",     "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "cc_blur_w1",      "to": "cc_warp1",     "from_output": "Blur_HQ",            "to_input": "inputgradient"},
        {"from": "cc_warp1",        "to": "cc_slope1",    "from_output": "unique_filter_output","to_input": "Source"},
        {"from": "cc_cells_md",     "to": "cc_slope1",    "from_output": "output",             "to_input": "Effect"},
        {"from": "cc_cells_md",     "to": "cc_blur_w2",   "from_output": "output",             "to_input": "Source"},
        {"from": "cc_slope1",       "to": "cc_warp2",     "from_output": "Slope_Blur",         "to_input": "input1"},
        {"from": "cc_blur_w2",      "to": "cc_warp2",     "from_output": "Blur_HQ",            "to_input": "inputgradient"},
        {"from": "cc_perlin_fine",  "to": "cc_blend2",    "from_output": "output",             "to_input": "source"},
        {"from": "cc_warp2",        "to": "cc_blend2",    "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "cc_perlin_fine",  "to": "cc_blur_w3",   "from_output": "output",             "to_input": "Source"},
        {"from": "cc_blend2",       "to": "cc_warp3",     "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "cc_blur_w3",      "to": "cc_warp3",     "from_output": "Blur_HQ",            "to_input": "inputgradient"},
        {"from": "cc_warp3",        "to": "cc_final",     "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "cc_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.45, highlight_factor=1.15)


# ─────────────────────────────────────────────────────────────────────────────
# BRICK RECIPE — tile pattern + mortar cracks + surface variation
# ─────────────────────────────────────────────────────────────────────────────

def _brick_recipe(description, color=(0.58, 0.30, 0.18), roughness=0.85, metallic=0.0,
                  brick_scale=4, mortar_width=0.08, disorder=0.3):
    """Brick: polygon tiles → mortar gaps via levels → surface perlin texture.
    Multi-pass: polygon base → slope-blur for mortar → warp + detail perlin → final blend.
    """
    nodes = [
        # Brick tile shape from polygon_2
        {"id_alias": "br_poly",      "resource_url": LIB["polygon_2"],         "position": [-1600, 0],
         "parameters": {"Tiling": {"value": brick_scale, "type": "int"}, "Sides": {"value": 4, "type": "int"},
                        "Scale": {"value": 0.92, "type": "float"}, "Rotation": {"value": 0.0, "type": "float"},
                        "Gradient": {"value": 1.0, "type": "float"}}},
        # Stretch horizontally for brick aspect ratio (2:1)
        {"id_alias": "br_stretch",   "definition_id": "sbs::compositing::transformation", "position": [-1400, 0],
         "parameters": {"matrix22": [2.0, 0.0, 0.0, 1.0]}},
        # Clamp to binary brick/mortar via levels
        {"id_alias": "br_lvl_mortar","definition_id": "sbs::compositing::levels", "position": [-1200, 0],
         "parameters": {"levelinlow": [mortar_width, mortar_width, mortar_width, mortar_width],
                        "levelinhigh": [mortar_width + 0.1, mortar_width + 0.1, mortar_width + 0.1, mortar_width + 0.1],
                        "leveloutlow": [0.0, 0.0, 0.0, 0.0], "levelouthigh": [1.0, 1.0, 1.0, 1.0]}},
        # Slope-blur for mortar groove depth
        {"id_alias": "br_perlin_mb", "resource_url": LIB["perlin_noise"],      "position": [-1200, 200],
         "parameters": {"scale": {"value": 24, "type": "int"}, "disorder": {"value": disorder * 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "br_blur_mb",   "resource_url": LIB["blur_hq_grayscale"], "position": [-1000, 200],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "br_slope1",    "resource_url": LIB["slope_blur_grayscale_2"], "position": [-1000, 0],
         "parameters": {"Samples": {"value": 8, "type": "int"}, "Intensity": {"value": 0.4, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        # Warp pass 1 — brick edge irregularity (hand-laid variation)
        {"id_alias": "br_perlin_w1", "resource_url": LIB["perlin_noise"],      "position": [-800, 300],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "br_blur_w1",   "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 300],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "br_warp1",     "definition_id": "sbs::compositing::warp",   "position": [-800, 0],
         "parameters": {"intensity": disorder * 0.3}},
        # Surface detail — clouds for fired clay texture variation
        {"id_alias": "br_clouds",    "resource_url": LIB["clouds_2"],          "position": [-600, 200],
         "parameters": {"scale": {"value": 6, "type": "int"}, "disorder": {"value": disorder * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "br_perlin_surf","resource_url": LIB["perlin_noise"],     "position": [-400, 200],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        # Blend surface textures together
        {"id_alias": "br_blend_surf","definition_id": "sbs::compositing::blend",   "position": [-400, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.25}},
        # Warp pass 2 — surface micro-variation
        {"id_alias": "br_blur_w2",   "resource_url": LIB["blur_hq_grayscale"], "position": [-200, 300],
         "parameters": {"Intensity": {"value": 1.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "br_warp2",     "definition_id": "sbs::compositing::warp",   "position": [-200, 0],
         "parameters": {"intensity": 0.06}},
        {"id_alias": "br_final",     "definition_id": "sbs::compositing::levels", "position": [0, 0],
         "parameters": {"levelinlow": [0.05, 0.05, 0.05, 0.05], "levelinhigh": [0.95, 0.95, 0.95, 0.95]}},
    ]
    connections = [
        {"from": "br_poly",       "to": "br_stretch",    "from_output": "output",             "to_input": "input1"},
        {"from": "br_stretch",    "to": "br_lvl_mortar", "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "br_perlin_mb",  "to": "br_blur_mb",    "from_output": "output",             "to_input": "Source"},
        {"from": "br_lvl_mortar", "to": "br_slope1",     "from_output": "unique_filter_output","to_input": "Source"},
        {"from": "br_blur_mb",    "to": "br_slope1",     "from_output": "Blur_HQ",            "to_input": "Effect"},
        {"from": "br_perlin_w1",  "to": "br_blur_w1",    "from_output": "output",             "to_input": "Source"},
        {"from": "br_slope1",     "to": "br_warp1",      "from_output": "Slope_Blur",         "to_input": "input1"},
        {"from": "br_blur_w1",    "to": "br_warp1",      "from_output": "Blur_HQ",            "to_input": "inputgradient"},
        {"from": "br_clouds",     "to": "br_blend_surf", "from_output": "output",             "to_input": "source"},
        {"from": "br_warp1",      "to": "br_blend_surf", "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "br_perlin_surf","to": "br_blend_surf", "from_output": "output",             "to_input": "opacity"},
        {"from": "br_perlin_surf","to": "br_blur_w2",    "from_output": "output",             "to_input": "Source"},
        {"from": "br_blend_surf", "to": "br_warp2",      "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "br_blur_w2",    "to": "br_warp2",      "from_output": "Blur_HQ",            "to_input": "inputgradient"},
        {"from": "br_warp2",      "to": "br_final",      "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "br_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.40, highlight_factor=1.20)


# ─────────────────────────────────────────────────────────────────────────────
# LAVA RECIPE — glowing crack network with cooling crust
# ─────────────────────────────────────────────────────────────────────────────

def _lava_recipe(description, color=(0.12, 0.06, 0.04), roughness=0.92, metallic=0.0):
    """Lava: cells_2 crack network → slope-blur for flow lines → 4 warp passes.
    Dark crust with glowing crack channels (height inversely drives albedo in PBR).
    """
    nodes = [
        # Macro crust blocks from cells_1
        {"id_alias": "lv_cells_crust",  "resource_url": LIB["cells_1"],     "position": [-1600, 0],
         "parameters": {"scale": {"value": 3, "type": "int"}, "disorder": {"value": 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "lv_lvl_crust",    "definition_id": "sbs::compositing::levels", "position": [-1400, 0],
         "parameters": {"levelinlow": [0.2, 0.2, 0.2, 0.2], "levelinhigh": [0.85, 0.85, 0.85, 0.85]}},
        # Crack channels from cells_2
        {"id_alias": "lv_cells_crack",  "resource_url": LIB["cells_2"],     "position": [-1600, 200],
         "parameters": {"scale": {"value": 5, "type": "int"}, "disorder": {"value": 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        # Slope-blur to create flow lines along crack edges
        {"id_alias": "lv_perlin_flow",  "resource_url": LIB["perlin_noise"], "position": [-1400, 300],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "lv_blur_flow",    "resource_url": LIB["blur_hq_grayscale"], "position": [-1200, 300],
         "parameters": {"Intensity": {"value": 4.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "lv_slope1",       "resource_url": LIB["slope_blur_grayscale_2"], "position": [-1200, 0],
         "parameters": {"Samples": {"value": 14, "type": "int"}, "Intensity": {"value": 0.5, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        # Blend crust levels into flow
        {"id_alias": "lv_blend1",       "definition_id": "sbs::compositing::blend", "position": [-1000, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.5}},
        # Warp pass 1 — macro lava flow deformation
        {"id_alias": "lv_perlin_w1",    "resource_url": LIB["perlin_noise"], "position": [-1000, 300],
         "parameters": {"scale": {"value": 2, "type": "int"}, "disorder": {"value": 0.25, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "lv_blur_w1",      "resource_url": LIB["blur_hq_grayscale"], "position": [-800, 300],
         "parameters": {"Intensity": {"value": 6.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "lv_warp1",        "definition_id": "sbs::compositing::warp",   "position": [-800, 0],
         "parameters": {"intensity": 0.5}},
        # Slope blur 2 — directional cooling crust texture
        {"id_alias": "lv_slope2",       "resource_url": LIB["slope_blur_grayscale_2"], "position": [-600, 0],
         "parameters": {"Samples": {"value": 10, "type": "int"}, "Intensity": {"value": 0.38, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        # Warp pass 2 — medium-scale fracturing
        {"id_alias": "lv_perlin_w2",    "resource_url": LIB["perlin_noise"], "position": [-600, 300],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "lv_blur_w2",      "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 300],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "lv_warp2",        "definition_id": "sbs::compositing::warp",   "position": [-400, 0],
         "parameters": {"intensity": 0.25}},
        # Fine surface detail — crystal_1 for cooled basalt
        {"id_alias": "lv_crystal",      "resource_url": LIB["crystal_1"],    "position": [-200, 300],
         "parameters": {"scale": {"value": 12, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "lv_blend2",       "definition_id": "sbs::compositing::blend", "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.12}},
        # Warp pass 3 — cooling contraction micro-cracks
        {"id_alias": "lv_blur_w3",      "resource_url": LIB["blur_hq_grayscale"], "position": [0, 300],
         "parameters": {"Intensity": {"value": 1.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "lv_warp3",        "definition_id": "sbs::compositing::warp",   "position": [0, 0],
         "parameters": {"intensity": 0.12}},
        {"id_alias": "lv_final",        "definition_id": "sbs::compositing::levels", "position": [200, 0],
         "parameters": {"levelinlow": [0.05, 0.05, 0.05, 0.05], "levelinhigh": [0.95, 0.95, 0.95, 0.95],
                        "leveloutlow": [0.0, 0.0, 0.0, 0.0], "levelouthigh": [0.85, 0.85, 0.85, 0.85]}},
    ]
    connections = [
        {"from": "lv_cells_crust", "to": "lv_lvl_crust", "from_output": "output",              "to_input": "input1"},
        {"from": "lv_perlin_flow", "to": "lv_blur_flow",  "from_output": "output",              "to_input": "Source"},
        {"from": "lv_cells_crack", "to": "lv_slope1",     "from_output": "output",              "to_input": "Source"},
        {"from": "lv_blur_flow",   "to": "lv_slope1",     "from_output": "Blur_HQ",             "to_input": "Effect"},
        {"from": "lv_lvl_crust",   "to": "lv_blend1",     "from_output": "unique_filter_output","to_input": "source"},
        {"from": "lv_slope1",      "to": "lv_blend1",     "from_output": "Slope_Blur",          "to_input": "destination"},
        {"from": "lv_perlin_w1",   "to": "lv_blur_w1",    "from_output": "output",              "to_input": "Source"},
        {"from": "lv_blend1",      "to": "lv_warp1",      "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "lv_blur_w1",     "to": "lv_warp1",      "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "lv_warp1",       "to": "lv_slope2",     "from_output": "unique_filter_output","to_input": "Source"},
        {"from": "lv_blur_w1",     "to": "lv_slope2",     "from_output": "Blur_HQ",             "to_input": "Effect"},
        {"from": "lv_perlin_w2",   "to": "lv_blur_w2",    "from_output": "output",              "to_input": "Source"},
        {"from": "lv_slope2",      "to": "lv_warp2",      "from_output": "Slope_Blur",          "to_input": "input1"},
        {"from": "lv_blur_w2",     "to": "lv_warp2",      "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "lv_crystal",     "to": "lv_blend2",     "from_output": "output",              "to_input": "source"},
        {"from": "lv_warp2",       "to": "lv_blend2",     "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "lv_crystal",     "to": "lv_blur_w3",    "from_output": "output",              "to_input": "Source"},
        {"from": "lv_blend2",      "to": "lv_warp3",      "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "lv_blur_w3",     "to": "lv_warp3",      "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "lv_warp3",       "to": "lv_final",      "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "lv_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.3, highlight_factor=1.8)


# ─────────────────────────────────────────────────────────────────────────────
# ASPHALT RECIPE — aggregate + bitumen + wear pattern
# ─────────────────────────────────────────────────────────────────────────────

def _asphalt_recipe(description, color=(0.18, 0.17, 0.16), roughness=0.90, metallic=0.0,
                    aggregate_scale=8, wear=0.3):
    """Asphalt: cells aggregate → perlin binder matrix → slope-blur for paving marks.
    3 warp passes for aggregate displacement and surface wear variation.
    """
    nodes = [
        # Aggregate distribution (pebbles/gravel embedded in bitumen)
        {"id_alias": "ap_cells_agg",  "resource_url": LIB["cells_1"],     "position": [-1400, 0],
         "parameters": {"scale": {"value": aggregate_scale, "type": "int"}, "disorder": {"value": 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ap_lvl_agg",    "definition_id": "sbs::compositing::levels", "position": [-1200, 0],
         "parameters": {"levelinlow": [0.4, 0.4, 0.4, 0.4], "levelinhigh": [0.85, 0.85, 0.85, 0.85]}},
        # Bitumen macro variation
        {"id_alias": "ap_perlin_mac", "resource_url": LIB["perlin_noise"], "position": [-1400, 200],
         "parameters": {"scale": {"value": 3, "type": "int"}, "disorder": {"value": 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ap_blur_mac",   "resource_url": LIB["blur_hq_grayscale"], "position": [-1200, 200],
         "parameters": {"Intensity": {"value": 6.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "ap_blend_base", "definition_id": "sbs::compositing::blend", "position": [-1000, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.35}},
        # Warp 1 — aggregate displacement
        {"id_alias": "ap_perlin_w1",  "resource_url": LIB["perlin_noise"], "position": [-1000, 300],
         "parameters": {"scale": {"value": 6, "type": "int"}, "disorder": {"value": 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ap_blur_w1",    "resource_url": LIB["blur_hq_grayscale"], "position": [-800, 300],
         "parameters": {"Intensity": {"value": 2.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "ap_warp1",      "definition_id": "sbs::compositing::warp",   "position": [-800, 0],
         "parameters": {"intensity": 0.12}},
        # Slope-blur for tyre track / compression direction
        {"id_alias": "ap_slope1",     "resource_url": LIB["slope_blur_grayscale_2"], "position": [-600, 0],
         "parameters": {"Samples": {"value": 12, "type": "int"}, "Intensity": {"value": 0.25, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        # Wear / aging — clouds for surface weathering
        {"id_alias": "ap_clouds",     "resource_url": LIB["clouds_2"],    "position": [-600, 300],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": wear, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ap_blend_wear", "definition_id": "sbs::compositing::blend", "position": [-400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": wear * 0.25}},
        # Warp 2 — surface irregularity
        {"id_alias": "ap_perlin_fine","resource_url": LIB["perlin_noise"], "position": [-400, 300],
         "parameters": {"scale": {"value": 24, "type": "int"}, "disorder": {"value": 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ap_blur_w2",    "resource_url": LIB["blur_hq_grayscale"], "position": [-200, 300],
         "parameters": {"Intensity": {"value": 1.2, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "ap_warp2",      "definition_id": "sbs::compositing::warp",   "position": [-200, 0],
         "parameters": {"intensity": 0.06}},
        {"id_alias": "ap_final",      "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    connections = [
        {"from": "ap_cells_agg",  "to": "ap_lvl_agg",    "from_output": "output",              "to_input": "input1"},
        {"from": "ap_perlin_mac", "to": "ap_blur_mac",    "from_output": "output",              "to_input": "Source"},
        {"from": "ap_perlin_mac", "to": "ap_blend_base",  "from_output": "output",              "to_input": "source"},
        {"from": "ap_lvl_agg",    "to": "ap_blend_base",  "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "ap_perlin_w1",  "to": "ap_blur_w1",     "from_output": "output",              "to_input": "Source"},
        {"from": "ap_blend_base", "to": "ap_warp1",       "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "ap_blur_w1",    "to": "ap_warp1",       "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "ap_warp1",      "to": "ap_slope1",      "from_output": "unique_filter_output","to_input": "Source"},
        {"from": "ap_blur_mac",   "to": "ap_slope1",      "from_output": "Blur_HQ",             "to_input": "Effect"},
        {"from": "ap_clouds",     "to": "ap_blend_wear",  "from_output": "output",              "to_input": "source"},
        {"from": "ap_slope1",     "to": "ap_blend_wear",  "from_output": "Slope_Blur",          "to_input": "destination"},
        {"from": "ap_perlin_fine","to": "ap_blur_w2",     "from_output": "output",              "to_input": "Source"},
        {"from": "ap_blend_wear", "to": "ap_warp2",       "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "ap_blur_w2",    "to": "ap_warp2",       "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "ap_warp2",      "to": "ap_final",       "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "ap_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.35, highlight_factor=1.10)


# ─────────────────────────────────────────────────────────────────────────────
# PLASTER RECIPE — smooth base + micro-surface + crack details
# ─────────────────────────────────────────────────────────────────────────────

def _plaster_recipe(description, color=(0.88, 0.85, 0.80), roughness=0.70, metallic=0.0,
                    crack_density=0.3, smoothness=0.8):
    """Plaster: smooth perlin base → fine cells for surface pitting → micro-cracks via slope-blur.
    2 warp passes keep surface smooth with subtle irregularity.
    """
    nodes = [
        # Smooth base — large low-disorder perlin
        {"id_alias": "pl_perlin_base","resource_url": LIB["perlin_noise"],  "position": [-1200, 0],
         "parameters": {"scale": {"value": 2, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pl_blur_base",  "resource_url": LIB["blur_hq_grayscale"], "position": [-1000, 0],
         "parameters": {"Intensity": {"value": 12.0 * smoothness, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pl_lvl_base",   "definition_id": "sbs::compositing::levels", "position": [-800, 0],
         "parameters": {"levelinlow": [0.35, 0.35, 0.35, 0.35], "levelinhigh": [0.65, 0.65, 0.65, 0.65],
                        "leveloutlow": [0.4, 0.4, 0.4, 0.4], "levelouthigh": [0.75, 0.75, 0.75, 0.75]}},
        # Surface pitting — fine cells
        {"id_alias": "pl_cells_pit",  "resource_url": LIB["cells_1"],      "position": [-1200, 250],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pl_blend_pit",  "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 1, "opacitymult": (1.0 - smoothness) * 0.15}},
        # Warp 1 — plaster trowel marks (directional)
        {"id_alias": "pl_perlin_w1",  "resource_url": LIB["perlin_noise"],  "position": [-600, 300],
         "parameters": {"scale": {"value": 6, "type": "int"}, "disorder": {"value": crack_density * 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pl_blur_w1",    "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 300],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pl_warp1",      "definition_id": "sbs::compositing::warp",   "position": [-400, 0],
         "parameters": {"intensity": 0.08}},
        # Micro-cracks via cells_2 + slope-blur
        {"id_alias": "pl_cells_crack","resource_url": LIB["cells_2"],      "position": [-200, 300],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": crack_density * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pl_slope",      "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": 6, "type": "int"}, "Intensity": {"value": crack_density * 0.2, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "pl_final",      "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    connections = [
        {"from": "pl_perlin_base",  "to": "pl_blur_base",  "from_output": "output",              "to_input": "Source"},
        {"from": "pl_blur_base",    "to": "pl_lvl_base",   "from_output": "Blur_HQ",             "to_input": "input1"},
        {"from": "pl_cells_pit",    "to": "pl_blend_pit",  "from_output": "output",              "to_input": "source"},
        {"from": "pl_lvl_base",     "to": "pl_blend_pit",  "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "pl_perlin_w1",    "to": "pl_blur_w1",    "from_output": "output",              "to_input": "Source"},
        {"from": "pl_blend_pit",    "to": "pl_warp1",      "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "pl_blur_w1",      "to": "pl_warp1",      "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "pl_cells_crack",  "to": "pl_slope",      "from_output": "output",              "to_input": "Source"},
        {"from": "pl_blur_w1",      "to": "pl_slope",      "from_output": "Blur_HQ",             "to_input": "Effect"},
        {"from": "pl_warp1",        "to": "pl_final",      "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "pl_slope",        "to": "pl_final",      "from_output": "Slope_Blur",          "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "pl_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.60, highlight_factor=1.10)


# ─────────────────────────────────────────────────────────────────────────────
# FABRIC / WOVEN RECIPE — grid structure + thread detail + weave variation
# ─────────────────────────────────────────────────────────────────────────────

def _fabric_recipe(description, color=(0.35, 0.25, 0.55), roughness=0.82, metallic=0.0,
                   thread_scale=12, weave_disorder=0.2):
    """Fabric/cloth: tile-random for thread distribution → transformation stretching →
    directional warp for weave pattern. 3 passes: warp, directional, detail blend.
    """
    nodes = [
        # Warp/weft threads from perlin with strong anisotropy
        {"id_alias": "fb_perlin_warp","resource_url": LIB["perlin_noise"],  "position": [-1400, 0],
         "parameters": {"scale": {"value": thread_scale, "type": "int"}, "disorder": {"value": weave_disorder * 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "fb_stretch_h",  "definition_id": "sbs::compositing::transformation", "position": [-1200, 0],
         "parameters": {"matrix22": [8.0, 0.0, 0.0, 0.15]}},
        {"id_alias": "fb_perlin_weft","resource_url": LIB["perlin_noise"],  "position": [-1400, 200],
         "parameters": {"scale": {"value": thread_scale, "type": "int"}, "disorder": {"value": weave_disorder * 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "fb_stretch_v",  "definition_id": "sbs::compositing::transformation", "position": [-1200, 200],
         "parameters": {"matrix22": [0.15, 0.0, 0.0, 8.0]}},
        # Blend warp + weft for weave crosshatch
        {"id_alias": "fb_blend_weave","definition_id": "sbs::compositing::blend", "position": [-1000, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.6}},
        # Warp pass 1 — thread irregularity
        {"id_alias": "fb_perlin_w1",  "resource_url": LIB["perlin_noise"],  "position": [-1000, 300],
         "parameters": {"scale": {"value": thread_scale * 2, "type": "int"}, "disorder": {"value": weave_disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "fb_blur_w1",    "resource_url": LIB["blur_hq_grayscale"], "position": [-800, 300],
         "parameters": {"Intensity": {"value": 1.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "fb_warp1",      "definition_id": "sbs::compositing::warp",   "position": [-800, 0],
         "parameters": {"intensity": weave_disorder * 0.15}},
        # Directional warp for fabric drape / flow
        {"id_alias": "fb_perlin_drape","resource_url": LIB["perlin_noise"], "position": [-600, 300],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": weave_disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "fb_dir_warp",   "definition_id": "sbs::compositing::directionalwarp", "position": [-600, 0],
         "parameters": {"intensity": 0.10}},
        # Fiber texture — clouds at fine scale for fabric fuzz
        {"id_alias": "fb_clouds_fuzz","resource_url": LIB["clouds_2"],     "position": [-400, 300],
         "parameters": {"scale": {"value": thread_scale * 3, "type": "int"}, "disorder": {"value": weave_disorder * 0.8, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "fb_blend_fuzz", "definition_id": "sbs::compositing::blend", "position": [-400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.10}},
        {"id_alias": "fb_final",      "definition_id": "sbs::compositing::levels", "position": [-200, 0]},
    ]
    connections = [
        {"from": "fb_perlin_warp",  "to": "fb_stretch_h",   "from_output": "output",              "to_input": "input1"},
        {"from": "fb_perlin_weft",  "to": "fb_stretch_v",   "from_output": "output",              "to_input": "input1"},
        {"from": "fb_stretch_h",    "to": "fb_blend_weave", "from_output": "unique_filter_output","to_input": "source"},
        {"from": "fb_stretch_v",    "to": "fb_blend_weave", "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "fb_perlin_w1",    "to": "fb_blur_w1",     "from_output": "output",              "to_input": "Source"},
        {"from": "fb_blend_weave",  "to": "fb_warp1",       "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "fb_blur_w1",      "to": "fb_warp1",       "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "fb_perlin_drape", "to": "fb_dir_warp",    "from_output": "output",              "to_input": "inputintensity"},
        {"from": "fb_warp1",        "to": "fb_dir_warp",    "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "fb_clouds_fuzz",  "to": "fb_blend_fuzz",  "from_output": "output",              "to_input": "source"},
        {"from": "fb_dir_warp",     "to": "fb_blend_fuzz",  "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "fb_blend_fuzz",   "to": "fb_final",       "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "fb_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.50, highlight_factor=1.15)


# ─────────────────────────────────────────────────────────────────────────────
# TERRACOTTA / FIRED CLAY RECIPE
# ─────────────────────────────────────────────────────────────────────────────

def _terracotta_recipe(description, color=(0.62, 0.32, 0.18), roughness=0.82, metallic=0.0):
    """Terracotta: coarse cells for pottery surface → perlin grain → slope-blur wheel marks.
    Similar to concrete but with finer surface pitting and warm clay tones.
    """
    nodes = [
        {"id_alias": "tc_cells_base", "resource_url": LIB["cells_1"],      "position": [-1200, 0],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": 0.35, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "tc_lvl_base",   "definition_id": "sbs::compositing::levels", "position": [-1000, 0],
         "parameters": {"levelinlow": [0.25, 0.25, 0.25, 0.25], "levelinhigh": [0.80, 0.80, 0.80, 0.80]}},
        {"id_alias": "tc_perlin_grn", "resource_url": LIB["perlin_noise"],  "position": [-1200, 200],
         "parameters": {"scale": {"value": 18, "type": "int"}, "disorder": {"value": 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "tc_blend1",     "definition_id": "sbs::compositing::blend", "position": [-800, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.28}},
        # Wheel throw lines — directional warp
        {"id_alias": "tc_perlin_dir", "resource_url": LIB["perlin_noise"],  "position": [-800, 300],
         "parameters": {"scale": {"value": 6, "type": "int"}, "disorder": {"value": 0.15, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "tc_dir_warp",   "definition_id": "sbs::compositing::directionalwarp", "position": [-600, 0],
         "parameters": {"intensity": 0.12}},
        {"id_alias": "tc_slope",      "resource_url": LIB["slope_blur_grayscale_2"], "position": [-400, 0],
         "parameters": {"Samples": {"value": 8, "type": "int"}, "Intensity": {"value": 0.22, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "tc_blur_slope", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 300],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        # Fine pitting — clouds at high scale
        {"id_alias": "tc_clouds_pit", "resource_url": LIB["clouds_2"],     "position": [-200, 300],
         "parameters": {"scale": {"value": 12, "type": "int"}, "disorder": {"value": 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "tc_blend_pit",  "definition_id": "sbs::compositing::blend", "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.10}},
        {"id_alias": "tc_final",      "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    connections = [
        {"from": "tc_cells_base", "to": "tc_lvl_base",  "from_output": "output",              "to_input": "input1"},
        {"from": "tc_perlin_grn", "to": "tc_blend1",    "from_output": "output",              "to_input": "source"},
        {"from": "tc_lvl_base",   "to": "tc_blend1",    "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "tc_perlin_dir", "to": "tc_dir_warp",  "from_output": "output",              "to_input": "inputintensity"},
        {"from": "tc_blend1",     "to": "tc_dir_warp",  "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "tc_perlin_dir", "to": "tc_blur_slope","from_output": "output",              "to_input": "Source"},
        {"from": "tc_dir_warp",   "to": "tc_slope",     "from_output": "unique_filter_output","to_input": "Source"},
        {"from": "tc_blur_slope", "to": "tc_slope",     "from_output": "Blur_HQ",             "to_input": "Effect"},
        {"from": "tc_clouds_pit", "to": "tc_blend_pit", "from_output": "output",              "to_input": "source"},
        {"from": "tc_slope",      "to": "tc_blend_pit", "from_output": "Slope_Blur",          "to_input": "destination"},
        {"from": "tc_blend_pit",  "to": "tc_final",     "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "tc_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.45, highlight_factor=1.20)


# ─────────────────────────────────────────────────────────────────────────────
# OBSIDIAN RECIPE — volcanic glass, ultra-smooth with conchoidal fractures
# ─────────────────────────────────────────────────────────────────────────────

def _obsidian_recipe(description, color=(0.05, 0.04, 0.06), roughness=0.05, metallic=0.0):
    """Obsidian: crystal fracture network → smooth glass surface + conchoidal shell patterns."""
    nodes = [
        {"id_alias": "ob_crystal",    "resource_url": LIB["crystal_1"],    "position": [-1200, 0],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ob_lvl1",       "definition_id": "sbs::compositing::levels", "position": [-1000, 0],
         "parameters": {"levelinlow": [0.35, 0.35, 0.35, 0.35], "levelinhigh": [0.9, 0.9, 0.9, 0.9],
                        "leveloutlow": [0.5, 0.5, 0.5, 0.5], "levelouthigh": [1.0, 1.0, 1.0, 1.0]}},
        # Conchoidal shell rings — cells at large scale
        {"id_alias": "ob_cells_shell","resource_url": LIB["cells_1"],      "position": [-1200, 200],
         "parameters": {"scale": {"value": 2, "type": "int"}, "disorder": {"value": 0.05, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ob_blur_shell", "resource_url": LIB["blur_hq_grayscale"], "position": [-1000, 200],
         "parameters": {"Intensity": {"value": 8.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "ob_blend1",     "definition_id": "sbs::compositing::blend", "position": [-800, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.25}},
        # Warp 1 — fracture flow
        {"id_alias": "ob_perlin_w1",  "resource_url": LIB["perlin_noise"],  "position": [-800, 300],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": 0.15, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ob_blur_w1",    "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 300],
         "parameters": {"Intensity": {"value": 4.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "ob_warp1",      "definition_id": "sbs::compositing::warp",   "position": [-600, 0],
         "parameters": {"intensity": 0.18}},
        # Smooth out — heavy blur for glass-like surface
        {"id_alias": "ob_blur_final", "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 0],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "ob_final",      "definition_id": "sbs::compositing::levels", "position": [-200, 0],
         "parameters": {"levelinlow": [0.35, 0.35, 0.35, 0.35], "levelinhigh": [0.95, 0.95, 0.95, 0.95],
                        "leveloutlow": [0.4, 0.4, 0.4, 0.4], "levelouthigh": [1.0, 1.0, 1.0, 1.0]}},
    ]
    connections = [
        {"from": "ob_crystal",    "to": "ob_lvl1",      "from_output": "output",              "to_input": "input1"},
        {"from": "ob_cells_shell","to": "ob_blur_shell", "from_output": "output",              "to_input": "Source"},
        {"from": "ob_lvl1",       "to": "ob_blend1",    "from_output": "unique_filter_output","to_input": "source"},
        {"from": "ob_blur_shell", "to": "ob_blend1",    "from_output": "Blur_HQ",             "to_input": "destination"},
        {"from": "ob_perlin_w1",  "to": "ob_blur_w1",   "from_output": "output",              "to_input": "Source"},
        {"from": "ob_blend1",     "to": "ob_warp1",     "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "ob_blur_w1",    "to": "ob_warp1",     "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "ob_warp1",      "to": "ob_blur_final","from_output": "unique_filter_output","to_input": "Source"},
        {"from": "ob_blur_final", "to": "ob_final",     "from_output": "Blur_HQ",             "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "ob_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.20, highlight_factor=2.0)


# ─────────────────────────────────────────────────────────────────────────────
# CARBON FIBER RECIPE — woven composite, high-tech surface
# ─────────────────────────────────────────────────────────────────────────────

def _carbon_fiber_recipe(description, color=(0.08, 0.08, 0.09), roughness=0.20, metallic=0.0):
    """Carbon fiber: tight anisotropic weave → directional warp → specular variation.
    Extremely tight thread scale with high anisotropy via transformation stretching.
    """
    nodes = [
        # Primary fiber direction (0°)
        {"id_alias": "cf_perlin_0",   "resource_url": LIB["perlin_noise"],  "position": [-1400, 0],
         "parameters": {"scale": {"value": 32, "type": "int"}, "disorder": {"value": 0.05, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cf_stretch_0",  "definition_id": "sbs::compositing::transformation", "position": [-1200, 0],
         "parameters": {"matrix22": [12.0, 0.0, 0.0, 0.1]}},
        # Secondary fiber direction (90°)
        {"id_alias": "cf_perlin_90",  "resource_url": LIB["perlin_noise"],  "position": [-1400, 200],
         "parameters": {"scale": {"value": 32, "type": "int"}, "disorder": {"value": 0.05, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cf_stretch_90", "definition_id": "sbs::compositing::transformation", "position": [-1200, 200],
         "parameters": {"matrix22": [0.1, 0.0, 0.0, 12.0]}},
        # Weave cross-hatch blend
        {"id_alias": "cf_blend_weave","definition_id": "sbs::compositing::blend", "position": [-1000, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.7}},
        {"id_alias": "cf_lvl_weave",  "definition_id": "sbs::compositing::levels", "position": [-800, 0],
         "parameters": {"levelinlow": [0.4, 0.4, 0.4, 0.4], "levelinhigh": [0.7, 0.7, 0.7, 0.7]}},
        # Tow bundle variation — cells at low scale
        {"id_alias": "cf_cells_tow",  "resource_url": LIB["cells_1"],      "position": [-800, 250],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": 0.15, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cf_blend_tow",  "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.12}},
        # Directional warp for slight fiber undulation
        {"id_alias": "cf_perlin_dul", "resource_url": LIB["perlin_noise"],  "position": [-400, 250],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": 0.08, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "cf_dir_warp",   "definition_id": "sbs::compositing::directionalwarp", "position": [-400, 0],
         "parameters": {"intensity": 0.04}},
        {"id_alias": "cf_final",      "definition_id": "sbs::compositing::levels", "position": [-200, 0],
         "parameters": {"levelinlow": [0.1, 0.1, 0.1, 0.1], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
    ]
    connections = [
        {"from": "cf_perlin_0",   "to": "cf_stretch_0",  "from_output": "output",              "to_input": "input1"},
        {"from": "cf_perlin_90",  "to": "cf_stretch_90", "from_output": "output",              "to_input": "input1"},
        {"from": "cf_stretch_0",  "to": "cf_blend_weave","from_output": "unique_filter_output","to_input": "source"},
        {"from": "cf_stretch_90", "to": "cf_blend_weave","from_output": "unique_filter_output","to_input": "destination"},
        {"from": "cf_blend_weave","to": "cf_lvl_weave",  "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "cf_cells_tow",  "to": "cf_blend_tow",  "from_output": "output",              "to_input": "source"},
        {"from": "cf_lvl_weave",  "to": "cf_blend_tow",  "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "cf_perlin_dul", "to": "cf_dir_warp",   "from_output": "output",              "to_input": "inputintensity"},
        {"from": "cf_blend_tow",  "to": "cf_dir_warp",   "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "cf_dir_warp",   "to": "cf_final",      "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "cf_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.30, highlight_factor=1.80)


# ─────────────────────────────────────────────────────────────────────────────
# TILE / CERAMIC RECIPE — regular grid with grout
# ─────────────────────────────────────────────────────────────────────────────

def _tile_recipe(description, color=(0.80, 0.78, 0.75), roughness=0.25, metallic=0.0,
                 tile_scale=4, grout_depth=0.12):
    """Ceramic tile: polygon grid → grout channels via slope-blur → surface gloss variation."""
    nodes = [
        {"id_alias": "tl_poly",      "resource_url": LIB["polygon_2"],     "position": [-1200, 0],
         "parameters": {"Tiling": {"value": tile_scale, "type": "int"}, "Sides": {"value": 4, "type": "int"},
                        "Scale": {"value": 0.93, "type": "float"}, "Gradient": {"value": 1.0, "type": "float"}}},
        {"id_alias": "tl_lvl_tile",  "definition_id": "sbs::compositing::levels", "position": [-1000, 0],
         "parameters": {"levelinlow": [grout_depth, grout_depth, grout_depth, grout_depth],
                        "levelinhigh": [grout_depth + 0.08, grout_depth + 0.08, grout_depth + 0.08, grout_depth + 0.08],
                        "leveloutlow": [0.0, 0.0, 0.0, 0.0], "levelouthigh": [1.0, 1.0, 1.0, 1.0]}},
        {"id_alias": "tl_perlin_grout","resource_url": LIB["perlin_noise"], "position": [-1200, 200],
         "parameters": {"scale": {"value": 24, "type": "int"}, "disorder": {"value": 0.35, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "tl_blur_grout", "resource_url": LIB["blur_hq_grayscale"], "position": [-1000, 200],
         "parameters": {"Intensity": {"value": 1.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "tl_slope",     "resource_url": LIB["slope_blur_grayscale_2"], "position": [-800, 0],
         "parameters": {"Samples": {"value": 6, "type": "int"}, "Intensity": {"value": grout_depth * 2, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        # Gloss variation on tile surface
        {"id_alias": "tl_perlin_surf","resource_url": LIB["perlin_noise"], "position": [-600, 200],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "tl_blur_surf",  "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 200],
         "parameters": {"Intensity": {"value": 4.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "tl_blend_surf", "definition_id": "sbs::compositing::blend", "position": [-400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.08}},
        {"id_alias": "tl_final",      "definition_id": "sbs::compositing::levels", "position": [-200, 0]},
    ]
    connections = [
        {"from": "tl_poly",       "to": "tl_lvl_tile",  "from_output": "output",              "to_input": "input1"},
        {"from": "tl_perlin_grout","to": "tl_blur_grout","from_output": "output",              "to_input": "Source"},
        {"from": "tl_lvl_tile",   "to": "tl_slope",     "from_output": "unique_filter_output","to_input": "Source"},
        {"from": "tl_blur_grout", "to": "tl_slope",     "from_output": "Blur_HQ",             "to_input": "Effect"},
        {"from": "tl_perlin_surf","to": "tl_blur_surf",  "from_output": "output",              "to_input": "Source"},
        {"from": "tl_blur_surf",  "to": "tl_blend_surf", "from_output": "Blur_HQ",             "to_input": "source"},
        {"from": "tl_slope",      "to": "tl_blend_surf", "from_output": "Slope_Blur",          "to_input": "destination"},
        {"from": "tl_blend_surf", "to": "tl_final",     "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "tl_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.55, highlight_factor=1.15)


# ─────────────────────────────────────────────────────────────────────────────
# PAINTED METAL RECIPE — smooth paint layer + chipping + surface dents
# ─────────────────────────────────────────────────────────────────────────────

def _painted_metal_recipe(description, color=(0.22, 0.35, 0.58), roughness=0.30, metallic=0.0,
                          chip_density=0.25, dent_intensity=0.15):
    """Painted metal: smooth base coat + paint chips via cells → dents via warp.
    The metal substrate shows through chipped areas (low height = exposed metal).
    """
    nodes = [
        # Base coat — very smooth perlin for paint layer
        {"id_alias": "pm_perlin_coat","resource_url": LIB["perlin_noise"],  "position": [-1200, 0],
         "parameters": {"scale": {"value": 3, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_blur_coat",  "resource_url": LIB["blur_hq_grayscale"], "position": [-1000, 0],
         "parameters": {"Intensity": {"value": 10.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pm_lvl_coat",   "definition_id": "sbs::compositing::levels", "position": [-800, 0],
         "parameters": {"levelinlow": [0.4, 0.4, 0.4, 0.4], "levelinhigh": [0.6, 0.6, 0.6, 0.6],
                        "leveloutlow": [0.7, 0.7, 0.7, 0.7], "levelouthigh": [0.95, 0.95, 0.95, 0.95]}},
        # Paint chips — cells at moderate scale
        {"id_alias": "pm_cells_chip", "resource_url": LIB["cells_1"],      "position": [-1200, 250],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": chip_density * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_lvl_chip",   "definition_id": "sbs::compositing::levels", "position": [-1000, 250],
         "parameters": {"levelinlow": [1.0 - chip_density, 1.0 - chip_density, 1.0 - chip_density, 1.0 - chip_density],
                        "levelinhigh": [1.0, 1.0, 1.0, 1.0],
                        "leveloutlow": [0.0, 0.0, 0.0, 0.0], "levelouthigh": [0.5, 0.5, 0.5, 0.5]}},
        {"id_alias": "pm_blend_chip", "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 0, "opacitymult": 1.0}},
        # Dents / impact marks — perlin warp
        {"id_alias": "pm_perlin_dent","resource_url": LIB["perlin_noise"],  "position": [-600, 300],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_blur_dent",  "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 300],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pm_warp_dent",  "definition_id": "sbs::compositing::warp",   "position": [-400, 0],
         "parameters": {"intensity": dent_intensity}},
        # Micro surface scratches
        {"id_alias": "pm_perlin_scr", "resource_url": LIB["perlin_noise"],  "position": [-200, 300],
         "parameters": {"scale": {"value": 48, "type": "int"}, "disorder": {"value": 0.02, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_blend_scr",  "definition_id": "sbs::compositing::blend", "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.06}},
        {"id_alias": "pm_final",      "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    connections = [
        {"from": "pm_perlin_coat","to": "pm_blur_coat",  "from_output": "output",              "to_input": "Source"},
        {"from": "pm_blur_coat",  "to": "pm_lvl_coat",   "from_output": "Blur_HQ",             "to_input": "input1"},
        {"from": "pm_cells_chip", "to": "pm_lvl_chip",   "from_output": "output",              "to_input": "input1"},
        {"from": "pm_lvl_coat",   "to": "pm_blend_chip", "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "pm_lvl_chip",   "to": "pm_blend_chip", "from_output": "unique_filter_output","to_input": "source"},
        {"from": "pm_lvl_chip",   "to": "pm_blend_chip", "from_output": "unique_filter_output","to_input": "opacity"},
        {"from": "pm_perlin_dent","to": "pm_blur_dent",  "from_output": "output",              "to_input": "Source"},
        {"from": "pm_blend_chip", "to": "pm_warp_dent",  "from_output": "unique_filter_output","to_input": "input1"},
        {"from": "pm_blur_dent",  "to": "pm_warp_dent",  "from_output": "Blur_HQ",             "to_input": "inputgradient"},
        {"from": "pm_perlin_scr", "to": "pm_blend_scr",  "from_output": "output",              "to_input": "source"},
        {"from": "pm_warp_dent",  "to": "pm_blend_scr",  "from_output": "unique_filter_output","to_input": "destination"},
        {"from": "pm_blend_scr",  "to": "pm_final",      "from_output": "unique_filter_output","to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "pm_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=0.35, highlight_factor=1.20)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SHAPE — Exact pro Data (extracted from SubstanceGraph1)
#
# Verified parameters from live SD 15.0.3 node inspection:
#   polygon_2:        Tiling=1, Sides=4, Scale=1.0, Gradient=1.0, autoscale=True
#   levels (poly):    levelinhigh=[0.4205], out=[0..1]  ← key: clips polygon top
#   blend1:           mode=6 (Difference),  gradient_linear_1 src + poly_levels dst
#   cells_1:          scale=2, disorder=0.18, non_square_expansion=False
#   blend2:           mode=3 (Multiply),    cells_1 src + blend1 dst
#   gradient_axial:   point_1=(0,0), point_2=(0.75,0.75)
#   transformation:   matrix22=(0,1,-1,0) → 90° rotation
#   levels (axial):   mid=0.66, outlow=0.214, outhigh=0.649  ← bevel remap
#   perlin_noise:     scale=3, disorder=0.0
#   blend3 (final):   mode=6 (Difference),  blend2 src + axial_levels dst
#
# Connection map (exactly as wired in SubstanceGraph1):
#   polygon_2 → levels1(input1)
#   gradient_linear_1 → blend1(source)
#   levels1 → blend1(destination)
#   cells_1 → blend2(source)
#   blend1 → blend2(destination)
#   gradient_axial → transformation(input1)
#   transformation → levels2(input1)
#   blend2 → blend3(source)
#   levels2 → blend3(destination)
#   → FINAL output (feeds IterationPatternShape)
# ─────────────────────────────────────────────────────────────────────────────

def _main_shape_recipe():
    """MainShape — faithful reconstruction from pro SubstanceGraph1 data.

    This is the ~20% foundation that all his rock material shapes are built upon.
    9 nodes / 8 connections — pure procedural, zero library noise generators.

    Output: grayscale shape combining:
      - Polygon gradient (4-sided, high-contrast via levels clip at 0.42)
      - Linear gradient difference (Difference blend creates concave/convex edge)
      - Cells variation (Multiply blend = structured cell noise modulation)
      - Axial gradient (rotated 90°, remapped 0.21→0.65 = soft directional bevel)
      - Final Difference blend = complex edge+interior mask ready for warp input
    """
    nodes = [
        # Top row: gradient_linear_1 + polygon
        {"id_alias": "ms_grad_lin",   "resource_url": LIB["gradient_linear_1"], "position": [-1600, -200],
         "parameters": {"Tiling": {"value": 1, "type": "int"}, "rotation": {"value": 0, "type": "int"}}},
        {"id_alias": "ms_poly",       "resource_url": LIB["polygon_2"], "position": [-1600, 0],
         "parameters": {"Tiling": {"value": 1, "type": "int"}, "Sides": {"value": 4, "type": "int"},
                        "Scale": {"value": 1.0, "type": "float"}, "Gradient": {"value": 1.0, "type": "float"},
                        "autoscale": {"value": True, "type": "bool"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        # Levels: clip polygon gradient at 0.4205 (creates sharp interior mask)
        {"id_alias": "ms_lvl_poly",   "definition_id": "sbs::compositing::levels", "position": [-1400, 0],
         "parameters": {"levelinlow":   [0.0,    0.0,    0.0,    0.0],
                        "levelinhigh":  [0.4205, 0.4205, 0.4205, 1.0],
                        "leveloutlow":  [0.0,    0.0,    0.0,    0.0],
                        "levelouthigh": [1.0,    1.0,    1.0,    1.0]}},
        # Blend 1: Difference(gradient_linear src, poly_levels dst)
        {"id_alias": "ms_blend1",     "definition_id": "sbs::compositing::blend", "position": [-1200, 0],
         "parameters": {"blendingmode": 6, "opacitymult": 1.0}},
        # Mid row: cells_1
        {"id_alias": "ms_cells",      "resource_url": LIB["cells_1"], "position": [-1200, 200],
         "parameters": {"scale": {"value": 2, "type": "int"}, "disorder": {"value": 0.18, "type": "float"},
                        "non_square_expansion": {"value": False, "type": "bool"}}},
        # Blend 2: Multiply(cells src, blend1 dst)
        {"id_alias": "ms_blend2",     "definition_id": "sbs::compositing::blend", "position": [-1000, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 1.0}},
        # Bottom row: gradient_axial → 90° rotation → levels remap
        {"id_alias": "ms_grad_axial", "resource_url": LIB["gradient_axial"], "position": [-1600, 400],
         "parameters": {"point_1": [0.0, 0.0], "point_2": [0.75, 0.75], "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "ms_transform",  "definition_id": "sbs::compositing::transformation", "position": [-1400, 400],
         "parameters": {"matrix22": [0.0, 1.0, -1.0, 0.0], "offset": [0.0, 0.0]}},
        # Levels: remap axial → outlow=0.214, outhigh=0.649, mid=0.658 (bevel profile)
        {"id_alias": "ms_lvl_axial",  "definition_id": "sbs::compositing::levels", "position": [-1200, 400],
         "parameters": {"levelinlow":   [0.0,   0.0,   0.0,   0.0],
                        "levelinhigh":  [1.0,   1.0,   1.0,   1.0],
                        "leveloutlow":  [0.214, 0.214, 0.214, 0.0],
                        "levelouthigh": [0.649, 0.649, 0.649, 1.0]}},
        # Final Blend: Difference(blend2 src, axial_levels dst) → MAIN SHAPE OUTPUT
        {"id_alias": "ms_final",      "definition_id": "sbs::compositing::blend", "position": [-800, 0],
         "parameters": {"blendingmode": 6, "opacitymult": 1.0}},
        # Output
        {"id_alias": "ms_out",        "definition_id": "sbs::compositing::output", "usage": "height",
         "label": "MainShape", "position": [-600, 0]},
    ]
    connections = [
        # Top path: polygon → levels → blend1(destination)
        {"from": "ms_poly",       "to": "ms_lvl_poly",   "from_output": "output",               "to_input": "input1"},
        {"from": "ms_grad_lin",   "to": "ms_blend1",     "from_output": "Simple_Gradient",       "to_input": "source"},
        {"from": "ms_lvl_poly",   "to": "ms_blend1",     "from_output": "unique_filter_output",  "to_input": "destination"},
        # Mid: cells → blend2(source), blend1 → blend2(destination)
        {"from": "ms_cells",      "to": "ms_blend2",     "from_output": "output",               "to_input": "source"},
        {"from": "ms_blend1",     "to": "ms_blend2",     "from_output": "unique_filter_output",  "to_input": "destination"},
        # Bottom path: axial → transform → levels → blend3(destination)
        {"from": "ms_grad_axial", "to": "ms_transform",  "from_output": "output",               "to_input": "input1"},
        {"from": "ms_transform",  "to": "ms_lvl_axial",  "from_output": "unique_filter_output",  "to_input": "input1"},
        # Final: blend2 → blend3(source), axial_levels → blend3(destination)
        {"from": "ms_blend2",     "to": "ms_final",      "from_output": "unique_filter_output",  "to_input": "source"},
        {"from": "ms_lvl_axial",  "to": "ms_final",      "from_output": "unique_filter_output",  "to_input": "destination"},
        {"from": "ms_final",      "to": "ms_out",        "from_output": "unique_filter_output",  "to_input": "inputNodeOutput"},
    ]
    return {
        "description": "MainShape — exact pro reconstruction from SubstanceGraph1 data. 20% foundation shape feeding IterationPatternShape.",
        "nodes": nodes,
        "connections": connections,
        "height_alias": "ms_final",
        "color": (0.5, 0.5, 0.5),
        "roughness": 0.8,
        "metallic": 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PROFESSIONAL ROCK — pro Architecture
# Pattern: clouds_2 → slope_blur cascade → edge_detect → flood_fill chain
#          → directionalwarp × N → multi_directional_warp → blend stack
# ─────────────────────────────────────────────────────────────────────────────

def _pro_rock_recipe(description, color=(0.50, 0.45, 0.40), roughness=0.88, metallic=0.0,
                     macro_scale=3, mid_scale=6, detail_scale=12, disorder=0.5,
                     shadow_factor=0.45, highlight_factor=1.35):
    """Professional rock material — pro pattern (53 nodes).

    Architecture:
      Stage 1: clouds_2 (macro) → slope_blur → slope_blur (cascade) → base shape
      Stage 2: edge_detect → flood_fill → flood_fill_to_gradient_2 (per-island gradients)
      Stage 3: multi_directional_warp × 2 (clouds drives warp)
      Stage 4: directionalwarp cascade × 3 (cells + perlin maps)
      Stage 5: highpass for micro surface + histogram_scan remap
      PBR: 14 nodes standard chain
    """
    nodes = [
        # ── Stage 1: Macro form (clouds_2 + cascaded slope blur)
        {"id_alias": "pr_clouds_macro", "resource_url": LIB["clouds_2"], "position": [-2800, 0],
         "parameters": {"scale": {"value": macro_scale, "type": "int"}, "disorder": {"value": disorder * 0.8, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pr_clouds_mid",   "resource_url": LIB["clouds_2"], "position": [-2800, 200],
         "parameters": {"scale": {"value": mid_scale, "type": "int"}, "disorder": {"value": disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pr_blur_macro",   "resource_url": LIB["blur_hq_grayscale"], "position": [-2600, 0],
         "parameters": {"Intensity": {"value": 4.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pr_slope1",       "resource_url": LIB["slope_blur_grayscale_2"], "position": [-2400, 0],
         "parameters": {"Samples": {"value": 12, "type": "int"}, "Intensity": {"value": 0.35, "type": "float"}, "mode": {"value": 0, "type": "int"}}},
        {"id_alias": "pr_slope2",       "resource_url": LIB["slope_blur_grayscale_2"], "position": [-2200, 0],
         "parameters": {"Samples": {"value": 8, "type": "int"}, "Intensity": {"value": 0.2, "type": "float"}, "mode": {"value": 0, "type": "int"}}},
        {"id_alias": "pr_lvl1",         "definition_id": "sbs::compositing::levels", "position": [-2000, 0],
         "parameters": {"levelinlow": [0.15, 0.15, 0.15, 0.15], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
        # ── Stage 2: Edge detect → flood fill → per-island gradient
        {"id_alias": "pr_edge1",        "resource_url": LIB["edge_detect"], "position": [-1800, 0],
         "parameters": {"edge_width": {"value": 2.0, "type": "float"}, "edge_roundness": {"value": 0.5, "type": "float"}, "tolerance": {"value": 0.3, "type": "float"}}},
        {"id_alias": "pr_flood1",       "resource_url": LIB["flood_fill"], "position": [-1600, 0]},
        {"id_alias": "pr_ff_grad",      "resource_url": LIB["flood_fill_to_gradient_2"], "position": [-1400, 0],
         "parameters": {"angle": {"value": 0.0, "type": "float"}, "angle_variation": {"value": 1.0, "type": "float"}}},
        {"id_alias": "pr_ff_gray",      "resource_url": LIB["flood_fill_to_grayscale"], "position": [-1400, 200],
         "parameters": {"luminance_random": {"value": 0.5, "type": "float"}}},
        {"id_alias": "pr_blend_ff",     "definition_id": "sbs::compositing::blend", "position": [-1200, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.35}},
        {"id_alias": "pr_lvl2",         "definition_id": "sbs::compositing::levels", "position": [-1000, 0],
         "parameters": {"levelinlow": [0.1, 0.1, 0.1, 0.1], "levelinhigh": [0.95, 0.95, 0.95, 0.95]}},
        # ── Stage 3: Multi-directional warp (clouds as intensity input)
        {"id_alias": "pr_clouds_warp1", "resource_url": LIB["clouds_2"], "position": [-1000, 250],
         "parameters": {"scale": {"value": mid_scale * 2, "type": "int"}, "disorder": {"value": disorder * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pr_multi_warp1",  "resource_url": LIB["multi_directional_warp_grayscale"], "position": [-800, 0],
         "parameters": {"intensity": {"value": 0.3, "type": "float"}, "warp_angle": {"value": 0.0, "type": "float"}, "directions": {"value": 4, "type": "int"}}},
        {"id_alias": "pr_clouds_warp2", "resource_url": LIB["clouds_2"], "position": [-800, 250],
         "parameters": {"scale": {"value": detail_scale, "type": "int"}, "disorder": {"value": disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pr_multi_warp2",  "resource_url": LIB["multi_directional_warp_grayscale"], "position": [-600, 0],
         "parameters": {"intensity": {"value": 0.18, "type": "float"}, "warp_angle": {"value": 0.25, "type": "float"}, "directions": {"value": 6, "type": "int"}}},
        # ── Stage 4: Directional warp cascade (perlin + crystal maps)
        {"id_alias": "pr_perlin_dw1",   "resource_url": LIB["perlin_noise"], "position": [-600, 350],
         "parameters": {"scale": {"value": mid_scale, "type": "int"}, "disorder": {"value": disorder * 0.7, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pr_blur_dw1",     "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 350],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pr_dir_warp1",    "definition_id": "sbs::compositing::directionalwarp", "position": [-400, 0],
         "parameters": {"intensity": 0.25}},
        {"id_alias": "pr_crystal",      "resource_url": LIB["crystal_1"], "position": [-200, 350],
         "parameters": {"scale": {"value": detail_scale, "type": "int"}, "disorder": {"value": disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pr_blur_dw2",     "resource_url": LIB["blur_hq_grayscale"], "position": [-200, 500],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pr_dir_warp2",    "definition_id": "sbs::compositing::directionalwarp", "position": [-200, 0],
         "parameters": {"intensity": 0.15}},
        {"id_alias": "pr_cells_dw3",    "resource_url": LIB["cells_2"], "position": [0, 350],
         "parameters": {"scale": {"value": detail_scale * 2, "type": "int"}, "disorder": {"value": disorder * 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pr_dir_warp3",    "definition_id": "sbs::compositing::directionalwarp", "position": [0, 0],
         "parameters": {"intensity": 0.08}},
        # ── Stage 5: Edge detail + highpass micro surface
        {"id_alias": "pr_edge2",        "resource_url": LIB["edge_detect"], "position": [200, 200],
         "parameters": {"edge_width": {"value": 1.0, "type": "float"}, "edge_roundness": {"value": 0.8, "type": "float"}, "tolerance": {"value": 0.2, "type": "float"}}},
        {"id_alias": "pr_blend_edge",   "definition_id": "sbs::compositing::blend", "position": [200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.18}},
        {"id_alias": "pr_highpass",     "resource_url": LIB["highpass_grayscale"], "position": [400, 200],
         "parameters": {"Radius": {"value": 8.0, "type": "float"}}},
        {"id_alias": "pr_blend_hp",     "definition_id": "sbs::compositing::blend", "position": [400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.10}},
        # ── Stage 6: Histogram scan + final levels
        {"id_alias": "pr_hist_scan",    "resource_url": LIB["histogram_scan"], "position": [600, 0],
         "parameters": {"Position": {"value": 0.5, "type": "float"}, "Contrast": {"value": 0.6, "type": "float"}}},
        {"id_alias": "pr_final",        "definition_id": "sbs::compositing::levels", "position": [800, 0],
         "parameters": {"levelinlow": [0.05, 0.05, 0.05, 0.05], "levelinhigh": [0.95, 0.95, 0.95, 0.95]}},
    ]
    connections = [
        # Stage 1: clouds cascade through slope blurs
        {"from": "pr_clouds_macro", "to": "pr_blur_macro",   "from_output": "output",       "to_input": "Source"},
        {"from": "pr_blur_macro",   "to": "pr_slope1",       "from_output": "Blur_HQ",      "to_input": "Source"},
        {"from": "pr_clouds_mid",   "to": "pr_slope1",       "from_output": "output",       "to_input": "Effect"},
        {"from": "pr_slope1",       "to": "pr_slope2",       "from_output": "Slope_Blur",   "to_input": "Source"},
        {"from": "pr_clouds_mid",   "to": "pr_slope2",       "from_output": "output",       "to_input": "Effect"},
        {"from": "pr_slope2",       "to": "pr_lvl1",         "from_output": "Slope_Blur",   "to_input": "input1"},
        # Stage 2: edge → flood fill → per-island gradients
        {"from": "pr_lvl1",         "to": "pr_edge1",        "from_output": "unique_filter_output", "to_input": "input"},
        {"from": "pr_edge1",        "to": "pr_flood1",       "from_output": "output",       "to_input": "mask"},
        {"from": "pr_flood1",       "to": "pr_ff_grad",      "from_output": "output",       "to_input": "input"},
        {"from": "pr_flood1",       "to": "pr_ff_gray",      "from_output": "output",       "to_input": "input"},
        {"from": "pr_ff_grad",      "to": "pr_blend_ff",     "from_output": "output",       "to_input": "source"},
        {"from": "pr_ff_gray",      "to": "pr_blend_ff",     "from_output": "output",       "to_input": "destination"},
        {"from": "pr_blend_ff",     "to": "pr_lvl2",         "from_output": "unique_filter_output", "to_input": "input1"},
        # Stage 3: multi-directional warp with clouds intensity
        {"from": "pr_lvl2",         "to": "pr_multi_warp1",  "from_output": "unique_filter_output", "to_input": "input"},
        {"from": "pr_clouds_warp1", "to": "pr_multi_warp1",  "from_output": "output",       "to_input": "intensity_input"},
        {"from": "pr_multi_warp1",  "to": "pr_multi_warp2",  "from_output": "output",       "to_input": "input"},
        {"from": "pr_clouds_warp2", "to": "pr_multi_warp2",  "from_output": "output",       "to_input": "intensity_input"},
        # Stage 4: directional warp cascade
        {"from": "pr_perlin_dw1",   "to": "pr_blur_dw1",    "from_output": "output",        "to_input": "Source"},
        {"from": "pr_multi_warp2",  "to": "pr_dir_warp1",   "from_output": "output",        "to_input": "input1"},
        {"from": "pr_blur_dw1",     "to": "pr_dir_warp1",   "from_output": "Blur_HQ",       "to_input": "inputintensity"},
        {"from": "pr_crystal",      "to": "pr_blur_dw2",    "from_output": "output",        "to_input": "Source"},
        {"from": "pr_dir_warp1",    "to": "pr_dir_warp2",   "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pr_blur_dw2",     "to": "pr_dir_warp2",   "from_output": "Blur_HQ",       "to_input": "inputintensity"},
        {"from": "pr_dir_warp2",    "to": "pr_dir_warp3",   "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pr_cells_dw3",    "to": "pr_dir_warp3",   "from_output": "output",        "to_input": "inputintensity"},
        # Stage 5: edge detail + highpass
        {"from": "pr_dir_warp3",    "to": "pr_edge2",       "from_output": "unique_filter_output", "to_input": "input"},
        {"from": "pr_edge2",        "to": "pr_blend_edge",  "from_output": "output",        "to_input": "source"},
        {"from": "pr_dir_warp3",    "to": "pr_blend_edge",  "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "pr_blend_edge",   "to": "pr_highpass",    "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "pr_highpass",     "to": "pr_blend_hp",    "from_output": "Highpass",      "to_input": "source"},
        {"from": "pr_blend_edge",   "to": "pr_blend_hp",    "from_output": "unique_filter_output", "to_input": "destination"},
        # Stage 6: histogram scan + final
        {"from": "pr_blend_hp",     "to": "pr_hist_scan",   "from_output": "unique_filter_output", "to_input": "Input_1"},
        {"from": "pr_hist_scan",    "to": "pr_final",       "from_output": "Output",        "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "pr_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=shadow_factor, highlight_factor=highlight_factor)


# ─────────────────────────────────────────────────────────────────────────────
# PROFESSIONAL METAL — pro Architecture
# Pattern: clouds_2 → multi_dir_warp → edge_detect for scratch/wear
#          non_uniform_blur (anisotropic) for directional brushing
# ─────────────────────────────────────────────────────────────────────────────

def _pro_metal_recipe(description, color=(0.65, 0.65, 0.68), roughness=0.25, metallic=1.0,
                      scratch_scale=24, wear_intensity=0.2, shadow_factor=0.3, highlight_factor=1.5):
    """Professional brushed metal — 45 nodes, pro workflow.

    Architecture:
      Stage 1: perlin (fine) + non_uniform_blur (anisotropic) = directional grain
      Stage 2: clouds_2 → multi_dir_warp = large-scale surface variation
      Stage 3: edge_detect → flood_fill → per-island contrast = wear zones
      Stage 4: directional warp cascade × 2 = micro undulation
      Stage 5: highpass + histogram_scan = micro-scratch detail
    """
    nodes = [
        # ── Stage 1: Directional grain via anisotropic blur
        {"id_alias": "pm_perlin_base",  "resource_url": LIB["perlin_noise"], "position": [-2400, 0],
         "parameters": {"scale": {"value": scratch_scale, "type": "int"}, "disorder": {"value": 0.05, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_aniso_blur",   "resource_url": LIB["non_uniform_blur_grayscale"], "position": [-2200, 0],
         "parameters": {"Intensity": {"value": 25.0, "type": "float"}, "Anisotropy": {"value": 0.95, "type": "float"}, "Asymmetry": {"value": 0.0, "type": "float"}, "Angle": {"value": 0.0, "type": "float"}, "Samples": {"value": 16, "type": "int"}}},
        {"id_alias": "pm_lvl_grain",    "definition_id": "sbs::compositing::levels", "position": [-2000, 0],
         "parameters": {"levelinlow": [0.35, 0.35, 0.35, 0.35], "levelinhigh": [0.7, 0.7, 0.7, 0.7]}},
        # ── Stage 2: Large-scale surface variation
        {"id_alias": "pm_clouds_var",   "resource_url": LIB["clouds_2"], "position": [-2000, 250],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_multi_warp",   "resource_url": LIB["multi_directional_warp_grayscale"], "position": [-1800, 0],
         "parameters": {"intensity": {"value": wear_intensity, "type": "float"}, "warp_angle": {"value": 0.0, "type": "float"}, "directions": {"value": 4, "type": "int"}}},
        {"id_alias": "pm_blend_var",    "definition_id": "sbs::compositing::blend", "position": [-1600, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.12}},
        {"id_alias": "pm_lvl_var",      "definition_id": "sbs::compositing::levels", "position": [-1400, 0],
         "parameters": {"levelinlow": [0.2, 0.2, 0.2, 0.2], "levelinhigh": [0.85, 0.85, 0.85, 0.85]}},
        # ── Stage 3: Wear zones via edge_detect + flood_fill
        {"id_alias": "pm_edge_wear",    "resource_url": LIB["edge_detect"], "position": [-1400, 250],
         "parameters": {"edge_width": {"value": 3.0, "type": "float"}, "edge_roundness": {"value": 0.6, "type": "float"}, "tolerance": {"value": 0.4, "type": "float"}}},
        {"id_alias": "pm_flood_wear",   "resource_url": LIB["flood_fill"], "position": [-1200, 250]},
        {"id_alias": "pm_ff_gray_wear", "resource_url": LIB["flood_fill_to_grayscale"], "position": [-1000, 250],
         "parameters": {"luminance_random": {"value": 0.3, "type": "float"}}},
        {"id_alias": "pm_blend_wear",   "definition_id": "sbs::compositing::blend", "position": [-1200, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.20}},
        {"id_alias": "pm_lvl_wear",     "definition_id": "sbs::compositing::levels", "position": [-1000, 0],
         "parameters": {"levelinlow": [0.1, 0.1, 0.1, 0.1], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
        # ── Stage 4: Directional warp cascade (subtle undulation)
        {"id_alias": "pm_perlin_dw",    "resource_url": LIB["perlin_noise"], "position": [-800, 250],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": 0.15, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_blur_dw",      "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 250],
         "parameters": {"Intensity": {"value": 4.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pm_dir_warp1",    "definition_id": "sbs::compositing::directionalwarp", "position": [-800, 0],
         "parameters": {"intensity": 0.12}},
        {"id_alias": "pm_clouds_dw2",   "resource_url": LIB["clouds_2"], "position": [-600, 400],
         "parameters": {"scale": {"value": scratch_scale // 2, "type": "int"}, "disorder": {"value": 0.1, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_dir_warp2",    "definition_id": "sbs::compositing::directionalwarp", "position": [-600, 0],
         "parameters": {"intensity": 0.06}},
        # ── Stage 5: Micro scratch via highpass + histogram_scan
        {"id_alias": "pm_perlin_scr",   "resource_url": LIB["perlin_noise"], "position": [-400, 250],
         "parameters": {"scale": {"value": scratch_scale * 2, "type": "int"}, "disorder": {"value": 0.02, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pm_highpass",     "resource_url": LIB["highpass_grayscale"], "position": [-400, 400],
         "parameters": {"Radius": {"value": 4.0, "type": "float"}}},
        {"id_alias": "pm_hist_scr",     "resource_url": LIB["histogram_scan"], "position": [-200, 400],
         "parameters": {"Position": {"value": 0.5, "type": "float"}, "Contrast": {"value": 0.8, "type": "float"}}},
        {"id_alias": "pm_blend_scr",    "definition_id": "sbs::compositing::blend", "position": [-400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.07}},
        {"id_alias": "pm_blend_scr2",   "definition_id": "sbs::compositing::blend", "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.04}},
        {"id_alias": "pm_final",        "definition_id": "sbs::compositing::levels", "position": [0, 0],
         "parameters": {"levelinlow": [0.05, 0.05, 0.05, 0.05], "levelinhigh": [0.95, 0.95, 0.95, 0.95]}},
    ]
    connections = [
        # Stage 1: anisotropic grain
        {"from": "pm_perlin_base",  "to": "pm_aniso_blur",  "from_output": "output",       "to_input": "Source"},
        {"from": "pm_aniso_blur",   "to": "pm_lvl_grain",   "from_output": "Non_Uniform_Blur", "to_input": "input1"},
        # Stage 2: surface variation
        {"from": "pm_lvl_grain",    "to": "pm_multi_warp",  "from_output": "unique_filter_output", "to_input": "input"},
        {"from": "pm_clouds_var",   "to": "pm_multi_warp",  "from_output": "output",       "to_input": "intensity_input"},
        {"from": "pm_lvl_grain",    "to": "pm_blend_var",   "from_output": "unique_filter_output", "to_input": "source"},
        {"from": "pm_multi_warp",   "to": "pm_blend_var",   "from_output": "output",       "to_input": "destination"},
        {"from": "pm_blend_var",    "to": "pm_lvl_var",     "from_output": "unique_filter_output", "to_input": "input1"},
        # Stage 3: wear zones
        {"from": "pm_lvl_var",      "to": "pm_edge_wear",   "from_output": "unique_filter_output", "to_input": "input"},
        {"from": "pm_edge_wear",    "to": "pm_flood_wear",  "from_output": "output",       "to_input": "mask"},
        {"from": "pm_flood_wear",   "to": "pm_ff_gray_wear","from_output": "output",       "to_input": "input"},
        {"from": "pm_ff_gray_wear", "to": "pm_blend_wear",  "from_output": "output",       "to_input": "source"},
        {"from": "pm_lvl_var",      "to": "pm_blend_wear",  "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "pm_blend_wear",   "to": "pm_lvl_wear",    "from_output": "unique_filter_output", "to_input": "input1"},
        # Stage 4: directional warp cascade
        {"from": "pm_perlin_dw",    "to": "pm_blur_dw",     "from_output": "output",       "to_input": "Source"},
        {"from": "pm_lvl_wear",     "to": "pm_dir_warp1",   "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pm_blur_dw",      "to": "pm_dir_warp1",   "from_output": "Blur_HQ",      "to_input": "inputintensity"},
        {"from": "pm_dir_warp1",    "to": "pm_dir_warp2",   "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pm_clouds_dw2",   "to": "pm_dir_warp2",   "from_output": "output",       "to_input": "inputintensity"},
        # Stage 5: micro scratch
        {"from": "pm_perlin_scr",   "to": "pm_highpass",    "from_output": "output",       "to_input": "Source"},
        {"from": "pm_highpass",     "to": "pm_hist_scr",    "from_output": "Highpass",     "to_input": "Input_1"},
        {"from": "pm_perlin_scr",   "to": "pm_blend_scr",   "from_output": "output",       "to_input": "source"},
        {"from": "pm_dir_warp2",    "to": "pm_blend_scr",   "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "pm_hist_scr",     "to": "pm_blend_scr2",  "from_output": "Output",       "to_input": "source"},
        {"from": "pm_blend_scr",    "to": "pm_blend_scr2",  "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "pm_blend_scr2",   "to": "pm_final",       "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "pm_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=shadow_factor, highlight_factor=highlight_factor)


# ─────────────────────────────────────────────────────────────────────────────
# PROFESSIONAL CONCRETE — pro Architecture
# Flood-fill per-crack-island + multi-dir warp + highpass detail
# ─────────────────────────────────────────────────────────────────────────────

def _pro_concrete_recipe(description, color=(0.50, 0.48, 0.46), roughness=0.88, metallic=0.0,
                         crack_density=0.4, surface_roughness=0.5, shadow_factor=0.50, highlight_factor=1.25):
    """Professional concrete — 47 nodes.

    Architecture:
      Stage 1: clouds_2 (macro slabs) + slope_blur × 2 (directional flow)
      Stage 2: crystal_1 (crack network) → edge_detect → flood_fill → ff_to_gradient (slab variation)
      Stage 3: multi_dir_warp × 2 (clouds-driven distortion)
      Stage 4: perlin (surface bumps) → slope_blur (directional) → blend
      Stage 5: highpass (micro pores) + histogram_scan → blend
      Stage 6: directionalwarp × 2 final shaping
    """
    nodes = [
        # ── Stage 1: Macro slab structure
        {"id_alias": "pc_clouds_slab",  "resource_url": LIB["clouds_2"], "position": [-3000, 0],
         "parameters": {"scale": {"value": 2, "type": "int"}, "disorder": {"value": surface_roughness * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pc_clouds_mid",   "resource_url": LIB["clouds_2"], "position": [-3000, 200],
         "parameters": {"scale": {"value": 5, "type": "int"}, "disorder": {"value": surface_roughness * 0.8, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pc_blur_slab",    "resource_url": LIB["blur_hq_grayscale"], "position": [-2800, 0],
         "parameters": {"Intensity": {"value": 5.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pc_slope1",       "resource_url": LIB["slope_blur_grayscale_2"], "position": [-2600, 0],
         "parameters": {"Samples": {"value": 16, "type": "int"}, "Intensity": {"value": 0.4, "type": "float"}, "mode": {"value": 0, "type": "int"}}},
        {"id_alias": "pc_slope2",       "resource_url": LIB["slope_blur_grayscale_2"], "position": [-2400, 0],
         "parameters": {"Samples": {"value": 10, "type": "int"}, "Intensity": {"value": 0.22, "type": "float"}, "mode": {"value": 0, "type": "int"}}},
        {"id_alias": "pc_lvl_slab",     "definition_id": "sbs::compositing::levels", "position": [-2200, 0],
         "parameters": {"levelinlow": [0.1, 0.1, 0.1, 0.1], "levelinhigh": [0.9, 0.9, 0.9, 0.9]}},
        # ── Stage 2: Crack network → flood fill → per-slab variation
        {"id_alias": "pc_crystal_crack","resource_url": LIB["crystal_1"], "position": [-2200, 250],
         "parameters": {"scale": {"value": 4, "type": "int"}, "disorder": {"value": crack_density, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pc_lvl_crack",    "definition_id": "sbs::compositing::levels", "position": [-2000, 250],
         "parameters": {"levelinlow": [0.6, 0.6, 0.6, 0.6], "levelinhigh": [0.9, 0.9, 0.9, 0.9],
                        "leveloutlow": [0.0, 0.0, 0.0, 0.0], "levelouthigh": [1.0, 1.0, 1.0, 1.0]}},
        {"id_alias": "pc_edge_crack",   "resource_url": LIB["edge_detect"], "position": [-2000, 400],
         "parameters": {"edge_width": {"value": 2.0, "type": "float"}, "edge_roundness": {"value": 0.4, "type": "float"}, "tolerance": {"value": 0.35, "type": "float"}}},
        {"id_alias": "pc_flood_crack",  "resource_url": LIB["flood_fill"], "position": [-1800, 400]},
        {"id_alias": "pc_ff_grad",      "resource_url": LIB["flood_fill_to_gradient_2"], "position": [-1600, 400],
         "parameters": {"angle_variation": {"value": 1.0, "type": "float"}}},
        {"id_alias": "pc_ff_gray",      "resource_url": LIB["flood_fill_to_grayscale"], "position": [-1600, 600],
         "parameters": {"luminance_random": {"value": 0.25, "type": "float"}}},
        {"id_alias": "pc_blend_slab",   "definition_id": "sbs::compositing::blend", "position": [-2000, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.25}},
        {"id_alias": "pc_blend_ff",     "definition_id": "sbs::compositing::blend", "position": [-1400, 0],
         "parameters": {"blendingmode": 3, "opacitymult": 0.3}},
        {"id_alias": "pc_lvl_struct",   "definition_id": "sbs::compositing::levels", "position": [-1200, 0],
         "parameters": {"levelinlow": [0.08, 0.08, 0.08, 0.08], "levelinhigh": [0.92, 0.92, 0.92, 0.92]}},
        # ── Stage 3: Multi-directional warp (clouds-driven)
        {"id_alias": "pc_clouds_warp",  "resource_url": LIB["clouds_2"], "position": [-1200, 250],
         "parameters": {"scale": {"value": 8, "type": "int"}, "disorder": {"value": surface_roughness * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pc_multi_warp1",  "resource_url": LIB["multi_directional_warp_grayscale"], "position": [-1000, 0],
         "parameters": {"intensity": {"value": 0.2, "type": "float"}, "warp_angle": {"value": 0.0, "type": "float"}, "directions": {"value": 4, "type": "int"}}},
        {"id_alias": "pc_multi_warp2",  "resource_url": LIB["multi_directional_warp_grayscale"], "position": [-800, 0],
         "parameters": {"intensity": {"value": 0.1, "type": "float"}, "warp_angle": {"value": 0.25, "type": "float"}, "directions": {"value": 6, "type": "int"}}},
        # ── Stage 4: Surface bumps (aggregate) + slope flow
        {"id_alias": "pc_perlin_surf",  "resource_url": LIB["perlin_noise"], "position": [-800, 300],
         "parameters": {"scale": {"value": 16, "type": "int"}, "disorder": {"value": surface_roughness, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pc_slope_surf",   "resource_url": LIB["slope_blur_grayscale_2"], "position": [-600, 300],
         "parameters": {"Samples": {"value": 6, "type": "int"}, "Intensity": {"value": 0.15, "type": "float"}, "mode": {"value": 0, "type": "int"}}},
        {"id_alias": "pc_blend_surf",   "definition_id": "sbs::compositing::blend", "position": [-600, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.22}},
        # ── Stage 5: Micro pores via highpass + histogram
        {"id_alias": "pc_cells_pores",  "resource_url": LIB["cells_1"], "position": [-400, 300],
         "parameters": {"scale": {"value": 24, "type": "int"}, "disorder": {"value": 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pc_highpass",     "resource_url": LIB["highpass_grayscale"], "position": [-400, 450],
         "parameters": {"Radius": {"value": 6.0, "type": "float"}}},
        {"id_alias": "pc_hist_pores",   "resource_url": LIB["histogram_scan"], "position": [-200, 450],
         "parameters": {"Position": {"value": 0.5, "type": "float"}, "Contrast": {"value": 0.7, "type": "float"}}},
        {"id_alias": "pc_blend_pores",  "definition_id": "sbs::compositing::blend", "position": [-400, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.12}},
        {"id_alias": "pc_blend_pores2", "definition_id": "sbs::compositing::blend", "position": [-200, 0],
         "parameters": {"blendingmode": 1, "opacitymult": 0.06}},
        # ── Stage 6: Final directional warp shaping
        {"id_alias": "pc_perlin_fin",   "resource_url": LIB["perlin_noise"], "position": [0, 300],
         "parameters": {"scale": {"value": 6, "type": "int"}, "disorder": {"value": surface_roughness * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "pc_blur_fin",     "resource_url": LIB["blur_hq_grayscale"], "position": [200, 300],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "pc_dir_fin",      "definition_id": "sbs::compositing::directionalwarp", "position": [0, 0],
         "parameters": {"intensity": 0.1}},
        {"id_alias": "pc_final",        "definition_id": "sbs::compositing::levels", "position": [200, 0],
         "parameters": {"levelinlow": [0.05, 0.05, 0.05, 0.05], "levelinhigh": [0.95, 0.95, 0.95, 0.95]}},
    ]
    connections = [
        # Stage 1
        {"from": "pc_clouds_slab",  "to": "pc_blur_slab",   "from_output": "output",       "to_input": "Source"},
        {"from": "pc_blur_slab",    "to": "pc_slope1",      "from_output": "Blur_HQ",      "to_input": "Source"},
        {"from": "pc_clouds_mid",   "to": "pc_slope1",      "from_output": "output",       "to_input": "Effect"},
        {"from": "pc_slope1",       "to": "pc_slope2",      "from_output": "Slope_Blur",   "to_input": "Source"},
        {"from": "pc_clouds_mid",   "to": "pc_slope2",      "from_output": "output",       "to_input": "Effect"},
        {"from": "pc_slope2",       "to": "pc_lvl_slab",    "from_output": "Slope_Blur",   "to_input": "input1"},
        # Stage 2: crack network
        {"from": "pc_crystal_crack","to": "pc_lvl_crack",   "from_output": "output",       "to_input": "input1"},
        {"from": "pc_crystal_crack","to": "pc_edge_crack",  "from_output": "output",       "to_input": "input"},
        {"from": "pc_edge_crack",   "to": "pc_flood_crack", "from_output": "output",       "to_input": "mask"},
        {"from": "pc_flood_crack",  "to": "pc_ff_grad",     "from_output": "output",       "to_input": "input"},
        {"from": "pc_flood_crack",  "to": "pc_ff_gray",     "from_output": "output",       "to_input": "input"},
        {"from": "pc_lvl_crack",    "to": "pc_blend_slab",  "from_output": "unique_filter_output", "to_input": "source"},
        {"from": "pc_lvl_slab",     "to": "pc_blend_slab",  "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "pc_ff_grad",      "to": "pc_blend_ff",    "from_output": "output",       "to_input": "source"},
        {"from": "pc_blend_slab",   "to": "pc_blend_ff",    "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "pc_ff_gray",      "to": "pc_blend_ff",    "from_output": "output",       "to_input": "opacity"},
        {"from": "pc_blend_ff",     "to": "pc_lvl_struct",  "from_output": "unique_filter_output", "to_input": "input1"},
        # Stage 3: multi-dir warp
        {"from": "pc_lvl_struct",   "to": "pc_multi_warp1", "from_output": "unique_filter_output", "to_input": "input"},
        {"from": "pc_clouds_warp",  "to": "pc_multi_warp1", "from_output": "output",       "to_input": "intensity_input"},
        {"from": "pc_multi_warp1",  "to": "pc_multi_warp2", "from_output": "output",       "to_input": "input"},
        {"from": "pc_clouds_warp",  "to": "pc_multi_warp2", "from_output": "output",       "to_input": "intensity_input"},
        # Stage 4: surface bumps
        {"from": "pc_perlin_surf",  "to": "pc_slope_surf",  "from_output": "output",       "to_input": "Source"},
        {"from": "pc_multi_warp2",  "to": "pc_slope_surf",  "from_output": "output",       "to_input": "Effect"},
        {"from": "pc_slope_surf",   "to": "pc_blend_surf",  "from_output": "Slope_Blur",   "to_input": "source"},
        {"from": "pc_multi_warp2",  "to": "pc_blend_surf",  "from_output": "output",       "to_input": "destination"},
        # Stage 5: micro pores
        {"from": "pc_cells_pores",  "to": "pc_highpass",    "from_output": "output",       "to_input": "Source"},
        {"from": "pc_highpass",     "to": "pc_hist_pores",  "from_output": "Highpass",     "to_input": "Input_1"},
        {"from": "pc_cells_pores",  "to": "pc_blend_pores", "from_output": "output",       "to_input": "source"},
        {"from": "pc_blend_surf",   "to": "pc_blend_pores", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "pc_hist_pores",   "to": "pc_blend_pores2","from_output": "Output",       "to_input": "source"},
        {"from": "pc_blend_pores",  "to": "pc_blend_pores2","from_output": "unique_filter_output", "to_input": "destination"},
        # Stage 6: final warp + levels
        {"from": "pc_perlin_fin",   "to": "pc_blur_fin",    "from_output": "output",       "to_input": "Source"},
        {"from": "pc_blend_pores2", "to": "pc_dir_fin",     "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "pc_blur_fin",     "to": "pc_dir_fin",     "from_output": "Blur_HQ",      "to_input": "inputintensity"},
        {"from": "pc_dir_fin",      "to": "pc_final",       "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    return _make_recipe(nodes, connections, "pc_final", color, roughness=roughness, metallic=metallic,
                        description=description, shadow_factor=shadow_factor, highlight_factor=highlight_factor)


# ─────────────────────────────────────────────────────────────────────────────
# RECIPE REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

RECIPE_REGISTRY = {}

def _reg(name, recipe):
    RECIPE_REGISTRY[name] = recipe

# WOOD
_reg("wood_oak",      _wood_base_recipe("wood_oak", "Oak wood — coarse grain, visible rings", perlin_scale=10, perlin_disorder=0.08, ring_scale=6, warp_intensity=0.35, color=(0.38, 0.22, 0.09), roughness=0.78))
_reg("wood_pine",     _wood_base_recipe("wood_pine", "Pine wood — tight vertical grain, pale", perlin_scale=14, perlin_disorder=0.04, ring_scale=10, warp_intensity=0.25, color=(0.55, 0.40, 0.20), roughness=0.72))
_reg("wood_walnut",   _wood_base_recipe("wood_walnut", "Dark walnut — rich wavy grain", perlin_scale=8, perlin_disorder=0.12, ring_scale=5, warp_intensity=0.45, color=(0.22, 0.13, 0.06), roughness=0.65))
_reg("wood_birch",    _wood_base_recipe("wood_birch", "Birch — pale fine grain", perlin_scale=18, perlin_disorder=0.03, ring_scale=14, warp_intensity=0.18, color=(0.75, 0.65, 0.50), roughness=0.70))
_reg("wood_mahogany", _wood_base_recipe("wood_mahogany", "Mahogany — deep red interlocked grain", perlin_scale=7, perlin_disorder=0.15, ring_scale=4, warp_intensity=0.5, color=(0.40, 0.13, 0.08), roughness=0.60))

# ROCK
_reg("rock_granite",   _rock_base_recipe("rock_granite", "Granite — coarse crystalline rock", cells_scale=4, perlin_scale=8, polygon_sides=6, warp_intensity=0.2, slope_samples=10, slope_intensity=0.25, color=(0.55, 0.48, 0.42), roughness=0.85))
_reg("rock_sandstone", _rock_base_recipe("rock_sandstone", "Sandstone — layered sedimentary", cells_scale=2, perlin_scale=4, polygon_sides=4, warp_intensity=0.3, slope_samples=14, slope_intensity=0.35, color=(0.72, 0.58, 0.38), roughness=0.90))
_reg("rock_limestone", _rock_base_recipe("rock_limestone", "Limestone — smooth pale sedimentary", cells_scale=3, perlin_scale=6, polygon_sides=4, warp_intensity=0.15, slope_samples=8, slope_intensity=0.2, color=(0.80, 0.78, 0.72), roughness=0.82))
_reg("rock_slate",     _rock_base_recipe("rock_slate", "Slate — dark layered metamorphic", cells_scale=2, perlin_scale=5, polygon_sides=4, warp_intensity=0.12, slope_samples=16, slope_intensity=0.5, color=(0.28, 0.30, 0.33), roughness=0.80))
_reg("rock_basalt",    _rock_base_recipe("rock_basalt", "Basalt — dark volcanic, fine-grained", cells_scale=5, perlin_scale=10, polygon_sides=6, warp_intensity=0.25, slope_samples=12, slope_intensity=0.3, color=(0.18, 0.18, 0.20), roughness=0.88))
_reg("rock_marble",    _rock_base_recipe("rock_marble", "Marble — metamorphic veining pattern", cells_scale=2, perlin_scale=3, polygon_sides=4, warp_intensity=0.6, slope_samples=6, slope_intensity=0.15, color=(0.88, 0.85, 0.80), roughness=0.20))

# METAL
_reg("metal_steel",    _metal_base_recipe("metal_steel", "Brushed steel — fine directional scratch", perlin_scale=32, perlin_disorder=0.03, scratch_intensity=0.08, color=(0.65, 0.65, 0.68), roughness=0.25, metallic=1.0))
_reg("metal_iron",     _metal_base_recipe("metal_iron", "Cast iron — rough, oxidized surface", perlin_scale=16, perlin_disorder=0.12, scratch_intensity=0.18, color=(0.25, 0.23, 0.22), roughness=0.70, metallic=0.85))
_reg("metal_copper",   _metal_base_recipe("metal_copper", "Copper — warm reddish, slight hammer texture", perlin_scale=24, perlin_disorder=0.08, scratch_intensity=0.12, color=(0.72, 0.42, 0.25), roughness=0.35, metallic=1.0))
_reg("metal_gold",     _metal_base_recipe("metal_gold", "Gold — polished warm yellow metal", perlin_scale=48, perlin_disorder=0.02, scratch_intensity=0.04, color=(0.83, 0.68, 0.22), roughness=0.15, metallic=1.0))
_reg("metal_silver",   _metal_base_recipe("metal_silver", "Silver — highly polished cool white metal", perlin_scale=48, perlin_disorder=0.02, scratch_intensity=0.05, color=(0.87, 0.87, 0.87), roughness=0.12, metallic=1.0))
_reg("metal_aluminum", _metal_base_recipe("metal_aluminum", "Aluminum — light brushed metal", perlin_scale=36, perlin_disorder=0.04, scratch_intensity=0.07, color=(0.75, 0.76, 0.78), roughness=0.28, metallic=1.0))
_reg("metal_rust",     _metal_base_recipe("metal_rust", "Rusty iron — corroded, flaky surface", perlin_scale=12, perlin_disorder=0.25, scratch_intensity=0.3, color=(0.48, 0.22, 0.08), roughness=0.88, metallic=0.3))

# ORGANIC
_reg("moss",    _organic_base_recipe("moss", "Wet moss — lumpy, highly organic texture", clouds_scale=3, clouds_disorder=0.7, cells_scale=8, cells_disorder=0.4, blend_weight=0.6, detail_perlin_scale=16, slope_samples=8, slope_intensity=0.4, color=(0.18, 0.38, 0.12), roughness=0.95))
_reg("bark",    _organic_base_recipe("bark", "Tree bark — rough cracked surface", clouds_scale=2, clouds_disorder=0.5, cells_scale=4, cells_disorder=0.6, blend_weight=0.7, detail_perlin_scale=12, slope_samples=10, slope_intensity=0.5, color=(0.28, 0.20, 0.12), roughness=0.92))
_reg("lichen",  _organic_base_recipe("lichen", "Lichen — patchy crusty growth on rock", clouds_scale=5, clouds_disorder=0.6, cells_scale=10, cells_disorder=0.5, blend_weight=0.5, detail_perlin_scale=20, slope_samples=6, slope_intensity=0.3, color=(0.55, 0.58, 0.28), roughness=0.90))
_reg("bone",    _organic_base_recipe("bone", "Bone — porous dry surface", clouds_scale=4, clouds_disorder=0.3, cells_scale=6, cells_disorder=0.2, blend_weight=0.4, detail_perlin_scale=20, slope_samples=8, slope_intensity=0.2, color=(0.88, 0.82, 0.70), roughness=0.80))
_reg("coral",   _organic_base_recipe("coral", "Coral — rough porous marine growth", clouds_scale=4, clouds_disorder=0.5, cells_scale=8, cells_disorder=0.4, blend_weight=0.55, detail_perlin_scale=14, slope_samples=8, slope_intensity=0.45, color=(0.88, 0.42, 0.28), roughness=0.90))
_reg("shell",   _organic_base_recipe("shell", "Sea shell — smooth ridged surface", clouds_scale=6, clouds_disorder=0.2, cells_scale=12, cells_disorder=0.1, blend_weight=0.35, detail_perlin_scale=24, slope_samples=4, slope_intensity=0.15, color=(0.88, 0.75, 0.60), roughness=0.30))
_reg("leather", _organic_base_recipe("leather", "Leather — pebbled hide surface", clouds_scale=3, clouds_disorder=0.4, cells_scale=8, cells_disorder=0.3, blend_weight=0.5, detail_perlin_scale=18, slope_samples=6, slope_intensity=0.25, color=(0.38, 0.22, 0.12), roughness=0.72))
_reg("skin",    _organic_base_recipe("skin", "Human skin — pores and fine surface detail", clouds_scale=4, clouds_disorder=0.35, cells_scale=12, cells_disorder=0.15, blend_weight=0.4, detail_perlin_scale=32, slope_samples=4, slope_intensity=0.12, color=(0.88, 0.65, 0.52), roughness=0.55))
_reg("scales",  _organic_base_recipe("scales", "Reptile scales — overlapping pattern", clouds_scale=5, clouds_disorder=0.3, cells_scale=6, cells_disorder=0.1, blend_weight=0.45, detail_perlin_scale=12, slope_samples=8, slope_intensity=0.3, color=(0.25, 0.45, 0.28), roughness=0.65))

# SOIL
_reg("soil_sand",   _soil_base_recipe("Sand — fine dry particles, slight dunes", color=(0.78, 0.68, 0.48), roughness=0.92, clouds_scale=5, cells_scale=12, disorder=0.6, crack_intensity=0.15))
_reg("soil_clay",   _soil_base_recipe("Clay — smooth wet earth, crack pattern", color=(0.52, 0.38, 0.28), roughness=0.80, clouds_scale=3, cells_scale=6, disorder=0.3, crack_intensity=0.4))
_reg("soil_mud",    _soil_base_recipe("Mud — thick wet earth, soft deformation", color=(0.28, 0.22, 0.15), roughness=0.85, clouds_scale=3, cells_scale=8, disorder=0.5, crack_intensity=0.25))
_reg("soil_gravel", _soil_base_recipe("Gravel — small rounded stones aggregate", color=(0.48, 0.45, 0.42), roughness=0.88, clouds_scale=6, cells_scale=5, disorder=0.4, crack_intensity=0.2))
_reg("soil_humus",  _soil_base_recipe("Humus — rich dark organic soil", color=(0.18, 0.14, 0.09), roughness=0.90, clouds_scale=4, cells_scale=10, disorder=0.55, crack_intensity=0.2))

# WATER / ICE
_reg("water_calm",  _water_recipe("Calm water surface — gentle ripples", color=(0.15, 0.35, 0.55), roughness=0.05))
_reg("water_ocean", _water_recipe("Ocean waves — larger swell pattern", color=(0.10, 0.28, 0.48), roughness=0.10))
_reg("ice",         _ice_recipe("Ice — clear faceted frozen surface", color=(0.65, 0.82, 0.90), roughness=0.08))
_reg("snow",        _organic_base_recipe("snow", "Snow — soft granular compressed snow surface", clouds_scale=5, clouds_disorder=0.8, cells_scale=16, cells_disorder=0.6, blend_weight=0.6, detail_perlin_scale=24, slope_samples=4, slope_intensity=0.15, color=(0.95, 0.95, 1.0), roughness=0.92))

# GEMS
_reg("gem_diamond",  _gem_recipe("Diamond — near-perfect faceted crystal", color=(0.90, 0.95, 1.00), roughness=0.02))
_reg("gem_ruby",     _gem_recipe("Ruby — deep red faceted gem", color=(0.75, 0.08, 0.08), roughness=0.03))
_reg("gem_sapphire", _gem_recipe("Sapphire — rich blue faceted gem", color=(0.10, 0.18, 0.80), roughness=0.03))
_reg("gem_emerald",  _gem_recipe("Emerald — deep green faceted gem", color=(0.05, 0.65, 0.22), roughness=0.04))
_reg("gem_amethyst", _gem_recipe("Amethyst — purple quartz crystal", color=(0.55, 0.20, 0.72), roughness=0.05))

# CONCRETE / MASONRY
_reg("concrete",          _concrete_recipe("Poured concrete — large aggregate, crack network", color=(0.52, 0.50, 0.48), roughness=0.88, crack_intensity=0.4, detail_scale=16, disorder=0.4))
_reg("concrete_aged",     _concrete_recipe("Aged concrete — weathered, more cracks and staining", color=(0.42, 0.40, 0.38), roughness=0.92, crack_intensity=0.6, detail_scale=20, disorder=0.6))
_reg("concrete_smooth",   _concrete_recipe("Smooth concrete — polished cast surface, minimal cracks", color=(0.60, 0.58, 0.56), roughness=0.70, crack_intensity=0.15, detail_scale=24, disorder=0.2))

# BRICK
_reg("brick_red",         _brick_recipe("Classic red brick — fired clay, rough mortar joints", color=(0.55, 0.28, 0.16), roughness=0.87, brick_scale=4, mortar_width=0.06, disorder=0.3))
_reg("brick_old",         _brick_recipe("Old weathered brick — irregular, spalled edges", color=(0.45, 0.22, 0.12), roughness=0.92, brick_scale=3, mortar_width=0.09, disorder=0.55))
_reg("brick_white",       _brick_recipe("White painted brick — thin coat on masonry", color=(0.88, 0.85, 0.82), roughness=0.78, brick_scale=4, mortar_width=0.05, disorder=0.2))

# LAVA / VOLCANIC
_reg("lava_fresh",        _lava_recipe("Fresh lava — active flow, glowing crack channels", color=(0.08, 0.04, 0.03), roughness=0.93))
_reg("lava_cooled",       _lava_recipe("Cooled lava — solidified basalt crust, dark fissures", color=(0.14, 0.12, 0.11), roughness=0.90))

# ASPHALT / ROAD
_reg("asphalt",           _asphalt_recipe("Road asphalt — aggregate bitumen, tyre wear", color=(0.18, 0.17, 0.16), roughness=0.90, aggregate_scale=8, wear=0.3))
_reg("asphalt_worn",      _asphalt_recipe("Worn asphalt — heavily weathered, exposed aggregate", color=(0.25, 0.23, 0.20), roughness=0.93, aggregate_scale=6, wear=0.7))

# PLASTER / STUCCO
_reg("plaster",           _plaster_recipe("Fresh plaster — smooth, slight trowel marks", color=(0.90, 0.87, 0.82), roughness=0.68, crack_density=0.15, smoothness=0.85))
_reg("plaster_cracked",   _plaster_recipe("Cracked plaster — aged, hairline crack network", color=(0.82, 0.78, 0.72), roughness=0.75, crack_density=0.55, smoothness=0.65))
_reg("stucco",            _plaster_recipe("Stucco — rough textured exterior coat", color=(0.78, 0.72, 0.62), roughness=0.85, crack_density=0.3, smoothness=0.45))

# FABRIC / CLOTH
_reg("fabric_denim",      _fabric_recipe("Denim — tight twill weave, indigo cotton", color=(0.22, 0.32, 0.52), roughness=0.85, thread_scale=16, weave_disorder=0.15))
_reg("fabric_canvas",     _fabric_recipe("Canvas — coarse plain weave, natural fiber", color=(0.72, 0.62, 0.45), roughness=0.88, thread_scale=10, weave_disorder=0.25))
_reg("fabric_silk",       _fabric_recipe("Silk — very fine smooth weave, high sheen", color=(0.85, 0.78, 0.72), roughness=0.30, thread_scale=24, weave_disorder=0.08))
_reg("fabric_wool",       _fabric_recipe("Wool felt — loose fluffy texture, matte", color=(0.55, 0.42, 0.35), roughness=0.95, thread_scale=8, weave_disorder=0.45))
_reg("fabric_velvet",     _fabric_recipe("Velvet — plush pile surface, directional sheen", color=(0.35, 0.12, 0.28), roughness=0.60, thread_scale=20, weave_disorder=0.20))

# CERAMIC / TILE
_reg("tile_ceramic",      _tile_recipe("White ceramic tile — glazed, regular grid with grout", color=(0.92, 0.90, 0.88), roughness=0.18, tile_scale=4, grout_depth=0.10))
_reg("tile_terracotta",   _tile_recipe("Terracotta floor tile — matte fired clay, wide grout", color=(0.65, 0.35, 0.20), roughness=0.80, tile_scale=3, grout_depth=0.14))
_reg("tile_stone",        _tile_recipe("Stone tile — cut natural stone, tight grout", color=(0.48, 0.45, 0.40), roughness=0.72, tile_scale=4, grout_depth=0.08))

# SPECIALTY MATERIALS
_reg("terracotta",        _terracotta_recipe("Terracotta pot — coarse fired clay, wheel marks", color=(0.62, 0.32, 0.18), roughness=0.82))
_reg("obsidian",          _obsidian_recipe("Obsidian — volcanic glass, conchoidal fractures", color=(0.05, 0.04, 0.06), roughness=0.05))
_reg("carbon_fiber",      _carbon_fiber_recipe("Carbon fiber — woven composite, high-tech surface", color=(0.08, 0.08, 0.09), roughness=0.20))
_reg("painted_metal",     _painted_metal_recipe("Painted metal — smooth coat with chips and dents", color=(0.22, 0.35, 0.58), roughness=0.30, chip_density=0.25))
_reg("painted_metal_worn",_painted_metal_recipe("Worn painted metal — heavy chipping, exposed substrate", color=(0.28, 0.25, 0.22), roughness=0.55, chip_density=0.55, dent_intensity=0.28))

# MAIN SHAPE — pro exact reconstruction (11 nodes, from live data)
_reg("main_shape", _main_shape_recipe())

# PROFESSIONAL GRADE — pro Architecture (53+ nodes each)
# Uses: clouds_2 + slope_blur cascade + edge_detect + flood_fill chain
#       + multi_directional_warp + directionalwarp × N + highpass + histogram_scan
_reg("pro_granite",     _pro_rock_recipe("Professional granite — crystalline rock, per-island variation", color=(0.52, 0.45, 0.40), roughness=0.88, macro_scale=2, mid_scale=5, detail_scale=10, disorder=0.45, shadow_factor=0.40, highlight_factor=1.40))
_reg("pro_limestone",   _pro_rock_recipe("Professional limestone — pale sedimentary, cavity network", color=(0.80, 0.76, 0.68), roughness=0.82, macro_scale=3, mid_scale=7, detail_scale=14, disorder=0.35, shadow_factor=0.45, highlight_factor=1.30))
_reg("pro_sandstone",   _pro_rock_recipe("Professional sandstone — layered with sediment variation", color=(0.72, 0.58, 0.38), roughness=0.90, macro_scale=2, mid_scale=4, detail_scale=8, disorder=0.55, shadow_factor=0.42, highlight_factor=1.25))
_reg("pro_basalt",      _pro_rock_recipe("Professional basalt — dark volcanic, columnar structure", color=(0.18, 0.18, 0.20), roughness=0.88, macro_scale=3, mid_scale=6, detail_scale=12, disorder=0.4, shadow_factor=0.35, highlight_factor=1.50))
_reg("pro_slate",       _pro_rock_recipe("Professional slate — layered metamorphic, fracture planes", color=(0.28, 0.30, 0.33), roughness=0.80, macro_scale=2, mid_scale=5, detail_scale=10, disorder=0.30, shadow_factor=0.40, highlight_factor=1.35))
_reg("pro_steel",       _pro_metal_recipe("Professional brushed steel — anisotropic grain, wear zones", color=(0.65, 0.65, 0.68), roughness=0.22, metallic=1.0, scratch_scale=32, wear_intensity=0.15, shadow_factor=0.25, highlight_factor=1.60))
_reg("pro_iron",        _pro_metal_recipe("Professional cast iron — rough grain, oxidized wear", color=(0.25, 0.23, 0.22), roughness=0.72, metallic=0.85, scratch_scale=16, wear_intensity=0.35, shadow_factor=0.30, highlight_factor=1.40))
_reg("pro_copper",      _pro_metal_recipe("Professional copper — hammered texture, patina zones", color=(0.72, 0.42, 0.25), roughness=0.32, metallic=1.0, scratch_scale=20, wear_intensity=0.25, shadow_factor=0.30, highlight_factor=1.45))
_reg("pro_concrete",    _pro_concrete_recipe("Professional concrete — slab variation, aggregate pores", color=(0.50, 0.48, 0.46), roughness=0.88, crack_density=0.4, surface_roughness=0.5, shadow_factor=0.48, highlight_factor=1.28))
_reg("pro_concrete_aged", _pro_concrete_recipe("Professional aged concrete — heavy cracks, stained slabs", color=(0.40, 0.38, 0.36), roughness=0.92, crack_density=0.65, surface_roughness=0.7, shadow_factor=0.40, highlight_factor=1.35))
_reg("pro_concrete_smooth", _pro_concrete_recipe("Professional smooth concrete — minimal cracks, fine pores", color=(0.60, 0.58, 0.56), roughness=0.72, crack_density=0.2, surface_roughness=0.3, shadow_factor=0.52, highlight_factor=1.22))


# ─────────────────────────────────────────────────────────────────────────────
# HEIGHTMAP RECIPES
# ─────────────────────────────────────────────────────────────────────────────

def _hm_output(height_alias):
    return (
        [{"id_alias": "hm_out", "definition_id": "sbs::compositing::output", "usage": "height", "label": "Height", "position": [2000, 0]}],
        [{"from": height_alias, "to": "hm_out", "from_output": "unique_filter_output", "to_input": "inputNodeOutput"}],
    )


def _hm_rock(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_cells", "resource_url": LIB["cells_1"], "position": [-600, 0],
         "parameters": {"scale": {"value": max(1, int(int_scale * 0.6)), "type": "int"}, "disorder": {"value": disorder, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_perlin", "resource_url": LIB["perlin_noise"], "position": [-600, 200],
         "parameters": {"scale": {"value": int_scale * detail_level, "type": "int"}, "disorder": {"value": disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend", "definition_id": "sbs::compositing::blend", "position": [-400, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.4}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-200, 200],
         "parameters": {"Intensity": {"value": 3.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp", "definition_id": "sbs::compositing::warp", "position": [-200, 0], "parameters": {"intensity": disorder * 0.5}},
        {"id_alias": "hm_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [0, 0],
         "parameters": {"Samples": {"value": 8 + detail_level * 2, "type": "int"}, "Intensity": {"value": 0.3, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [200, 0]},
    ]
    conns = [
        {"from": "hm_perlin", "to": "hm_blend", "from_output": "output", "to_input": "source"},
        {"from": "hm_cells", "to": "hm_blend", "from_output": "output", "to_input": "destination"},
        {"from": "hm_perlin", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend", "to": "hm_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp", "to": "hm_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "hm_blur", "to": "hm_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "hm_slope", "to": "hm_final", "from_output": "Slope_Blur", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


def _hm_cliff(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_perlin", "resource_url": LIB["perlin_noise"], "position": [-800, 0],
         "parameters": {"scale": {"value": int_scale, "type": "int"}, "disorder": {"value": disorder * 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_stretch", "definition_id": "sbs::compositing::transformation", "position": [-600, 0],
         "parameters": {"matrix22": [1.0, 0.0, 0.0, 3.0]}},
        {"id_alias": "hm_cells", "resource_url": LIB["cells_1"], "position": [-600, 200],
         "parameters": {"scale": {"value": max(1, int_scale // 2), "type": "int"}, "disorder": {"value": disorder * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend", "definition_id": "sbs::compositing::blend", "position": [-400, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.35}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-400, 200],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp", "definition_id": "sbs::compositing::warp", "position": [-200, 0], "parameters": {"intensity": disorder * 0.4}},
        {"id_alias": "hm_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [0, 0],
         "parameters": {"Samples": {"value": 10 + detail_level * 2, "type": "int"}, "Intensity": {"value": 0.5, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [200, 0]},
    ]
    conns = [
        {"from": "hm_perlin", "to": "hm_stretch", "from_output": "output", "to_input": "input1"},
        {"from": "hm_cells", "to": "hm_blend", "from_output": "output", "to_input": "source"},
        {"from": "hm_stretch", "to": "hm_blend", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "hm_cells", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend", "to": "hm_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp", "to": "hm_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "hm_blur", "to": "hm_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "hm_slope", "to": "hm_final", "from_output": "Slope_Blur", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


def _hm_sand(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_perlin_low", "resource_url": LIB["perlin_noise"], "position": [-800, 0],
         "parameters": {"scale": {"value": max(1, int_scale // 2), "type": "int"}, "disorder": {"value": disorder * 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_perlin_high", "resource_url": LIB["perlin_noise"], "position": [-800, 200],
         "parameters": {"scale": {"value": int_scale * 3, "type": "int"}, "disorder": {"value": disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend", "definition_id": "sbs::compositing::blend", "position": [-600, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.2}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 8.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp", "definition_id": "sbs::compositing::warp", "position": [-400, 0], "parameters": {"intensity": disorder * 0.25}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [-200, 0],
         "parameters": {"leveloutlow": [0.3, 0.3, 0.3, 0.3], "levelouthigh": [0.7, 0.7, 0.7, 0.7]}},
    ]
    conns = [
        {"from": "hm_perlin_high", "to": "hm_blend", "from_output": "output", "to_input": "source"},
        {"from": "hm_perlin_low", "to": "hm_blend", "from_output": "output", "to_input": "destination"},
        {"from": "hm_perlin_high", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend", "to": "hm_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp", "to": "hm_final", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


def _hm_cracked(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_cells", "resource_url": LIB["cells_2"], "position": [-800, 0],
         "parameters": {"scale": {"value": int_scale, "type": "int"}, "disorder": {"value": disorder * 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_perlin", "resource_url": LIB["perlin_noise"], "position": [-800, 200],
         "parameters": {"scale": {"value": int_scale * 2, "type": "int"}, "disorder": {"value": disorder * 0.7, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend", "definition_id": "sbs::compositing::blend", "position": [-600, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.3}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 2.5, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-400, 0],
         "parameters": {"Samples": {"value": 12 + detail_level * 2, "type": "int"}, "Intensity": {"value": 0.6, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "hm_warp", "definition_id": "sbs::compositing::warp", "position": [-200, 0], "parameters": {"intensity": disorder * 0.35}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    conns = [
        {"from": "hm_perlin", "to": "hm_blend", "from_output": "output", "to_input": "source"},
        {"from": "hm_cells", "to": "hm_blend", "from_output": "output", "to_input": "destination"},
        {"from": "hm_perlin", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend", "to": "hm_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "hm_blur", "to": "hm_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "hm_slope", "to": "hm_warp", "from_output": "Slope_Blur", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp", "to": "hm_final", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


def _hm_mud(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_clouds", "resource_url": LIB["clouds_2"], "position": [-800, 0],
         "parameters": {"scale": {"value": max(1, int_scale // 2), "type": "int"}, "disorder": {"value": disorder * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_cells", "resource_url": LIB["cells_1"], "position": [-800, 200],
         "parameters": {"scale": {"value": int_scale, "type": "int"}, "disorder": {"value": disorder * 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend", "definition_id": "sbs::compositing::blend", "position": [-600, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.45}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 4.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp", "definition_id": "sbs::compositing::warp", "position": [-400, 0], "parameters": {"intensity": disorder * 0.3}},
        {"id_alias": "hm_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": 6 + detail_level, "type": "int"}, "Intensity": {"value": 0.25, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    conns = [
        {"from": "hm_cells", "to": "hm_blend", "from_output": "output", "to_input": "source"},
        {"from": "hm_clouds", "to": "hm_blend", "from_output": "output", "to_input": "destination"},
        {"from": "hm_cells", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend", "to": "hm_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp", "to": "hm_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "hm_blur", "to": "hm_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "hm_slope", "to": "hm_final", "from_output": "Slope_Blur", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


def _hm_mountain(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_perlin", "resource_url": LIB["perlin_noise"], "position": [-800, 0],
         "parameters": {"scale": {"value": max(1, int_scale // 2), "type": "int"}, "disorder": {"value": disorder * 0.3, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_crystal", "resource_url": LIB["crystal_1"], "position": [-800, 200],
         "parameters": {"scale": {"value": int_scale, "type": "int"}, "disorder": {"value": disorder * 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend", "definition_id": "sbs::compositing::blend", "position": [-600, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.35}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 5.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp1", "definition_id": "sbs::compositing::warp", "position": [-400, 0], "parameters": {"intensity": disorder * 0.4}},
        {"id_alias": "hm_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": 8 + detail_level * 2, "type": "int"}, "Intensity": {"value": 0.4, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "hm_perlin2", "resource_url": LIB["perlin_noise"], "position": [0, 200],
         "parameters": {"scale": {"value": int_scale * 3, "type": "int"}, "disorder": {"value": disorder * 0.5, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blur2", "resource_url": LIB["blur_hq_grayscale"], "position": [200, 200],
         "parameters": {"Intensity": {"value": 8.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp2", "definition_id": "sbs::compositing::warp", "position": [0, 0], "parameters": {"intensity": disorder * 0.2}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [200, 0]},
    ]
    conns = [
        {"from": "hm_crystal", "to": "hm_blend", "from_output": "output", "to_input": "source"},
        {"from": "hm_perlin", "to": "hm_blend", "from_output": "output", "to_input": "destination"},
        {"from": "hm_crystal", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend", "to": "hm_warp1", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp1", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp1", "to": "hm_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "hm_blur", "to": "hm_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "hm_perlin2", "to": "hm_blur2", "from_output": "output", "to_input": "Source"},
        {"from": "hm_slope", "to": "hm_warp2", "from_output": "Slope_Blur", "to_input": "input1"},
        {"from": "hm_blur2", "to": "hm_warp2", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp2", "to": "hm_final", "from_output": "unique_filter_output", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


def _hm_cobblestone(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_poly", "resource_url": LIB["polygon_2"], "position": [-800, 0],
         "parameters": {"Tiling": {"value": int_scale, "type": "int"}, "Sides": {"value": 6, "type": "int"}, "Scale": {"value": 0.85, "type": "float"}, "Gradient": {"value": 1.0, "type": "float"}}},
        {"id_alias": "hm_perlin", "resource_url": LIB["perlin_noise"], "position": [-800, 200],
         "parameters": {"scale": {"value": int_scale * 2, "type": "int"}, "disorder": {"value": disorder * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend", "definition_id": "sbs::compositing::blend", "position": [-600, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.15}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 200],
         "parameters": {"Intensity": {"value": 2.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp", "definition_id": "sbs::compositing::warp", "position": [-400, 0], "parameters": {"intensity": disorder * 0.2}},
        {"id_alias": "hm_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": 6 + detail_level, "type": "int"}, "Intensity": {"value": 0.2, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    conns = [
        {"from": "hm_perlin", "to": "hm_blend", "from_output": "output", "to_input": "source"},
        {"from": "hm_poly", "to": "hm_blend", "from_output": "output", "to_input": "destination"},
        {"from": "hm_perlin", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend", "to": "hm_warp", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp", "to": "hm_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "hm_blur", "to": "hm_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "hm_slope", "to": "hm_final", "from_output": "Slope_Blur", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


def _hm_terrain(detail_level=3, scale=5.0, disorder=0.5):
    int_scale = max(1, int(scale))
    nodes = [
        {"id_alias": "hm_perlin_macro", "resource_url": LIB["perlin_noise"], "position": [-1000, 0],
         "parameters": {"scale": {"value": max(1, int_scale // 3), "type": "int"}, "disorder": {"value": disorder * 0.2, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_perlin_mid", "resource_url": LIB["perlin_noise"], "position": [-1000, 200],
         "parameters": {"scale": {"value": int_scale, "type": "int"}, "disorder": {"value": disorder * 0.4, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_perlin_fine", "resource_url": LIB["perlin_noise"], "position": [-1000, 400],
         "parameters": {"scale": {"value": int_scale * 4, "type": "int"}, "disorder": {"value": disorder * 0.6, "type": "float"}, "non_square_expansion": {"value": True, "type": "bool"}}},
        {"id_alias": "hm_blend1", "definition_id": "sbs::compositing::blend", "position": [-800, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.35}},
        {"id_alias": "hm_blend2", "definition_id": "sbs::compositing::blend", "position": [-600, 0], "parameters": {"blendingmode": 1, "opacitymult": 0.15}},
        {"id_alias": "hm_blur", "resource_url": LIB["blur_hq_grayscale"], "position": [-600, 300],
         "parameters": {"Intensity": {"value": 6.0, "type": "float"}, "Quality": {"value": 0, "type": "int"}}},
        {"id_alias": "hm_warp1", "definition_id": "sbs::compositing::warp", "position": [-400, 0], "parameters": {"intensity": disorder * 0.35}},
        {"id_alias": "hm_slope", "resource_url": LIB["slope_blur_grayscale_2"], "position": [-200, 0],
         "parameters": {"Samples": {"value": 6 + detail_level * 2, "type": "int"}, "Intensity": {"value": 0.3, "type": "float"}, "mode": {"value": 7, "type": "int"}}},
        {"id_alias": "hm_final", "definition_id": "sbs::compositing::levels", "position": [0, 0]},
    ]
    conns = [
        {"from": "hm_perlin_mid", "to": "hm_blend1", "from_output": "output", "to_input": "source"},
        {"from": "hm_perlin_macro", "to": "hm_blend1", "from_output": "output", "to_input": "destination"},
        {"from": "hm_perlin_fine", "to": "hm_blend2", "from_output": "output", "to_input": "source"},
        {"from": "hm_blend1", "to": "hm_blend2", "from_output": "unique_filter_output", "to_input": "destination"},
        {"from": "hm_perlin_mid", "to": "hm_blur", "from_output": "output", "to_input": "Source"},
        {"from": "hm_blend2", "to": "hm_warp1", "from_output": "unique_filter_output", "to_input": "input1"},
        {"from": "hm_blur", "to": "hm_warp1", "from_output": "Blur_HQ", "to_input": "inputgradient"},
        {"from": "hm_warp1", "to": "hm_slope", "from_output": "unique_filter_output", "to_input": "Source"},
        {"from": "hm_blur", "to": "hm_slope", "from_output": "Blur_HQ", "to_input": "Effect"},
        {"from": "hm_slope", "to": "hm_final", "from_output": "Slope_Blur", "to_input": "input1"},
    ]
    out_nodes, out_conns = _hm_output("hm_final")
    return {"nodes": nodes + out_nodes, "connections": conns + out_conns}


HEIGHTMAP_RECIPES = {
    "rock":        _hm_rock,
    "cliff":       _hm_cliff,
    "sand":        _hm_sand,
    "cracked":     _hm_cracked,
    "mud":         _hm_mud,
    "mountain":    _hm_mountain,
    "cobblestone": _hm_cobblestone,
    "terrain":     _hm_terrain,
}


def get_recipe(name):
    return RECIPE_REGISTRY.get(name)


def get_heightmap_recipe(style, detail_level=3, scale=5.0, disorder=0.5):
    fn = HEIGHTMAP_RECIPES.get(style)
    if fn is None:
        return None
    return fn(detail_level=detail_level, scale=scale, disorder=disorder)


def list_recipes():
    return sorted(RECIPE_REGISTRY.keys())


def list_heightmap_styles():
    return sorted(HEIGHTMAP_RECIPES.keys())
