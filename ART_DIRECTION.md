# Art Direction — Stack Those Flowers

## Overall look
A cheerful, handcrafted pixel-art garden. The world should feel like a little living garden colony viewed from above, with clear silhouettes, warm natural colors, chunky pixel edges, and readable animation at iPhone scale.

## Existing source art
Use the repository's two supplied sheets as the source of truth:
- `IMG_1369.jpeg`: farmer/helper character, walk and run cycles, flower pickup poses, flower growth stages, loose petals, flower varieties, and modular ground tiles.
- `IMG_1370.jpeg`: staged flower-pile sizes and launcher-related visual reference.

Preserve the original files. Create transparent PNG sprite sheets or individual PNGs from carefully isolated source regions. Remove the white background only from extracted sprites; do not erase white pixels that belong to petals, eyes, highlights, or other artwork. Keep every animation frame on a consistent canvas size and baseline so workers never jump in scale or position.

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
- Use consistent frame bounds and anchors across animation states.
- Do not recolor the farmer or flower art in ways that damage its original palette.
- Keep all animation loops deterministic and smooth at variable frame rates.
