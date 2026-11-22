"""Extract the eight campfire animation poses from IMG_1382.jpeg."""
from pathlib import Path
import numpy as np
from PIL import Image
from matte_removal import remove_magenta_matte

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "IMG_1382.jpeg"
OUT = ROOT / "assets"
FRAME_DIR = OUT / "campfire-frames"
FRAME_SIZE = 192
COLS, ROWS = 4, 2

if not SOURCE.is_file():
    raise FileNotFoundError(f"Missing campfire source sheet: {SOURCE}")

sheet = Image.open(SOURCE).convert("RGBA")
# The submitted sheet is a clean 4 x 2 grid with black separators.
cell_w, cell_h = sheet.width / COLS, sheet.height / ROWS
if abs(cell_w - 352) > 1 or abs(cell_h - 384) > 1:
    raise RuntimeError(f"Unexpected IMG_1382.jpeg dimensions: {sheet.size}; expected approximately 1408x768")

FRAME_DIR.mkdir(parents=True, exist_ok=True)
atlas = Image.new("RGBA", (FRAME_SIZE * COLS, FRAME_SIZE * ROWS), (0, 0, 0, 0))

for i in range(COLS * ROWS):
    col, row = i % COLS, i // COLS
    x0, y0 = round(col * cell_w) + 7, round(row * cell_h) + 7
    x1, y1 = round((col + 1) * cell_w) - 7, round((row + 1) * cell_h) - 7
    cell = sheet.crop((x0, y0, x1, y1))
    # The sheet has dark separators around each pose, so matte each isolated
    # cell independently; its magenta field then reaches all four edges.
    cell = remove_magenta_matte(cell)
    alpha = np.asarray(cell.getchannel("A"))
    bbox = Image.fromarray(alpha).getbbox()
    if bbox is None:
        raise RuntimeError(f"Campfire frame {i + 1} is empty")
    sprite = cell.crop(bbox)
    # Preserve full artwork and aspect ratio; use a consistent ground baseline.
    scale = min(1.0, 178 / sprite.width, 178 / sprite.height)
    if scale < 1.0:
        sprite = sprite.resize((round(sprite.width * scale), round(sprite.height * scale)), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    frame.alpha_composite(sprite, ((FRAME_SIZE - sprite.width) // 2, FRAME_SIZE - 5 - sprite.height))
    path = FRAME_DIR / f"burn-{i + 1:02d}.png"
    frame.save(path, optimize=True)
    check = Image.open(path).convert("RGBA")
    a = np.asarray(check.getchannel("A"))
    if check.size != (FRAME_SIZE, FRAME_SIZE) or a[0, 0] != 0 or np.count_nonzero(a) < 500:
        raise RuntimeError(f"Campfire frame validation failed: {path}")
    atlas.alpha_composite(frame, (col * FRAME_SIZE, row * FRAME_SIZE))
    print(f"{path.relative_to(ROOT)}: isolated {sprite.size} artwork on transparent {FRAME_SIZE}x{FRAME_SIZE} canvas")

atlas_path = OUT / "campfire-atlas.png"
atlas.save(atlas_path, optimize=True)
check = Image.open(atlas_path).convert("RGBA")
if check.size != (FRAME_SIZE * COLS, FRAME_SIZE * ROWS):
    raise RuntimeError("Campfire atlas dimensions failed validation")
for i in range(COLS * ROWS):
    x, y = (i % COLS) * FRAME_SIZE, (i // COLS) * FRAME_SIZE
    alpha = np.asarray(check.getchannel("A"))[y:y + FRAME_SIZE, x:x + FRAME_SIZE]
    if not np.any(alpha > 0) or alpha[0, 0] != 0:
        raise RuntimeError(f"Campfire atlas frame {i + 1} is invalid")
print(f"{atlas_path.relative_to(ROOT)}: extracted all eight transparent animation frames")
