"""Extract the four worker-house door frames from IMG_1381.jpeg."""
from pathlib import Path
import numpy as np
from PIL import Image
from matte_removal import remove_magenta_matte

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "IMG_1381.jpeg"
OUT = ROOT / "assets"
FRAME_DIR = OUT / "worker-house-frames"
FRAME_SIZE = 224
FRAME_COUNT = 4

if not SOURCE.is_file():
    raise FileNotFoundError(f"Missing worker-house source sheet: {SOURCE}")

sheet = Image.open(SOURCE).convert("RGBA")
if sheet.size != (828, 228):
    raise RuntimeError(f"Unexpected IMG_1381.jpeg dimensions: {sheet.size}; expected 828x228")

# Remove the connected magenta sheet matte once, before splitting the four
# adjacent poses. This prevents a neighboring frame's edge from influencing
# the background estimate.
clean = remove_magenta_matte(sheet)
FRAME_DIR.mkdir(parents=True, exist_ok=True)
atlas = Image.new("RGBA", (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE), (0, 0, 0, 0))

for i in range(FRAME_COUNT):
    x0 = round(i * sheet.width / FRAME_COUNT)
    x1 = round((i + 1) * sheet.width / FRAME_COUNT)
    cell = clean.crop((x0, 0, x1, sheet.height))
    alpha = np.asarray(cell.getchannel("A"))
    bbox = Image.fromarray(alpha).getbbox()
    if bbox is None:
        raise RuntimeError(f"Worker-house frame {i + 1} is empty")
    sprite = cell.crop(bbox)
    # Preserve the full silhouette and aspect ratio; only scale down if needed.
    scale = min(1.0, 204 / sprite.width, 204 / sprite.height)
    if scale < 1.0:
        sprite = sprite.resize((round(sprite.width * scale), round(sprite.height * scale)), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    frame.alpha_composite(sprite, ((FRAME_SIZE - sprite.width) // 2, FRAME_SIZE - 4 - sprite.height))
    path = FRAME_DIR / f"door-{i + 1:02d}.png"
    frame.save(path, optimize=True)
    check = Image.open(path).convert("RGBA")
    a = np.asarray(check.getchannel("A"))
    if check.size != (FRAME_SIZE, FRAME_SIZE) or a[0, 0] != 0 or np.count_nonzero(a) < 1000:
        raise RuntimeError(f"Worker-house frame validation failed: {path}")
    atlas.alpha_composite(frame, (i * FRAME_SIZE, 0))
    print(f"{path.relative_to(ROOT)}: isolated {sprite.size} artwork on {FRAME_SIZE}x{FRAME_SIZE} transparent canvas")

atlas_path = OUT / "worker-house.png"
atlas.save(atlas_path, optimize=True)
check = Image.open(atlas_path).convert("RGBA")
if check.size != (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE):
    raise RuntimeError("Worker-house atlas dimensions failed validation")
for i in range(FRAME_COUNT):
    alpha = np.asarray(check.getchannel("A"))[:, i * FRAME_SIZE:(i + 1) * FRAME_SIZE]
    if not np.any(alpha > 0) or alpha[0, 0] != 0:
        raise RuntimeError(f"Worker-house atlas frame {i + 1} is invalid")
print(f"{atlas_path.relative_to(ROOT)}: {FRAME_COUNT} isolated transparent frames")
