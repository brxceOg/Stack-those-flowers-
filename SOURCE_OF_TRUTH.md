# Stack Those Flowers — Source of Truth

## Project
A standalone, mobile-first idle gathering game for iPhone Safari, hosted as a GitHub Pages site from this repository.

## Core loop
1. A large, pannable world contains flower patches and decorative ground.
2. The player opens the build drawer and chooses **Worker House**.
3. The player taps an open patch of ground to place the house.
4. A worker spawns at that house, finds the nearest available flower, walks to it, picks it, and carries it to the central Flower Launcher.
5. The launcher deposits each flower into a visible pile beside it.
6. Flowers regrow over time; workers repeat the loop autonomously.

## Current prototype rules
- World dimensions: 2600 × 1900 world units.
- The Flower Launcher is the fixed world center and the visual anchor.
- Worker House costs 10 deposited flowers and creates one worker.
- One flower is deposited per successful worker delivery.
- Picked flowers regrow after a short cooldown.
- Camera supports one-finger drag, two-finger pinch zoom, zoom buttons, and a recenter button.
- The HUD and build drawer remain fixed while the world moves beneath them.

## Technical constraints
- Plain HTML, CSS, and JavaScript; no build step or external runtime dependency.
- Canvas renders the world; DOM overlays are reserved for HUD and touch controls.
- Keep touch input usable in iOS Safari and respect safe-area insets.
- Keep simulation coordinates independent from screen pixels; resize and zoom must not distort world objects.
- Keep worker state transitions explicit: search → toFlower → toLauncher → deposit → search.
- Keep the two original JPEG source sheets intact. Any future extracted assets must be derived files, never destructive edits to the source art.
- **All extracted production sprites must be PNGs with real transparency (alpha channel); a white sheet background or white matte/halo must never remain visible.**
- Remove only connected sheet-background white pixels; preserve intentional white artwork such as petals, highlights, eyes, and shirt details. Never globally erase all white pixels.
- Extract and inspect each frame individually before building a sprite sheet. Preserve the full silhouette, all edge pixels, original aspect ratio, and consistent frame canvas/baseline.
- Validate each PNG by compositing it over dark and contrasting backgrounds and checking that the background is transparent while intentional white artwork remains intact.
- Persist player progress in localStorage when save/load is added; version the save schema.

## Asset inventory
- `IMG_1369.jpeg`: combined pixel-art sheet containing worker walk/run poses, flower/pickup poses, flower growth stages, flower varieties, and ground/world tiles.
- `IMG_1370.jpeg`: flower-pile progression reference sheet.
- The sheets include labels and multiple assets; do not use either full sheet as a visible in-game sprite. Crop individual frames and remove the white sheet background when creating production sprites.

## Non-goals unless explicitly requested
- No combat, enemies, or unrelated colony systems.
- Do not replace the flower launcher with a generic factory.
- Do not turn workers into animals or unrelated characters.
