from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "IMG_1379.jpeg"
OUT = ROOT / "assets"
FRAME_DIR = OUT / "worker-frames"
FRAME_W, FRAME_H = 256, 192
TARGET_SPRITE_HEIGHT = 176
MAX_SPRITE_WIDTH = FRAME_W - 8

def remove_connected_magenta(image):
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[:, :, :3].astype(np.int16)
    r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
    # Match the vivid pink field and JPEG-compressed edge pixels only.
    candidate = (r > 135) & (b > 105) & (g < 225) & ((np.minimum(r,b)-g) > 16)
    h, w = candidate.shape
    seen = np.zeros((h,w), dtype=bool)
    queue = deque()
    def add(y,x):
        if candidate[y,x] and not seen[y,x]:
            seen[y,x] = True
            queue.append((y,x))
    for x in range(w):
        add(0,x); add(h-1,x)
    for y in range(h):
        add(y,0); add(y,w-1)
    while queue:
        y,x = queue.popleft()
        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<h and 0<=nx<w:
                add(ny,nx)
    rgba[seen] = (0,0,0,0)
    # Defringe antialiased edge pixels directly adjacent to removed magenta.
    alpha = rgba[:,:,3] > 0
    edge = np.zeros((h,w), dtype=bool)
    edge[1:,:] |= ~alpha[:-1,:]
    edge[:-1,:] |= ~alpha[1:,:]
    edge[:,1:] |= ~alpha[:,:-1]
    edge[:,:-1] |= ~alpha[:,1:]
    edge &= alpha
    spill = np.maximum(0, np.minimum(r,b) - g).astype(np.float32)
    for channel in (0,2):
        values = rgba[:,:,channel].astype(np.float32)
        values[edge] = np.maximum(0, values[edge] - spill[edge]*0.78)
        rgba[:,:,channel] = values.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")

if not SOURCE.is_file():
    raise FileNotFoundError(SOURCE)
source = Image.open(SOURCE).convert("RGBA")
clean = remove_connected_magenta(source)
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
