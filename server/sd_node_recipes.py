"""
sd_node_recipes.py
Substance Designer Procedural Texture Recipes
Researched 2026-02-18 from Adobe official docs, 80.lv, TurboSquid, Overdraw.xyz,
and community breakdowns. For use by the SD MCP plugin and Claude Code.

ATOMIC NODES (use create_node with definition_id):
    sbs::compositing::blend
    sbs::compositing::levels
    sbs::compositing::curve
    sbs::compositing::hsl
    sbs::compositing::blur
    sbs::compositing::sharpen
    sbs::compositing::warp
    sbs::compositing::directionalwarp
    sbs::compositing::emboss
    sbs::compositing::transformation
    sbs::compositing::distance
    sbs::compositing::grayscaleconversion
    sbs::compositing::shuffle
    sbs::compositing::pixelprocessor
    sbs::compositing::fxmaps
    sbs::compositing::normal
    sbs::compositing::uniform
    sbs::compositing::output
    sbs::compositing::gradient            (Gradient Map - maps grayscale to color)
    sbs::compositing::gradient_dynamic    (Gradient Dynamic - generates gradients)

LIBRARY NODES (use create_instance_node with resource_url from get_library_nodes):
    Always call get_library_nodes(filter_text="cells") etc. to get exact pkg:// URLs.
    Known library node names and their output port IDs (SD 15.0.3):
        cells_1               -> output: "output"
        perlin_noise          -> output: "output"
        polygon_2             -> output: "output"
        gradient_linear_1     -> output: "Simple_Gradient"
        gradient_axial        -> output: "output"
        clouds_1              -> output: "output"
        clouds_2              -> output: "output"
        voronoi               -> output: "output"
        voronoi_fractal       -> output: "output"
        tile_generator        -> output: "unique_filter_output"
        tile_sampler          -> output: "unique_filter_output"
        flood_fill            -> output: "unique_filter_output"
        flood_fill_to_random_grayscale -> output: "unique_filter_output"
        flood_fill_to_gradient -> output: "unique_filter_output"
        edge_detect           -> output: "unique_filter_output"
        bevel                 -> output_height: "output_height", output_normal: "output_normal"
        curvature_smooth      -> output_concave: "output_concave", output_convex: "output_convex"
        histogram_scan        -> output: "unique_filter_output"
        histogram_select      -> output: "unique_filter_output"
        ambient_occlusion_hbao -> output: "unique_filter_output"
        slope_blur_grayscale  -> output: "unique_filter_output"
        non_uniform_blur_grayscale -> output: "unique_filter_output"
        height_blend          -> output: "unique_filter_output"
        grunge_map_001        -> output: "output"
        grunge_map_002        -> output: "output"
        grunge_concrete       -> output: "output"
        grunge_scratches_rough -> output: "output"
        grunge_spots          -> output: "output"
        directional_noise_1   -> output: "output"
        gaussian_noise        -> output: "output"
        gaussian_spots_1      -> output: "output"
        fractal_sum_base      -> output: "output"
        weave_generator       -> output: "unique_filter_output"
        weave_2               -> output: "unique_filter_output"

ATOMIC NODE INPUT PORT NAMES:
    blend          -> source (fg), destination (bg), opacity (mask)
    levels         -> input1
    curve          -> input1
    hsl            -> input1
    blur           -> input1
    sharpen        -> input1
    warp           -> input1 (image), inputgradient (warp intensity map)
    directionalwarp -> input1 (image), inputintensity (warp map) -- NOT inputgradient!
    normal         -> input1
    transformation -> input1
    distance       -> input1
    grayscaleconversion -> input1
    shuffle        -> input1
    emboss         -> input1
    output         -> inputNodeOutput
    gradient_map   -> input1 (grayscale), gradient (gradient definition)

BLEND MODES (set via blendingmode parameter, int):
    0  = Copy (Normal)
    1  = Add
    2  = Subtract
    3  = Multiply
    4  = Max (Lighten)
    5  = Min (Darken)
    6  = Linear Dodge (Add)
    9  = Overlay
    10 = Screen
    11 = Soft Light
    12 = Hard Light

PARAMETER TYPES for set_parameter:
    float, int, bool, string, float2, float3, float4, color (RGBA 0-1), int2, int3, int4
    $outputsize: int2, e.g. [11, 11] = 2048x2048, [10, 10] = 1024x1024

================================================================================
SECTION 1: STONE / ROCK HEIGHT MAP RECIPES
================================================================================

RECIPE: Rocky Ground Height Map (Foundation Recipe)
    Purpose: Organic, varied rocky ground with small, medium, and large stones
    Approach: Cells-based shape generation with Flood Fill variation
    Key nodes:
        1. cells_1  (LIBRARY)
               parameters: Scale=5, Disorder=0.5
               output port: "output"
        2. edge_detect  (LIBRARY)
               input: cells_1 output
               parameters: EdgeWidth=0.01, EdgeRoundness=0.5
        3. flood_fill  (LIBRARY)
               input: edge_detect output
        4. flood_fill_to_random_grayscale  (LIBRARY)
               input: flood_fill output
               -- gives each rock cell a unique height value
        5. bevel  (LIBRARY)
               input: flood_fill_to_random_grayscale output -> input_height
               parameters: Distance=0.15, CornerType=Round, Smoothing=1.0
               output port for height: "output_height"
        6. perlin_noise  (LIBRARY)
               parameters: Scale=4, Disorder=0.6
               -- used as detail overlay
        7. blend  (ATOMIC)
               source: perlin_noise, destination: bevel output_height
               blendingmode: 3 (Multiply), opacitymult: 0.3
               -- subtle height variation within each stone
        8. levels  (ATOMIC)
               input: blend output
               -- remap: push black point up to 0.1, keep white at 1.0
        9. normal  (ATOMIC)
               input: levels output
               -- generates normal map from height
        10. ambient_occlusion_hbao  (LIBRARY)
               input: levels output (the height map)
               parameters: Quality=4 (samples), HeightScale=3.0

    Connection pattern:
        cells_1 -> edge_detect -> flood_fill -> flood_fill_to_random_grayscale
                                                         |
                                                       bevel (height) ----> blend(dest)
                                                                               |
                                        perlin_noise ----------------> blend(source)
                                                                               |
                                                                            levels -> HEIGHT_OUTPUT
                                                                            levels -> normal -> NORMAL_OUTPUT
                                                                            levels -> AO_HBAO -> AO_OUTPUT

    Notes:
        - Vary cells_1 Scale between 3-8 for different stone size distributions
        - Bevel Distance 0.05-0.3 controls stone roundness vs sharpness
        - The Multiply blend of Perlin adds micro-surface variation
        - cells_1 Disorder 0.3-0.8 controls organic vs regular spacing

---

RECIPE: Multi-Frequency Rock Detail (3-Octave Approach)
    Purpose: Realistic rock surface with macro shape, mid detail, and micro roughness
    Based on: TurboSquid/80.lv rock detail breakdowns
    Approach: Three separate Perlin noises at different scales blended together

    Node chain:
        1. perlin_noise  (LIBRARY) -- MACRO
               parameters: Scale=2, Disorder=0.5
               -- large boulder-scale variation

        2. perlin_noise  (LIBRARY) -- MID
               parameters: Scale=8, Disorder=0.4
               -- medium surface undulation

        3. perlin_noise  (LIBRARY) -- MICRO
               parameters: Scale=20, Disorder=0.3
               -- fine surface grain

        4. blend  (ATOMIC) -- macro + mid
               source: perlin_mid, destination: perlin_macro
               blendingmode: 1 (Add), opacitymult: 0.4

        5. blend  (ATOMIC) -- add micro
               source: perlin_micro, destination: blend_4 output
               blendingmode: 1 (Add), opacitymult: 0.15

        6. levels  (ATOMIC) -- compress range
               input: blend_5 output
               levelinlow=[0.1,0.1,0.1,0.1], levelinhigh=[0.9,0.9,0.9,0.9]

        7. warp  (ATOMIC) -- organic breakup
               input1: levels output
               inputgradient: perlin_macro (reuse)
               intensity: 15.0

        8. normal  (ATOMIC)
               input: warp output -> HEIGHT_OUTPUT
               output -> NORMAL_OUTPUT

    Notes:
        - Adjust Add blend opacities to taste: macro=dominant, micro=subtle
        - Warp intensity 10-30 controls how "melted" vs angular the result looks
        - For sedimentary rock: add a directional_noise_1 node and blend with Overlay

---

RECIPE: Cracked Stone / Dry Ground (Voronoi-Based)
    Purpose: Cracked earth, dry mud, cracked clay, cracked stone pavement
    Based on: 80.lv mineral mud breakdown by Dzmitry Yafimau

    Node chain:
        1. voronoi  (LIBRARY) -- SMALL cracks
               parameters: Scale=8, Style=F2-F1 (outputs crack borders), Disorder=0.3
               output port: "output"

        2. voronoi  (LIBRARY) -- MEDIUM cracks
               parameters: Scale=4, Style=F2-F1, Disorder=0.2

        3. edge_detect  (LIBRARY)
               input: voronoi_medium output
               parameters: EdgeWidth=0.005, EdgeRoundness=0.0

        4. flood_fill  (LIBRARY)
               input: edge_detect output

        5. flood_fill_to_random_grayscale  (LIBRARY)
               input: flood_fill output
               -- gives each crack polygon a unique height value

        6. bevel  (LIBRARY)
               input: flood_fill_to_random_grayscale output -> input_height
               parameters: Distance=0.08, CornerType=Round, Smoothing=2.0
               -- creates curved surface between cracks

        7. warp  (ATOMIC)
               input1: bevel output_height
               inputgradient: voronoi_small output
               intensity: 8.0
               -- warp the bevel using small voronoi = jagged crack edges

        8. slope_blur_grayscale  (LIBRARY)
               input_grayscale: warp output
               input_slope: voronoi_small output
               parameters: Samples=8, Intensity=-0.3
               -- pinch crack terminations for realistic look

        9. non_uniform_blur_grayscale  (LIBRARY)
               input: slope_blur output
               parameters: Intensity=4.0, Anisotropy=0.8
               -- smooth the crack interiors

        10. levels  (ATOMIC)
               -- adjust final contrast and floor level

        11. normal  (ATOMIC)
               input: levels output -> HEIGHT_OUTPUT

    Notes:
        - Voronoi Style options: F1, F2, F2-F1, Edge -- "Edge" gives thinnest cracks
        - Voronoi Disorder 0.0 = geometric grid, 1.0 = fully random
        - Chain 2-3 non_uniform_blur_grayscale nodes (low intensity each)
          rather than 1 high-intensity node to avoid artifacts
        - For wet mud look: increase bevel Distance to 0.2+, Smoothing to 3.0

---

RECIPE: Tile-Sampler Rock Scatter (Height Blend Approach)
    Purpose: Scattered rocks on ground, stones on sand, pebble beach
    Based on: Tom Jacobs rocky ground breakdown from 80.lv

    Node chain:
        1. cells_1  (LIBRARY)
               parameters: Scale=6, Disorder=0.7
               -- drives position/size distribution

        2. perlin_noise  (LIBRARY)
               parameters: Scale=3, Disorder=0.5
               -- used as Scale Map for tile sampler

        3. tile_sampler  (LIBRARY)
               Pattern: Half Bell (built-in), X=4, Y=4
               ScaleMap input: perlin_noise output
               ScaleMapMultiplier: 0.8
               -- or use custom rock silhouette as Pattern Input
               LuminanceVariation: 0.5, RotationRandom: 1.0

        4. bevel  (LIBRARY)
               input: tile_sampler output -> input_height
               parameters: Distance=0.2, CornerType=Round, Smoothing=1.5

        5. perlin_noise  (LIBRARY) -- ground texture
               parameters: Scale=12, Disorder=0.3

        6. height_blend  (LIBRARY)
               input_fg: bevel output_height (rocks)
               input_bg: perlin_ground output
               parameters: HeightOffset=0.3, Contrast=0.7

        7. non_uniform_blur_grayscale  (LIBRARY)
               input: height_blend output
               parameters: Intensity=2.0
               -- smooths transition between ground and rocks

    Notes:
        - tile_sampler X,Y Amount controls stone density (2-8 range)
        - height_blend HeightOffset controls how much rock "sticks out"
        - Add a second Perlin (Scale=20) blended Multiply for micro-pitting

================================================================================
SECTION 2: ORGANIC PATTERNS (WOOD, BARK, FABRIC)
================================================================================

RECIPE: Procedural Wood Grain (5-Step Foundation)
    Purpose: Oak/pine wood plank grain with fiber direction and knots
    Based on: not-lonely.com tutorial, Adobe parametric woods article

    Node chain:
        1. gradient_linear_1  (LIBRARY) -- horizontal fiber base
               output port: "Simple_Gradient"
               -- use Transformation2D after to set angle/tiling

        2. transformation  (ATOMIC) -- tile the gradient densely
               input: gradient_linear_1 output
               Tiling: [1, 30] -- many horizontal lines = wood grain density
               Rotation: 0.02 -- slight angle for natural look

        3. warp  (ATOMIC) -- distort with large soft noise
               input1: transformation output
               inputgradient: gaussian_noise (Scale=2, Disorder=0.3)
               intensity: 25.0
               -- large-scale wood grain undulation

        4. directionalwarp  (ATOMIC) -- knot swirl effect
               input1: warp output
               inputintensity: gaussian_noise_2 (separate, Scale=1, Disorder=0.5)
               intensity: 30.0
               -- localised swirling for knot areas

        5. directional_noise_1  (LIBRARY) -- fine fiber detail
               parameters: Scale=15, Disorder=0.4
               -- fine parallel noise like individual wood fibers

        6. blend  (ATOMIC) -- add fiber detail
               source: directional_noise_1 output
               destination: directionalwarp output
               blendingmode: 1 (Add), opacitymult: 0.15

        7. levels  (ATOMIC) -- contrast / brightness adjust
               -- set black point ~0.1 for rich dark grain

        8. histogram_scan  (LIBRARY)
               -- Contrast near max (0.95), Position=0.5
               -- creates aging/wear mask for dark weathering patches

        [COLOR BRANCH]
        9. gradient  (ATOMIC) -- Gradient Map for coloring
               input: levels output
               -- sample from reference: dark brown (0.15,0.08,0.03) to
                  light tan (0.72,0.55,0.38)

        10. hsl  (ATOMIC)
               input: gradient output
               Hue=0.5 (neutral), Saturation=0.55, Luminosity=0.45

        [ROUGHNESS BRANCH]
        11. blend  (ATOMIC)
               source: histogram_scan output (aging mask)
               destination: levels output
               blendingmode: 3 (Multiply), opacitymult: 0.6
               -- darker grain = rougher

    Connection summary:
        gradient_linear_1 -> transformation -> warp -> directionalwarp -> blend(dest)
        directional_noise_1 -----------------------------------------> blend(source)
                                                                          |
                                                                       levels -> HEIGHT_OUTPUT
                                                                       levels -> normal -> NORMAL_OUTPUT
                                                                       levels -> gradient -> hsl -> BASECOLOR_OUTPUT

    Notes:
        - Transformation Tiling Y controls grain density: 20-50 for pine, 8-15 for oak
        - Warp intensity 15-40 controls bow/wave in grain
        - Directional Warp intensity 20-60 controls knot size
        - For end-grain (cross-section): replace transformation with gradient_axial

---

RECIPE: Tree Bark (Tile Sampler + Bevel Approach)
    Purpose: Rough tree bark with raised ridges and organic edge breakup
    Based on: 80.lv cypress bark and bark material breakdowns

    Node chain:
        1. tile_sampler  (LIBRARY)
               Pattern: Disc (built-in circle), X=2, Y=20
               -- elongated circles = bark ridge shapes
               ScaleX: 0.3, ScaleY: 0.9
               RotationRandom: 0.05 -- very slight rotation
               LuminanceVariation: 0.4
               PositionRandom: 0.1

        2. edge_detect  (LIBRARY)
               input: tile_sampler output
               parameters: EdgeWidth=0.015, EdgeRoundness=0.3

        3. flood_fill  (LIBRARY)
               input: edge_detect output

        4. flood_fill_to_random_grayscale  (LIBRARY)
               input: flood_fill output

        5. bevel  (LIBRARY)
               input: flood_fill_to_random_grayscale -> input_height
               parameters: Distance=0.12, CornerType=Round, Smoothing=1.0

        6. directionalwarp  (ATOMIC)
               input1: bevel output_height
               inputintensity: clouds_2 (Scale=3)
               intensity: 20.0
               -- gives organic "bite" to bark ridges

        7. slope_blur_grayscale  (LIBRARY)
               input_grayscale: directionalwarp output
               input_slope: clouds_1 (Scale=6)
               parameters: Samples=8, Intensity=0.5, Mode=Min

        8. perlin_noise  (LIBRARY) -- fine bark pitting
               parameters: Scale=15, Disorder=0.5

        9. blend  (ATOMIC)
               source: perlin_noise, destination: slope_blur output
               blendingmode: 3 (Multiply), opacitymult: 0.4

    Notes:
        - tile_sampler Y Amount 15-30 controls bark density (more = finer bark)
        - For smoother bark (beech): reduce Directional Warp intensity to 5-10
        - For shaggy bark (pine): increase Slope Blur Intensity to 1.5-2.0
        - Add grunge_map_001 blended Multiply at 0.2 opacity for surface variation

---

RECIPE: Fabric Weave (Weave Generator + Detail)
    Purpose: Canvas, burlap, linen weave pattern
    Based on: Adobe Weave Generator docs, Surface Mentor article

    Node chain:
        1. weave_generator  (LIBRARY)
               -- or weave_2 for more complex patterns
               parameters: WarpCount=8, WeftCount=8
               ThreadWidth: 0.7, ThreadSpacing: 0.05
               WarpPattern: Plain weave (0)

        2. warp  (ATOMIC)
               input1: weave_generator output
               inputgradient: gaussian_noise (Scale=2, Disorder=0.4)
               intensity: 4.0
               -- subtle thread distortion for natural look

        3. grunge_map_001  (LIBRARY)
               parameters: Balance=0.5, Contrast=0.6

        4. slope_blur_grayscale  (LIBRARY)
               input_grayscale: warp output
               input_slope: grunge_map_001 output
               parameters: Samples=4, Intensity=0.3
               -- drives wear along weave slopes

        5. curvature_smooth  (LIBRARY)
               input: warp output
               -- outputs convex (thread tops) and concave (thread gaps)
               use output_convex port

        6. blend  (ATOMIC)
               source: curvature_smooth convex, destination: warp output
               blendingmode: 11 (Soft Light), opacitymult: 0.6
               -- enhances thread highlight/shadow

        [HEIGHT -> NORMAL]
        7. normal  (ATOMIC)
               input: warp output (height map)

        [ROUGHNESS]
        8. levels  (ATOMIC)
               input: curvature_smooth concave output
               -- thread intersections = higher roughness (darker in roughness map)

    Notes:
        - For burlap: WarpCount=WeftCount=4, ThreadWidth=0.5
        - For fine linen: WarpCount=WeftCount=16, ThreadWidth=0.85
        - grunge_map_015 (coarser) works well for rough canvas

================================================================================
SECTION 3: HARD SURFACE PATTERNS (METAL, CONCRETE, TILES)
================================================================================

RECIPE: Procedural Concrete (Fractal + Grunge)
    Purpose: Poured concrete, cement floor, rough concrete wall
    Based on: Olde Tinkerer Studio concrete breakdown, 80.lv hard surface workflow

    Node chain:
        1. fractal_sum_base  (LIBRARY)
               parameters: Scale=3, Disorder=0.5, Iterations=8
               -- macro concrete form

        2. grunge_concrete  (LIBRARY)
               parameters: Balance=0.5, Contrast=0.7
               -- builtin concrete grunge map

        3. blend  (ATOMIC)
               source: grunge_concrete, destination: fractal_sum_base output
               blendingmode: 3 (Multiply), opacitymult: 0.6

        4. sharpen  (ATOMIC)
               input: blend output
               intensity: 0.8
               -- sharpen concrete grain detail

        5. blend  (ATOMIC) -- sharpen layer
               source: sharpen output, destination: blend_3 output
               blendingmode: 9 (Overlay), opacitymult: 0.5

        6. levels  (ATOMIC)
               -- raise black point to 0.2 (concrete is mid-range height)
               -- lower white to 0.85

        7. perlin_noise  (LIBRARY) -- micro roughness
               parameters: Scale=25, Disorder=0.2

        8. blend  (ATOMIC) -- add micro
               source: perlin_noise, destination: levels output
               blendingmode: 1 (Add), opacitymult: 0.08

        [ROUGHNESS CHANNEL]
        9. grunge_map_002  (LIBRARY)
               -- complex combined noise for roughness variation

        10. histogram_scan  (LIBRARY)
               input: grunge_map_002
               parameters: Position=0.6, Contrast=0.7
               -- high concrete is relatively rough (0.7-0.9 roughness)

        11. blend  (ATOMIC) -- roughness = mostly rough + variation
               source: histogram_scan, destination: uniform (value=0.8)
               blendingmode: 3 (Multiply), opacitymult: 0.3

    Notes:
        - grunge_concrete Balance: 0.3=darker/wetter, 0.7=lighter/drier
        - For stamped concrete: add tile_generator (Brick pattern) before fractal_sum
        - For exposed aggregate: add cells_1 (Scale=15) blended Screen at 0.15

---

RECIPE: Rusted Metal (Curvature + Grunge)
    Purpose: Aged steel, iron, or galvanized metal with rust patches
    Based on: Adobe Rust Weathering docs, 80.lv tarnished metal breakdown

    Node chain:
        1. uniform  (ATOMIC) -- clean metal base height
               value: 0.5 (flat)

        2. grunge_scratches_rough  (LIBRARY)
               parameters: ScratchQuantity=0.4, ScratchWidth=0.3,
                            ScratchBlur=0.5, ScratchDirtiness=0.7

        3. blend  (ATOMIC)
               source: grunge_scratches_rough, destination: uniform output
               blendingmode: 1 (Add), opacitymult: 0.2
               -- subtle scratch height

        [RUST MASK CHAIN]
        4. gaussian_spots_1  (LIBRARY)
               parameters: Scale=5
               -- rust spot seed shapes

        5. histogram_scan  (LIBRARY)
               input: gaussian_spots_1
               parameters: Position=0.4, Contrast=0.8
               -- threshold spots to create rust patch masks

        6. slope_blur_grayscale  (LIBRARY)
               input_grayscale: histogram_scan output
               input_slope: clouds_2 (Scale=4)
               parameters: Samples=16, Intensity=0.8
               -- organic rust spread along cloud slopes

        7. levels  (ATOMIC)
               input: slope_blur output
               -- tighten: push black to 0.05 for clean mask edges

        [RUST HEIGHT DETAIL]
        8. fractal_sum_base  (LIBRARY)
               parameters: Scale=12, Iterations=5
               -- pitted rust surface texture

        9. blend  (ATOMIC)
               source: fractal_sum_base, destination: blend_3 output (scratch height)
               blendingmode: 3 (Multiply), opacitymult: 0.5
               opacity port: levels output (rust mask)
               -- only add rust height where mask is bright

        [ROUGHNESS]
        10. blend  (ATOMIC)
               -- clean metal: low roughness (0.2-0.3)
               -- rust areas: high roughness (0.85-0.95)
               source: uniform (value=0.9), destination: uniform (value=0.25)
               opacity port: levels output (rust mask)

        [BASE COLOR]
        11. gradient  (ATOMIC) -- rust color ramp
               input: fractal_sum_base
               -- gradient: 0.0=(0.1, 0.07, 0.04), 0.5=(0.55, 0.18, 0.05),
                             1.0=(0.75, 0.45, 0.15)

        12. blend  (ATOMIC) -- composite rust onto metal color
               source: gradient rust, destination: uniform (0.4, 0.4, 0.42) metal grey
               opacity port: levels output (rust mask)

    Notes:
        - gaussian_spots_1 Scale 3-8 controls rust patch size
        - Slope Blur Intensity 0.5-2.0 controls how far rust "spreads"
        - For dripping rust: replace gaussian_spots_1 with dripping_rust library node
        - Add curvature_smooth convex output as extra blend into rust mask
          (convex edges rust first)

---

RECIPE: Brick Wall (Tile Generator + Mortar)
    Purpose: Standard running bond brick, stone brick, tile floor
    Based on: Kokku Games procedural brick breakdown, Adobe Tile Generator docs

    Node chain:
        1. tile_generator  (LIBRARY)
               Pattern: Brick, X=6, Y=12
               Offset=0.5 (running bond), OffsetRandom=0.0
               PositionRandom: 0.02 -- slight brick position variation
               RotationRandom: 0.005 -- very slight

        2. perlin_noise  (LIBRARY) -- scale variation
               parameters: Scale=3, Disorder=0.5

        3. blend  (ATOMIC)
               source: perlin_noise, destination: perlin_noise (smaller scale=8)
               blendingmode: 1 (Add), opacitymult: 0.5
               -- combined noise for scale map

        [BRICK HEIGHT VARIATION]
        4. flood_fill  (LIBRARY)
               input: tile_generator output

        5. flood_fill_to_gradient  (LIBRARY)
               input: flood_fill output
               parameters: AngleVariation=1.0, RandomSeed=12345

        6. levels  (ATOMIC)
               input: flood_fill_to_gradient output
               -- black pivot to 0.3: compress height variation

        [BRICK EDGE EROSION]
        7. levels  (ATOMIC) -- edge isolation
               input: flood_fill_to_gradient output
               -- push black pivot RIGHT until only edges remain bright

        8. blend  (ATOMIC) -- invert + darken blend for erosion
               source: invert of levels_7, destination: levels_6 output
               blendingmode: 5 (Min/Darken)
               opacitymult: 0.4 -- control erosion strength

        9. blur  (ATOMIC)
               input: blend_8 output
               intensity: 0.65 -- improves edge depth in normal map

        [MORTAR CHANNEL]
        10. clouds_2  (LIBRARY) OR clouds_1
               parameters: Scale=6

        11. blend  (ATOMIC)
               source: clouds_2, destination: clouds_1 (Scale=20)
               blendingmode: 3 (Multiply)
               -- multi-scale mortar noise

        12. levels  (ATOMIC)
               input: blend_11 -- lighten to make mortar stand out

        [COMBINE BRICKS + MORTAR]
        13. blend  (ATOMIC)
               source: blur_9 output (brick height), destination: levels_12 (mortar)
               blendingmode: 0 (Copy), opacitymult: 0.97
               opacity port: tile_generator output (brick mask)
               -- mortar fills gaps, bricks sit on top

        14. normal  (ATOMIC)
               input: blend_13 -> HEIGHT_OUTPUT
        15. ambient_occlusion_hbao  (LIBRARY)
               input: blend_13 output

    Notes:
        - tile_generator X=6 Y=12 = standard brick ratio; X=4 Y=4 = square tiles
        - flood_fill_to_gradient AngleVariation=1.0 = max height variation per brick
        - blur intensity 0.5-0.9 controls edge softness in normal map
        - For aged bricks: add grunge_map_001 blended Overlay at 0.25

---

RECIPE: Sci-Fi / Industrial Tile Panels
    Purpose: Machined metal panels, sci-fi floor, industrial grating
    Based on: 80.lv sci-fi hard surface workflow

    Node chain:
        1. tile_generator  (LIBRARY)
               Pattern: Square, X=4, Y=4
               ScaleX=0.95, ScaleY=0.95 -- panel separation gap

        2. bevel  (LIBRARY)
               input: tile_generator -> input_height
               parameters: Distance=0.05, CornerType=Angular, Smoothing=0.2
               -- sharp machined chamfer on panel edges

        3. non_uniform_blur_grayscale  (LIBRARY)
               input: tile_generator output
               parameters: Intensity=2.0, Anisotropy=0.9, Angle=0.0
               -- anisotropic blur = machined surface look (directional polish)

        4. blend  (ATOMIC)
               source: bevel output_height, destination: non_uniform_blur output
               blendingmode: 1 (Add), opacitymult: 0.8

        5. grunge_scratches_rough  (LIBRARY)
               parameters: ScratchQuantity=0.2, ScratchWidth=0.1, ScratchBlur=0.8

        6. blend  (ATOMIC)
               source: grunge_scratches_rough, destination: blend_4 output
               blendingmode: 2 (Subtract), opacitymult: 0.1
               -- very subtle surface micro-scratches

        [ROUGHNESS - MACHINED PATTERN]
        7. non_uniform_blur_grayscale  (LIBRARY) -- roughness variation
               parameters: Intensity=3.0, Anisotropy=0.95
               -- brushed metal effect

        8. levels  (ATOMIC)
               input: non_uniform_blur_7 output
               -- remap to 0.1-0.4 range for polished metal roughness

    Notes:
        - non_uniform_blur Anisotropy 0.8-1.0 = brushed/machined finish
        - Anisotropy Angle controls brush direction (0.0=horizontal, 0.25=diagonal)
        - For grating: change tile_generator Pattern to a custom cross/diamond input
        - CornerType=Angular for machined, CornerType=Round for molded plastic

================================================================================
SECTION 4: UTILITY PATTERNS (EDGE WEAR, AO, CAVITY)
================================================================================

RECIPE: Procedural Edge Wear Mask (Without Baked Maps)
    Purpose: Mask highlighting worn/bright edges for metal, paint, etc.
    Based on: Adobe Edge Wear docs, 80.lv mastering SD guide

    Node chain:
        1. [HEIGHT_INPUT] -- connect your height map here

        2. bevel  (LIBRARY)
               input: height_input -> input_height
               parameters: Distance=0.05, CornerType=Round, Smoothing=0.5

        3. curvature_smooth  (LIBRARY)
               input: height_input
               use output_convex port (convex = protruding = worn edges)

        4. histogram_scan  (LIBRARY)
               input: curvature_smooth convex
               parameters: Position=0.6, Contrast=0.85
               -- sharpen convex mask: only sharpest peaks become wear

        5. grunge_map_001  (LIBRARY)
               parameters: Balance=0.5, Contrast=0.5

        6. blend  (ATOMIC)
               source: grunge_map_001, destination: histogram_scan output
               blendingmode: 3 (Multiply), opacitymult: 0.7
               -- break up edge wear with grunge for organic look

        7. levels  (ATOMIC)
               input: blend output
               -- final contrast adjustment: black=0.0, white pushes to 1.0

    Output: grayscale mask (white = worn edges)
    Notes:
        - histogram_scan Position 0.4-0.8 controls how much of surface is "worn"
        - histogram_scan Contrast 0.7-0.99 controls sharpness of wear boundary
        - Feed this mask into roughness channel (worn edges = low roughness = shiny)
        - Also feed into height channel blended with small negative value = slight edge chamfer

---

RECIPE: Height-Derived AO and Cavity Mask
    Purpose: Generates AO, convex highlight, and concave cavity masks from height
    Based on: Adobe AO docs, curvature workflow from community tutorials

    Node chain:
        1. [HEIGHT_INPUT]

        2. ambient_occlusion_hbao  (LIBRARY)
               input: height_input
               parameters: Quality=4, HeightScale=3.0, MaxDistance=0.15,
                            SpreadAngle=1.0
               output: AO mask (dark in crevices)

        3. curvature_smooth  (LIBRARY)
               input: height_input
               output_convex: bright where surface is convex (peaks/edges)
               output_concave: bright where surface is concave (valleys/crevices)

        4. histogram_scan  (LIBRARY) -- sharpen convex peaks
               input: curvature_smooth convex
               parameters: Position=0.7, Contrast=0.9

        5. histogram_scan  (LIBRARY) -- sharpen concave cavity
               input: curvature_smooth concave
               parameters: Position=0.5, Contrast=0.8

        6. blend  (ATOMIC) -- combine AO + cavity for deep shadow mask
               source: histogram_scan_5 (cavity), destination: AO output
               blendingmode: 3 (Multiply)
               -- deep crevices darker than either alone

        7. blend  (ATOMIC) -- DIRT ACCUMULATION MASK
               -- dirt gathers in AO/cavity areas
               source: grunge_map_002, destination: blend_6 output
               blendingmode: 3 (Multiply), opacitymult: 0.5

    Outputs:
        - blend_6 output: deep shadow / occlusion mask for basecolor darkening
        - histogram_scan_4 output: highlight mask for edge color brightening
        - blend_7 output: dirt accumulation mask

    Notes:
        - AO Quality 2=fast, 4=balanced, 8=high quality
        - MaxDistance 0.05-0.3 controls how far AO shadow reaches
        - Use deep shadow mask in blend Multiply on basecolor (darken crevices)
        - Use highlight mask in blend Screen on basecolor (brighten peaks)

---

RECIPE: Procedural Grunge / Dirt Overlay
    Purpose: Universal grunge mask for applying dirt, dust, paint peeling
    Based on: 80.lv edge wear and dirt recipes

    Node chain:
        1. grunge_map_001  (LIBRARY) -- large blobs
               parameters: Balance=0.5, Contrast=0.4

        2. grunge_map_002  (LIBRARY) -- complex noise
               parameters: Balance=0.45, Contrast=0.6

        3. clouds_2  (LIBRARY)
               parameters: Scale=5

        4. blend  (ATOMIC)
               source: grunge_map_002, destination: grunge_map_001 output
               blendingmode: 3 (Multiply), opacitymult: 0.6

        5. blend  (ATOMIC)
               source: clouds_2, destination: blend_4 output
               blendingmode: 9 (Overlay), opacitymult: 0.4

        6. histogram_scan  (LIBRARY)
               input: blend_5 output
               parameters: Position=0.5, Contrast=0.6
               -- Position: 0.3=heavy dirt, 0.7=light dust

        7. slope_blur_grayscale  (LIBRARY)
               input_grayscale: histogram_scan output
               input_slope: [HEIGHT_INPUT] -- your height map
               parameters: Samples=8, Intensity=0.4
               -- dirt pools in low areas / crevices

        8. levels  (ATOMIC)
               input: slope_blur output

    Output: grayscale dirt/grunge mask
    Notes:
        - histogram_scan Position is the KEY parameter to expose to user (dirt amount)
        - Slope Blur Intensity 0.2-1.0 controls how strongly dirt follows topology
        - For dust: Position=0.7, Intensity=0.2 (light, uniform)
        - For heavy grime: Position=0.3, Contrast=0.8 (thick, patchy)

---

RECIPE: Paint Peeling / Damage Mask
    Purpose: Chipped paint, weathered coatings, decal damage
    Based on: SD workflow community patterns

    Node chain:
        1. voronoi  (LIBRARY)
               parameters: Scale=6, Style=Random (F1), Disorder=0.5
               -- cells = paint chip areas

        2. histogram_scan  (LIBRARY)
               input: voronoi output
               parameters: Position=0.45, Contrast=0.9
               -- threshold: which cells are chipped vs intact

        3. curvature_smooth  (LIBRARY)
               input: [HEIGHT_INPUT]
               use output_convex

        4. blend  (ATOMIC)
               source: histogram_scan (voronoi), destination: curvature_smooth convex
               blendingmode: 4 (Max/Lighten), opacitymult: 0.8
               -- paint chips appear on voronoi boundaries AND convex edges

        5. grunge_map_001  (LIBRARY)
               parameters: Balance=0.4, Contrast=0.7

        6. blend  (ATOMIC)
               source: grunge_map_001, destination: blend_4 output
               blendingmode: 3 (Multiply), opacitymult: 0.6
               -- organic variation in damage pattern

        7. levels  (ATOMIC)
               input: blend_6 output

    Output: white = damaged/bare, black = painted intact
    Notes:
        - voronoi Scale 3-10 controls chip size
        - histogram_scan Position 0.3-0.6 controls coverage of damage
        - Use as opacity mask when blending paint layer over bare metal layer

================================================================================
SECTION 5: FX-MAP PATTERNS
================================================================================

RECIPE: FX-Map Scattered Dots / Stipple
    Purpose: Procedural dot pattern, stipple, porous surface, foam
    Based on: Adobe FX-Map docs, Rosen Kazlachev basics tutorial

    Inside the FX-Map node (fxmaps), the graph uses Quadrant nodes:

    FX-Map internal graph:
        1. Quadrant node -- LEVEL 0 (root)
               Depth: 6 (2^6 = 64 subdivisions)
               Pattern: No Pattern (just subdivides)

        2. Quadrant node -- LEVEL 1 (nested)
               Pattern: Disc
               Size: 0.35 -- relative to cell
               Color: $random (use Dynamic Function with random)
               Blending: Max

    Exposed parameters (in outer graph):
        - DotDensity: controls Depth (5=32x32 grid, 7=128x128 grid)
        - DotSize: maps to Size parameter (0.1-0.8)
        - SizeVariation: maps to Size via $random * multiplier

    External connections to FX-Map:
        - Input Image: any grayscale to use as brightness input
        - Output: grayscale dot pattern

    Notes:
        - Depth 5-7 is typical; higher = more dots but slower
        - Pattern options: Square, Disc, Gaussian, Pyramid
        - For irregular scatter: add Dynamic Function to Position using sin/cos of
          ($Number * 0.618) for golden ratio spiral distribution
        - Disc pattern gives circular dots; Gaussian = soft feathered dots

---

RECIPE: FX-Map Brick / Stacked Pattern
    Purpose: Custom brick/tile layouts, irregular stacking

    FX-Map internal graph:
        1. Quadrant -- root
               Depth: 4 (16 subdivisions = 4x4 grid)
               Pattern: No Pattern

        2. Quadrant -- rows
               Depth: 5 (adds another level = 4x8)
               Pattern: Square
               Size: [0.92, 0.45] -- wide flat bricks
               Color: $random
               BranchOffset: [$Number % 2 * 0.5, 0] -- running bond offset
               Blending: Max

    Notes:
        - BranchOffset using modulo creates alternating row offset = running bond
        - Size [width, height] ratio controls brick proportions
        - For random masonry: add random Size variation via Dynamic Function
        - $Number gives current iteration index for per-brick logic

---

RECIPE: FX-Map Spiral / Radial Scatter
    Purpose: Radial patterns, swirls, mandala-like arrangements

    FX-Map internal graph:
        1. Quadrant -- root
               Depth: 7 (128 elements)
               Pattern: Disc, Size: 0.02

        Position Dynamic Function:
            x = cos($Number * 0.3) * ($Number / 128.0) * 0.8
            y = sin($Number * 0.3) * ($Number / 128.0) * 0.8
            -- Archimedes spiral distribution

        Rotation Dynamic Function:
            $Number * 0.3
            -- each dot rotated relative to its angle

    Notes:
        - Multiplier 0.3 controls spiral tightness (0.1=loose, 1.0=tight)
        - 0.618 instead of 0.3 = golden angle = sunflower/phyllotaxis pattern
        - Useful for organic cluster patterns (moss, lichen, spores)

---

RECIPE: FX-Map Gaussian Noise (Brownian Motion)
    Purpose: Custom noise generation, fog, cloud base, soft texture variation

    FX-Map internal graph:
        1. Quadrant -- root
               Depth: 8 (256 elements)
               Pattern: Bell (soft gaussian falloff)
               Size: 0.3
               Color: Dynamic Function using $random
               Position: Dynamic Function [$random_x, $random_y]
               Blending: Add

        2. Quadrant -- fine detail (nested)
               Depth: 10
               Pattern: Gaussian
               Size: 0.1
               Color: Dynamic Function $random * 0.3 (dimmer fine dots)
               Blending: Add

    Notes:
        - Bell pattern = smooth dot with Gaussian falloff
        - Add mode accumulates: many overlapping soft dots = noise distribution
        - Adjust sizes and depths for macro vs micro noise characteristics
        - This replicates the gaussian_noise library node behavior at atomic level

================================================================================
SECTION 6: COMPLETE PBR WORKFLOW PATTERNS
================================================================================

RECIPE: Full Stone Floor PBR Graph (Connection Summary)
    Purpose: Complete stone tile floor with all PBR channels

    HEIGHT MAP:
        cells_1(Scale=5) -> edge_detect -> flood_fill ->
        flood_fill_to_random_grayscale -> bevel(Distance=0.15) ->
        blend+perlin_noise(Multiply,0.3) -> levels -> HEIGHT_OUTPUT

    NORMAL MAP:
        HEIGHT -> normal -> NORMAL_OUTPUT

    AO MAP:
        HEIGHT -> ambient_occlusion_hbao -> AO_OUTPUT

    BASE COLOR:
        HEIGHT -> gradient_map(stone: 0.2,0.18,0.15 to 0.8,0.75,0.68) ->
        blend+grunge(Multiply,0.3) -> hsl(Saturation=0.45) -> BASECOLOR_OUTPUT

    ROUGHNESS:
        curvature_smooth(HEIGHT) convex ->
        histogram_scan(Position=0.6, Contrast=0.8) ->
        blend(destination=uniform(0.8), blendmode=Multiply, 0.4) -> ROUGHNESS_OUTPUT
        -- peaks slightly less rough than average, crevices rougher

    METALLIC:
        uniform(value=0.0) -> METALLIC_OUTPUT -- stone is non-metallic

---

RECIPE: Full Metal Panel PBR Graph
    Purpose: Complete painted/bare metal all channels

    HEIGHT:
        tile_generator(Square,4x4) ->
        bevel(Distance=0.05,Angular) -> HEIGHT_OUTPUT

    NORMAL: HEIGHT -> normal -> NORMAL_OUTPUT

    AO: HEIGHT -> ambient_occlusion_hbao -> AO_OUTPUT

    RUST/WEAR MASK:
        gaussian_spots_1 -> histogram_scan -> slope_blur(clouds_2) -> RUST_MASK

    BASE COLOR:
        blend(paint_color vs rust_gradient, opacity=RUST_MASK) -> BASECOLOR_OUTPUT

    ROUGHNESS:
        blend(dest=uniform(0.3), src=uniform(0.9), opacity=RUST_MASK) ->
        blend(grunge_scratches_rough Subtract 0.05) -> ROUGHNESS_OUTPUT

    METALLIC:
        blend(dest=uniform(1.0), src=uniform(0.0), opacity=RUST_MASK) ->
        METALLIC_OUTPUT
        -- rust areas are non-metallic (0.0), bare metal = metallic (1.0)

================================================================================
SECTION 7: KEY PARAMETER REFERENCE
================================================================================

PERLIN NOISE (library node: perlin_noise):
    Scale:    1-256 (int)    -- global scale; 2-3=macro, 8-15=mid, 20-40=micro
    Disorder: 0.0-1.0        -- phase shift; 0.3=subtle, 0.5=medium, 0.8=chaotic

CELLS 1 (library node: cells_1):
    Scale:    1-256 (int)    -- cell size; 3-5=large rocks, 8-15=pebbles
    Disorder: 0.0-1.0        -- cell regularity; 0.0=grid, 1.0=organic

VORONOI (library node: voronoi):
    Scale:    1-256           -- crack/cell scale
    Style:    F1, F2, F2-F1, F1*F2, F1/F2, Edge, Random
              -- F2-F1=crackle pattern, Edge=thin borders, Random=flat color cells
    Disorder: 0.0-1.0

BEVEL (library node: bevel):
    Distance: -1.0 to 1.0   -- positive=outward, negative=inward, 0.05-0.2 typical
    CornerType: Round | Angular
    Smoothing: 0.0-5.0      -- 0=sharp, 1-2=natural, 4+=very smooth

HISTOGRAM SCAN (library node: histogram_scan):
    Position: 0.0-1.0       -- center of scan window; 0.5=neutral
    Contrast: 0.0-1.0       -- 0=soft gradient, 0.95=hard threshold
    NOTE: default Position=0.0 outputs ALL BLACK -- start at 0.5

SLOPE BLUR GRAYSCALE (library node: slope_blur_grayscale):
    Samples:  1-32           -- 4=fast, 8=balanced, 32=smooth
    Intensity: -1.0 to 1.0  -- positive=pushes down slopes, negative=pinches
    Mode:     Blur | Min | Max

NON UNIFORM BLUR GRAYSCALE (library node: non_uniform_blur_grayscale):
    Intensity: 0.0-40.0     -- blur radius; 2-8 typical
    Anisotropy: 0.0-1.0     -- 0=isotropic, 1.0=fully directional
    Angle: 0.0-1.0          -- direction of anisotropic blur

BLEND (atomic: sbs::compositing::blend):
    blendingmode: int       -- see BLEND MODES section above
    opacitymult: 0.0-1.0   -- overall opacity
    source=foreground, destination=background, opacity=mask

TILE GENERATOR (library node: tile_generator):
    X Amount: 1-64          -- horizontal tile count
    Y Amount: 1-64          -- vertical tile count
    Pattern:  Square, Brick, Disc, etc.
    Offset: 0.0-1.0         -- row/col offset (0.5=running bond)
    ScaleX/Y: 0.0-1.0      -- tile size relative to cell

TILE SAMPLER (library node: tile_sampler):
    X Amount: 1-32
    Y Amount: 1-32
    -- more advanced than Tile Generator: accepts Scale Map, Rotation Map,
       Displacement Map, Mask Map, Color Map inputs
    ScaleMapMultiplier: 0.0-2.0 -- how much Scale Map affects size

AMBIENT OCCLUSION HBAO (library node: ambient_occlusion_hbao):
    Quality: 1-4 (int)      -- 1=fast, 4=high quality
    HeightScale: 0.01-30.0  -- multiplier for height input intensity
    MaxDistance: 0.01-1.0   -- AO shadow reach radius
    SpreadAngle: 0.0-1.0    -- 1.0=full hemisphere

FLOOD FILL (library node: flood_fill):
    -- No significant parameters; input is a black-and-white mask
    -- Output: each white island gets unique ID color
    -- Always use edge_detect before flood_fill for shape isolation

CURVATURE SMOOTH (library node: curvature_smooth):
    -- Two outputs: output_convex (peaks), output_concave (valleys)
    -- Use with histogram_scan to threshold selection strength

FRACTAL SUM BASE (library node: fractal_sum_base):
    Scale: 1-256
    Disorder: 0.0-1.0
    Iterations: 1-12        -- 6-8 typical; more=more detail octaves

GRUNGE MAP 001 (library node: grunge_map_001):
    Balance:   0.0-1.0     -- 0.0=dark, 1.0=bright
    Contrast:  0.0-1.0
    Invert:    bool

DIRECTIONAL NOISE 1 (library node: directional_noise_1):
    Scale: 1-256            -- 10-20 for wood grain, 3-5 for large streaks
    Disorder: 0.0-1.0

================================================================================
SECTION 8: QUICK GRAPH CREATION HINTS FOR MCP TOOLS
================================================================================

# STEP ORDER FOR create_batch_graph OR sequential calls:
# 1. Always create_graph first
# 2. Create library nodes one at a time with create_instance_node
# 3. get_node_info on EVERY library node before connecting
#    (library node output IDs are NOT "unique_filter_output")
# 4. Create atomic nodes with create_node
# 5. connect_nodes one at a time (left-to-right, source-to-destination)
# 6. set_parameter after connecting
# 7. create_output_node for each PBR channel
# 8. connect final nodes to outputs
# 9. get_graph_info to verify
# 10. open_graph to view result

# KNOWN GOOD LIBRARY NODE SEARCH TERMS for get_library_nodes():
#   "cells"       -> cells_1
#   "perlin"      -> perlin_noise, perlin_noise_zoom, etc.
#   "voronoi"     -> voronoi, voronoi_fractal
#   "gradient"    -> gradient_linear_1, gradient_axial
#   "clouds"      -> clouds_1, clouds_2
#   "polygon"     -> polygon_2
#   "bevel"       -> bevel
#   "flood fill"  -> flood_fill, flood_fill_to_random_grayscale,
#                    flood_fill_to_gradient, flood_fill_to_index
#   "curvature"   -> curvature_smooth, curvature_sobel
#   "edge detect" -> edge_detect
#   "histogram"   -> histogram_scan, histogram_select, histogram_range
#   "slope blur"  -> slope_blur_grayscale
#   "non uniform blur" -> non_uniform_blur_grayscale
#   "tile"        -> tile_generator, tile_sampler, tile_random
#   "ambient"     -> ambient_occlusion_hbao, ambient_occlusion_rtao
#   "grunge"      -> grunge_map_001, grunge_map_002, grunge_concrete,
#                    grunge_scratches_rough, grunge_spots
#   "fractal"     -> fractal_sum_base, voronoi_fractal
#   "gaussian"    -> gaussian_noise, gaussian_spots_1
#   "directional" -> directional_noise_1, directional_warp (atomic)
#   "weave"       -> weave_generator, weave_2
#   "height blend" -> height_blend

# SAFE PARAMETER VALUES TO START WITH:
#   Most library noise nodes: Scale=5, Disorder=0.5
#   bevel: Distance=0.1, CornerType=Round, Smoothing=1.0
#   histogram_scan: Position=0.5, Contrast=0.7
#   slope_blur_grayscale: Samples=8, Intensity=0.5
#   non_uniform_blur_grayscale: Intensity=4.0, Anisotropy=0.0
#   ambient_occlusion_hbao: Quality=2, HeightScale=5.0
#   blend (for layering): blendingmode=3 (Multiply), opacitymult=0.5
#   blend (for detail): blendingmode=1 (Add), opacitymult=0.2
"""

# This module contains no executable code.
# All content is documentation / reference data as Python docstring / comments.
# Import and use the string constants via __doc__ or read the file directly.

RECIPE_CATEGORIES = [
    "stone_rock_height",
    "organic_wood_bark_fabric",
    "hard_surface_metal_concrete_tile",
    "utility_edge_wear_ao_cavity",
    "fx_map_patterns",
    "complete_pbr_workflows",
]

LIBRARY_NODE_OUTPUT_PORTS = {
    "cells_1": "output",
    "perlin_noise": "output",
    "polygon_2": "output",
    "gradient_linear_1": "Simple_Gradient",
    "gradient_axial": "output",
    "clouds_1": "output",
    "clouds_2": "output",
    "voronoi": "output",
    "voronoi_fractal": "output",
    "tile_generator": "unique_filter_output",
    "tile_sampler": "unique_filter_output",
    "flood_fill": "unique_filter_output",
    "flood_fill_to_random_grayscale": "unique_filter_output",
    "flood_fill_to_gradient": "unique_filter_output",
    "edge_detect": "unique_filter_output",
    "bevel_height_output": "output_height",
    "bevel_normal_output": "output_normal",
    "curvature_smooth_convex": "output_convex",
    "curvature_smooth_concave": "output_concave",
    "histogram_scan": "unique_filter_output",
    "histogram_select": "unique_filter_output",
    "ambient_occlusion_hbao": "unique_filter_output",
    "slope_blur_grayscale": "unique_filter_output",
    "non_uniform_blur_grayscale": "unique_filter_output",
    "height_blend": "unique_filter_output",
    "grunge_map_001": "output",
    "grunge_map_002": "output",
    "grunge_concrete": "output",
    "grunge_scratches_rough": "output",
    "grunge_spots": "output",
    "directional_noise_1": "output",
    "gaussian_noise": "output",
    "gaussian_spots_1": "output",
    "fractal_sum_base": "output",
    "weave_generator": "unique_filter_output",
    "weave_2": "unique_filter_output",
}

BLEND_MODES = {
    "Copy":          0,
    "Add":           1,
    "Subtract":      2,
    "Multiply":      3,
    "Max":           4,   # Lighten
    "Min":           5,   # Darken
    "LinearDodge":   6,
    "Overlay":       9,
    "Screen":        10,
    "SoftLight":     11,
    "HardLight":     12,
}

ATOMIC_INPUT_PORTS = {
    "blend":            {"fg": "source", "bg": "destination", "mask": "opacity"},
    "levels":           {"in": "input1"},
    "curve":            {"in": "input1"},
    "hsl":              {"in": "input1"},
    "blur":             {"in": "input1"},
    "sharpen":          {"in": "input1"},
    "warp":             {"image": "input1", "warp": "inputgradient"},
    "directionalwarp":  {"image": "input1", "warp": "inputintensity"},  # NOT inputgradient!
    "normal":           {"in": "input1"},
    "transformation":   {"in": "input1"},
    "distance":         {"in": "input1"},
    "grayscaleconversion": {"in": "input1"},
    "shuffle":          {"in": "input1"},
    "emboss":           {"in": "input1"},
    "output":           {"in": "inputNodeOutput"},
}

ATOMIC_OUTPUT_PORT = "unique_filter_output"  # All atomic nodes except output
