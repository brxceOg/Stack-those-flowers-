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
- Campfire costs 25 deposited flowers, occupies one 96 × 96 grid tile inside a planned housing area, and animates using the four isolated frames in the bottom row of the transparent `IMG_1382.jpeg` sprite atlas; the top row is excluded from playback. Playback runs at 6 frames per second so the flame silhouette changes remain readable at the compact 50 × 50 draw size.
- Workers assigned to a tower whose position is within 320 world units of a campfire receive +20% movement speed and +20% flower-picking speed. The check uses the worker house/tower position, not the worker's changing position, so one campfire can boost every nearby tower. Campfires are saved with the world.
- One flower is deposited per successful worker delivery.
- Picked flowers regrow after a short cooldown.
- Camera supports one-finger drag, two-finger pinch zoom, zoom buttons, and a recenter button.
- The HUD and build drawer remain fixed while the world moves beneath them.

## Structure selling
- Selling is accessed from the contextual menu opened by tapping a placed Worker House or Campfire; the player reviews its flower refund, then explicitly confirms or cancels. The build drawer contains no sell-structure mode or button.
- Selling a Worker House refunds 5 flowers and removes its assigned worker; selling a Campfire refunds 12 flowers and removes its boost radius.

- When one or more dye vats are present, each default worker independently has a 2% chance per second to seek an unclaimed vat (evaluated continuously over elapsed time). This is intentionally frequent enough for a worker group to consume an accumulating vat surplus; each vat can still be claimed by only one worker at a time. The worker uses its existing normal walk/run animation to approach the vat's final displayed position (`tx`,`ty`), then plays only the four-frame lower-row pick-up-and-drink sequence from `IMG_1395.jpeg` once beside the vat. The four isolated drink poses use a dedicated 208 × 208 frame strip with added transparent trim. The lower-row crop begins at source y=86 (above the mathematical halfway split) to preserve the tops of the heads, raised hands, worker outline, and drink prop. Normal walk/run/carry sheets remain unchanged. Workers do not enter the dye tent to drink; a vat is consumed when the worker reaches it and begins the visible drink animation.
- Finishing a drink grants that worker a 90-second Rainbow Rush: +30% movement speed, +30% flower-picking speed, and a 20% chance to earn one additional flower per delivery. A brief rainbow poof plays at the end of the drink animation, then the persistent animated rainbow-spectrum shine band and narrow white glint begin after a short transition delay. The continuous overlay is composited over the worker's opaque sprite pixels for the duration of the buff. Both gameplay buffs and the visual effect expire automatically. This temporary worker buff is runtime-only and does not alter existing save data.

## Technical constraints
- Plain HTML, CSS, and JavaScript; no build step or external runtime dependency.
- Canvas renders the world; DOM overlays are reserved for HUD and touch controls.
- Keep touch input usable in iOS Safari and respect safe-area insets.
- Keep simulation coordinates independent from screen pixels; resize and zoom must not distort world objects.
- Keep worker state transitions explicit: search → toFlower → toLauncher → deposit → search.
- Keep all original JPEG source sheets intact. Any future extracted assets must be derived files, never destructive edits to the source art.
- **All extracted production sprites must be PNGs with real transparency (alpha channel); neither white nor magenta sheet backgrounds or color mattes/halos may remain visible.**
- Remove only the edge-connected sheet background using a color-aware matte-removal method. The cartoon worker source uses vivid magenta; discard magenta-contaminated edge pixels while preserving the original character colors and dark outlines.
- Extract and inspect each frame individually before building a sprite sheet. Preserve the full silhouette, all edge pixels, original aspect ratio, and consistent frame canvas/baseline.
- Validate each PNG by compositing it over dark and contrasting backgrounds and checking that the background is transparent while intentional white artwork remains intact.
- Persist player progress in localStorage when save/load is added; version the save schema.

## Asset inventory
- `IMG_1393.jpeg`: final replacement base-worker sheet with a pale background and 4×4 layout for walk, run, idle, pickup, toss/hold, and carrying poses.\n- `IMG_1394.jpeg`: final replacement Dye Maker worker sheet with a pale background and 4×4 layout for run, idle, pickup/interaction, and carrying poses.\n- `IMG_1369.jpeg`: combined pixel-art sheet containing worker walk/run poses, flower/pickup poses, flower growth stages, flower varieties, and ground/world tiles.
- `IMG_1370.jpeg`: flower-pile progression reference sheet.
- The new worker sheets are split into their individual 4×4 cells at runtime. Each cell is isolated by foreground-component detection and edge-connected background removal before being packed into transparent animation strips/atlases; do not display either full source sheet in-game.

## Non-goals unless explicitly requested
- No combat, enemies, or unrelated colony systems.
- Do not replace the flower launcher with a generic factory.
- Do not turn workers into animals or unrelated characters.

- Campfires render a soft amber glow in a 58-world-unit circular radius, with gentle flame-synchronized flicker. This is visual only; the worker boost radius remains 320 world units.

- Workers whose assigned house is within 320 world units of a campfire receive an animated golden tint and bright diagonal shine sweep composited directly over the worker's opaque sprite pixels. The shine follows the worker and is clipped by sprite transparency; it uses the same `isWorkerBoosted` check as gameplay and does not affect movement, animation, or collision.


- Every completed planned housing area creates a distinct dirt land patch inside its exact grid footprint, with a subtle soil texture and grassy border to divide it from the surrounding garden. The active planning preview remains translucent blue.

- Flowers never spawn or regrow inside a completed planned housing area. When a plot is added, flowers already located within it are moved to unplanned ground while retaining their type and current state; the normal flower count and 8-second regrowth cooldown are unchanged.

- Planned housing areas automatically merge when they touch along an edge or have at most one empty grid tile between them with overlapping span along that edge. The merged area is treated as one continuous housing plot for building and flower-spawn exclusion.

- Tapping a placed Worker House or Campfire opens a small contextual menu beside that structure, with disabled placeholder upgrade actions reserved for future upgrades and a Sell Structure action. Selling continues to show the existing refund confirmation before removing the structure.

- Upgrade progression is universal per structure category, not individually attached to each building. The Worker House menu previews upgrades that apply to all Worker Houses; the Campfire menu previews upgrades that apply to all Campfires. Opening the menu on one building shows the upgrade options for its entire category.
- The first Worker House upgrade is **Run Speed**: each purchase increases all workers' running movement speed by 5%. Its shared level is saved in the existing V3 save data; older V2/V3 saves default to level 0. The first purchase costs 25 flowers; each subsequent purchase costs 1.5× the previous price, rounded up. The upgrade does not change walking speed or flower-picking speed.

- Successfully purchasing a Worker House upgrade triggers a small cartoon-green up-arrow beside every worker's head. Each arrow drifts gently upward and to the right, then fades away as a brief purchase-success celebration; it is visual feedback only.

- After a Worker House upgrade purchase, the open upgrade menu refreshes its next price in place without reopening or recalculating its position. The menu stays anchored exactly where the player opened it.


## Dye maker production
- A Dye Maker Tent costs 35 flowers and must be placed inside a planned housing section, following the existing building placement rules.
- The tent's soft ground shadow is tucked close beneath the tent base (centered at y=36 in tent-local drawing coordinates) so it reads as a contact shadow, not a detached oval.
- Each tent has one dedicated dye maker. The maker waits until a flower is visibly available in the flower pile, runs to collect it, carries it back to the tent, and starts a 4.5-second brewing cycle.
- When brewing finishes, the tent spits a physical dye-vat item out from its entrance. Dye vats remain in the world and are saved with the existing V3 save data; the dye tent positions are also saved. Existing V2/V3 saves without these fields migrate to empty dye-tent and dye-vat arrays.
- The base worker uses `IMG_1393.jpeg`; the Dye Maker uses `IMG_1394.jpeg`. Both are 4×4 pale-background sheets. Each cell is independently segmented, edge-connected background and separator marks are discarded, enclosed light details are retained, and the isolated poses are packed into transparent frame canvases. The base worker uses rows 1–4 for walk, run, idle/pickup/toss, and carrying. The Dye Maker uses rows 1–4 for run, idle/pickup/interaction, and carrying.
- The dye-vat sprite sheet is keyed at runtime using magenta transparency only. Preserve all dark bottle-outline pixels, including the lowest rows, and crop each of the eight horizontal frames at its full 84-pixel height.


- Final character source sheets: base worker `IMG_1394.jpeg`; Dye Maker `IMG_1393.jpeg`. Independently isolate all 16 cells. The pale background must become fully transparent, horizontal spacer rules must be removed rather than retained as sprite pixels, and enclosed white/cream character details and dark outlines must remain intact.

- During drinking, the worker visibly holds the actual matching dye-vat sprite from `IMG_1386.jpeg`. The world vat is consumed on arrival, but its type remains on the worker's drink reference so the same isolated bottle frame can be drawn in the raised hand for the entire animation; the prop is rendered in front of the worker and does not change the drink sequence or buff timing.

- The held bottle renders through the drinking poses but is hidden on the final mouth-open pose (`frame === count - 1`), before the worker returns to idle to receive the buff. Drink completion then clears `w.drinkVat` before the completion poof and search/idle transition; the bottle stays hidden during the 0.28-second buff delay.
