from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
FRAME_DIR = OUT / "worker-frames"
OUT.mkdir(parents=True, exist_ok=True)
FRAME_DIR.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "IMG_1375.jpeg"
COLS = ROWS = 4
FRAME_W = FRAME_H = 192
MAGENTA = np.array([255.0, 0.0, 255.0], dtype=np.float32)

def remove_magenta_matte(image):
    """Remove only edge-connected magenta and un-matte antialiased edges."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[:, :, :3].astype(np.float32)
    h, w = rgb.shape[:2]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    candidate = (r > 78) & (b > 78) & (g < 158) & ((r-g) > 42) & ((b-g) > 42)
    seen = np.zeros((h, w), dtype=bool)
    queue = deque()
    def add(y, x):
        if candidate[y, x] and not seen[y, x]:
            seen[y, x] = True
            queue.append((y, x))
    for x in range(w):
        add(0, x); add(h-1, x)
    for y in range(h):
        add(y, 0); add(y, w-1)
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny, nx = y+dy, x+dx
            if 0 <= ny < h and 0 <= nx < w:
                add(ny, nx)
    if np.any(seen):
        delta = np.max(np.abs(rgb - MAGENTA), axis=2)
        alpha = np.clip(delta / 255.0, 0.0, 1.0)
        safe = np.maximum(alpha, 1.0/255.0)
        unmatte = (rgb - (1.0-alpha[:, :, None])*MAGENTA) / safe[:, :, None]
        rgba[seen, :3] = np.clip(unmatte[seen], 0, 255).astype(np.uint8)
        rgba[seen, 3] = np.clip(alpha[seen]*255.0, 0, 255).astype(np.uint8)
    rgba[rgba[:, :, 3] == 0, :3] = 0
    return Image.fromarray(rgba, "RGBA")

def extract_cell(sheet, row, col):
    cell_w, cell_h = sheet.width // COLS, sheet.height // ROWS
    x0, y0 = col*cell_w, row*cell_h
    cell = remove_magenta_matte(sheet.crop((x0, y0, x0+cell_w, y0+cell_h)))
    bbox = cell.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError(f"Empty new-cartoon pose at row {row}, column {col}")
    sprite = cell.crop(bbox)
    if sprite.width > FRAME_W-8 or sprite.height > FRAME_H-8:
        raise RuntimeError(f"Pose row {row}, column {col} will not fit without scaling: {sprite.size}")
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0,0,0,0))
    frame.alpha_composite(sprite, ((FRAME_W-sprite.width)//2, FRAME_H-4-sprite.height))
    return frame

def save_cycle(name, row, columns):
    frames = [extract_cell(source, row, col) for col in columns]
    sheet = Image.new("RGBA", (FRAME_W*len(frames), FRAME_H), (0,0,0,0))
    for i, frame in enumerate(frames):
        path = FRAME_DIR / f"{name}-{i+1:02d}.png"
        frame.save(path, optimize=True)
        check = Image.open(path).convert("RGBA")
        alpha = np.asarray(check.getchannel("A"))
        if check.size != (FRAME_W, FRAME_H) or not np.any(alpha == 0) or np.count_nonzero(alpha) < 300:
            raise RuntimeError(f"Frame validation failed: {path}")
        sheet.alpha_composite(frame, (i*FRAME_W, 0))
    path = OUT / f"worker-{name}.png"
    sheet.save(path, optimize=True)
    check = Image.open(path).convert("RGBA")
    alpha = np.asarray(check.getchannel("A"))
    if check.size != (FRAME_W*len(frames), FRAME_H) or alpha[0,0] != 0:
        raise RuntimeError(f"{name} sheet dimensions or transparency failed")
    for i in range(len(frames)):
        cell = alpha[:, i*FRAME_W:(i+1)*FRAME_W]
        if not np.any(cell > 0) or not np.any(cell == 0):
            raise RuntimeError(f"{name} frame {i+1} alpha validation failed")
    print(f"{path.relative_to(ROOT)}: {len(frames)} cartoon frames, {check.size}, alpha verified")

if not SOURCE.is_file():
    raise FileNotFoundError(f"Required new worker artwork is missing: {SOURCE}")
source = Image.open(SOURCE).convert("RGBA")
if source.size != (1408, 768):
    raise RuntimeError(f"Unexpected IMG_1375.jpeg dimensions: {source.size}; expected 1408x768")

# Exact 4x4 layout: walk, run, idle + two pick poses, then carry.
save_cycle("walk", 0, (0,1,2,3))
save_cycle("run", 1, (0,1,2,3))
save_cycle("idle", 2, (0,))
save_cycle("pick", 2, (1,2))
save_cycle("carry", 3, (0,1,2,3))
