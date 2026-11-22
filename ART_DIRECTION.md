# Art Direction — Stack Those Flowers

## Overall look
A cheerful, handcrafted garden combining the existing pixel-art garden world with the new cartoon 2D worker character. The world should feel like a little living garden colony viewed from above, with clear silhouettes, warm natural colors, chunky pixel edges, and readable animation at iPhone scale.

## Existing source art
- `IMG_1382.jpeg`: two-row campfire animation sheet on a vivid magenta background. Isolate each pose individually, remove only the connected magenta matte, and preserve the complete dark outline and warm fire/log colors. In-game playback uses only the four frames in the bottom row; the top row remains unused. This row has more pronounced flame-silhouette changes at the compact 50 × 50 in-world draw size.
Use the repository's two supplied sheets as the source of truth:
- `IMG_1375.jpeg`: legacy cartoon worker sheet retained as an original source; replaced in-game by `IMG_1390.jpeg`.\n- `IMG_1369.jpeg`: original world, flower, and tile art source.
- `IMG_1370.jpeg`: staged flower-pile sizes and launcher-related visual reference.

Preserve both original files unchanged. All production sprite assets must be derived transparent PNGs (individual sprites and/or sprite sheets), never destructive edits to the source art.

## Mandatory extraction and transparency standard
- **Every isolated sprite must have a genuinely transparent alpha background. A white background is not acceptable.**
- Remove the edge-connected pale sheet background completely from the new worker sprite sheets. Do not leave white pixels, pale halos, background rectangles, separator lines, or a matte around the sprite. Preserve enclosed cream/white artwork and highlights.
- Preserve white pixels that are part of the artwork: flower petals, eye whites, shine, highlights, shirt details, and other intentional white markings. Background removal must be based on connected background regions / careful masks, not a global “turn every white pixel transparent” operation.
- Inspect each extracted sprite against both a dark checkerboard and a contrasting solid background. Any leftover white fringe, stray background pixels, holes in the artwork, or clipped details must be corrected before the asset is accepted.
- Keep the cartoon outline faithful. Remove magenta contamination without introducing color spill; do not blur, feather, or erode the sprite silhouette.
- Isolate frames individually before arranging them into a sheet. Never use guessed crop boxes that cut off artwork or include neighboring frames, labels, or another sprite.
- Give each frame a consistent transparent canvas size and baseline. Preserve the complete silhouette and original aspect ratio; do not stretch frames to fit.
- Keep a small transparent safety margin around each sprite so the full outermost pixels remain intact, but no visible background.
- Validate the exported PNGs by checking their alpha channel and compositing previews over dark and colored backgrounds. A white-looking petal must remain white while the surrounding sheet background is transparent.

## Worker
- Use `IMG_1394.jpeg` as the final replacement base-worker sheet. Its 4×4 layout is cut into individual poses by foreground-component isolation inside each cell, removing the pale sheet background and edge-touching separator rules while retaining enclosed light details and the original dark outlines.
- Row one supplies the four-frame walk cycle; row two supplies the four-frame run cycle; row three supplies idle, two pickup poses, and the arms-forward toss/hold pose; row four supplies the four-frame carrying cycle. Preserve the new witch outfit and original palette.
- Keep every extracted pose on a consistent transparent 192×192 canvas, scale uniformly, and align the feet to a shared baseline. Draw the character at approximately 76 world pixels tall so it remains visually consistent with the enlarged base worker.
- Carry a clearly visible flower while returning to the launcher.\n- On arrival within launcher range, hold the flower in the normal carrying pose for a brief 0.3-second wind-up. Switch to the dedicated `IMG_1379.jpeg` raised-arm toss pose at the exact moment the flower is released, then animate the flower arcing into the launcher before depositing it. The toss artwork is exported tightly cropped with transparent background and drawn by visible-art height (60 world pixels), so transparent canvas padding cannot make it appear smaller than the other worker animations.
- Keep the worker's feet aligned to a stable ground baseline across every frame.
- Never stretch individual frames to fit; preserve original aspect ratio.
- In-world worker rendering uses a 76×76 square draw size for the 192×192 transparent frame canvas; scale width and height uniformly and keep the feet on the same ground baseline.

## Flowers and world
- Use the supplied daisies, tulips, sunflowers, pink flowers, growth stages, and loose petals.
- The world should be lush and varied, not a flat green plane. Combine the supplied grass tiles, flower patches, dirt paths, stone, water, and sand only where appropriate.
- Scatter flowers with enough spacing that each target remains readable and workers can navigate around decorations.
- Flowers should visibly regrow after being harvested.

## Flower Launcher and pile
- The supplied collection sheet's first frame is also the permanent idle launcher pose; never show the old placeholder when the launcher is idle.
- Draw a soft, low-opacity contact shadow directly beneath the launcher in every state (idle, collection, charge, and fire) so the machine sits naturally on the garden ground. Keep the shadow subtle and broad, not a hard black outline.
- The launcher is the central landmark and should remain easy to find while scrolling.
- Each delivery should trigger a short, satisfying launch/toss animation.
- The pile should grow visibly beside the launcher, using the progression art as a size and silhouette reference.
- Pile growth must not cover the launcher, workers, or important world navigation.

## UI
- Keep the HUD fixed to the screen while the world scrolls.
- The build menu is a compact slide-out drawer with large touch targets.
- Use warm cream text, garden greens, earthy wood browns, and flower accents.
- Respect iPhone safe areas and avoid tiny controls.
- Avoid default browser-looking controls and avoid placing essential UI over the launcher.

## Animation and technical art rules
- Nearest-neighbor/pixelated rendering for pixel-art assets.
- Isolate each frame individually; no neighboring-frame bleed, labels, or white-sheet gutters.
- Use consistent frame bounds and anchors across all animation states.
- Do not recolor the farmer or flower art in ways that damage its original palette.
- Keep all animation loops deterministic and smooth at variable frame rates.
- A sprite sheet is not considered complete until every frame has been visually inspected at native scale and against contrasting backgrounds, with its transparent background verified.

- Campfires cast a subtle, warm amber circular glow with a small local radius (58 world units). Its brightness flickers gently with the fire animation; it is a visual light effect only and does not change the 320-unit worker boost radius.

- Workers receiving a campfire boost get a clearly visible, animated golden-white shine that sweeps diagonally across the worker's actual character pixels. The shine is clipped to the sprite's transparency, follows its animation and movement, and appears only while the assigned-house boost is active.


- Each completed planned housing area is rendered as a distinct worked-earth plot with a warm brown soil surface, subtle soil texture, and a narrow grassy edge. The patch follows the exact planned grid rectangle; the blue overlay is reserved for an area currently being drawn.

- Flower spawn points must remain outside every completed planned housing plot. When a new plot is drawn, any existing flower point it covers is relocated to open garden ground; flower count, type, and current growth/respawn state are preserved. This changes spawn locations only, not the spawn count or regrowth timing.

- Planned housing plots automatically join into one continuous dirt division when they share an edge or are separated by at most one empty grid tile, with overlapping span along that edge. This keeps nearby plots visually connected without joining diagonally separated plots.

- Tapping a placed worker house or campfire opens a compact contextual action menu immediately beside it. The menu reserves disabled upgrade slots for future upgrades and includes the structure's sell action; selling still requires explicit confirmation.

- The contextual upgrade menu is category-wide, not per-building: Worker House upgrades apply to every Worker House, and Campfire upgrades apply to every Campfire. Selecting any one structure opens the available upgrade list for its category; future purchases will affect all structures of that type.


## Dye maker asset direction
- `IMG_1393.jpeg` is the final replacement Dye Maker character sheet. It uses a 4×4 layout. Isolate each pose independently with foreground-component and edge-connected background separation inside its own cell; discard separator lines that touch the cell edges, preserve enclosed light artwork, and alpha-trim before packing into a transparent 4×4 atlas. The first two rows supply the eight-frame run cycle, row three supplies idle and pickup/interaction poses, and row four supplies the four-frame carrying cycle. Keep the original JPEG unchanged.
- `IMG_1384.jpeg` is the dye tent sheet. Its upper row supplies the tent's resting/entrance states and its lower row supplies the brewing animation. Keep the original sheet intact and crop frames at draw time. Align the bottom of the tent artwork with its contact shadow so the tent visibly rests on the ground.
- `IMG_1386.jpeg` is the dye-vat sheet with eight horizontal bottle frames. Remove the magenta key only. Do not erase dark pixels by row or strip: the dark bottle outlines extend into the lowest source rows and must remain intact. Crop the full 84-pixel frame height so each bottle's bottom edge is visible.
- Dye maker tents are animated production buildings. The dye maker runs between the tent and the visible flower pile, carries one flower, physically enters the tent, and remains hidden throughout the 4.5-second brew before emerging. Keep the tent in front of the entering/exiting character for natural occlusion; preserve the physical vat spawn.


## Final default character sheets
- Base worker: `IMG_1394.jpeg` (witch outfit, 4×4). Dye Maker: `IMG_1393.jpeg` (plain outfit, 4×4).
- Treat each of the 16 cells as an independent frame. Remove the pale sheet background by edge-connected background separation, and discard horizontal spacer rules that touch the cell boundary. Do not retain any white/pink background pixels or spacer-line fragments. Preserve enclosed light artwork, dark outlines, and all character pixels. Trim each isolated frame with a small transparent margin, then pack on a shared baseline without stretching.
