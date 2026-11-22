# Art Direction — Stack Those Flowers

## Overall look
A cheerful, handcrafted pixel-art garden. The world should feel like a little living garden colony viewed from above, with clear silhouettes, warm natural colors, chunky pixel edges, and readable animation at iPhone scale.

## Existing source art
Use the repository's two supplied sheets as the source of truth:
- `IMG_1373.jpeg`: current worker character sprite sheet, used for the worker walk, run, and flower-picking animations.\n- `IMG_1369.jpeg`: original world, flower, and tile art source.
- `IMG_1370.jpeg`: staged flower-pile sizes and launcher-related visual reference.

Preserve both original files unchanged. All production sprite assets must be derived transparent PNGs (individual sprites and/or sprite sheets), never destructive edits to the source art.

## Mandatory extraction and transparency standard
- **Every isolated sprite must have a genuinely transparent alpha background. A white background is not acceptable.**
- Remove the white sheet/paper background completely from the extracted sprite area. Do not leave white pixels, pale halos, white rectangles, or a matte around the sprite.
- Preserve white pixels that are part of the artwork: flower petals, eye whites, shine, highlights, shirt details, and other intentional white markings. Background removal must be based on connected background regions / careful masks, not a global “turn every white pixel transparent” operation.
- Inspect each extracted sprite against both a dark checkerboard and a contrasting solid background. Any leftover white fringe, stray background pixels, holes in the artwork, or clipped details must be corrected before the asset is accepted.
- Keep antialiasing/pixel edges faithful. For pixel art, favor clean hard-edged alpha where appropriate; do not blur, feather, or erode the sprite silhouette.
- Isolate frames individually before arranging them into a sheet. Never use guessed crop boxes that cut off artwork or include neighboring frames, labels, or another sprite.
- Give each frame a consistent transparent canvas size and baseline. Preserve the complete silhouette and original aspect ratio; do not stretch frames to fit.
- Keep a small transparent safety margin around each sprite so the full outermost pixels remain intact, but no visible background.
- Validate the exported PNGs by checking their alpha channel and compositing previews over dark and colored backgrounds. A white-looking petal must remain white while the surrounding sheet background is transparent.

## Worker
- Use the supplied farmer character: straw hat, blue overalls, light shirt, small friendly proportions.
- Use the walk cycle for ordinary travel and the run cycle for longer-distance movement or upgrades.
- Use dedicated pickup poses when collecting a flower.
- Carry a clearly visible flower while returning to the launcher.
- Keep the worker's feet aligned to a stable ground baseline across every frame.
- Never stretch individual frames to fit; preserve original aspect ratio.

## Flowers and world
- Use the supplied daisies, tulips, sunflowers, pink flowers, growth stages, and loose petals.
- The world should be lush and varied, not a flat green plane. Combine the supplied grass tiles, flower patches, dirt paths, stone, water, and sand only where appropriate.
- Scatter flowers with enough spacing that each target remains readable and workers can navigate around decorations.
- Flowers should visibly regrow after being harvested.

## Flower Launcher and pile
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
