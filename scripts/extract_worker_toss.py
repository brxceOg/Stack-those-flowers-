from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image
from matte_removal import remove_magenta_matte

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "IMG_1379.jpeg"
OUT = ROOT / "assets"
FRAME_DIR = OUT / "worker-frames"
FRAME_W, FRAME_H = 256, 192
TARGET_SPRITE_HEIGHT = 176
MAX_SPRITE_WIDTH = FRAME_W - 8

if not SOURCE.is_file():
    raise FileNotFoundError(SOURCE)
source = Image.open(SOURCE).convert("RGBA")
clean = remove_magenta_matte(source)
bbox = clean.getchannel("A").getbbox()
if bbox is None:
    raise RuntimeError("No worker artwork remained after magenta removal")
sprite = clean.crop(bbox)
# Export a tightly cropped transparent sprite rather than a padded 256x192
# worker canvas. The runtime sizes the visible artwork itself, avoiding the
# extra transparent margins that made this pose look smaller than other frames.
sprite = sprite.resize((round(sprite.width * TARGET_SPRITE_HEIGHT / sprite.height), TARGET_SPRITE_HEIGHT), Image.Resampling.LANCZOS)
bbox = sprite.getchannel("A").getbbox()
sprite = sprite.crop(bbox)
OUT.mkdir(parents=True, exist_ok=True)
FRAME_DIR.mkdir(parents=True, exist_ok=True)
path = OUT / "worker-toss.png"
sprite.save(path, optimize=True)
sprite.save(FRAME_DIR / "toss-01.png", optimize=True)
check = Image.open(path).convert("RGBA")
alpha = np.asarray(check.getchannel("A"))
if check.width < 80 or check.height != TARGET_SPRITE_HEIGHT or np.count_nonzero(alpha) < 300:
    raise RuntimeError("Toss pose transparency/dimension validation failed")
# Ensure the canvas contains both transparent background and opaque artwork.
if not np.any(alpha == 0) or not np.any(alpha == 255):
    raise RuntimeError("Toss pose alpha channel is incomplete")
print(f"{path.relative_to(ROOT)}: tight-cropped flower-toss sprite, {check.size}, transparent alpha verified")
