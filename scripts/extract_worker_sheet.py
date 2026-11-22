from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image
from matte_removal import remove_magenta_matte

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
FRAME_DIR = OUT / "worker-frames"
OUT.mkdir(parents=True, exist_ok=True)
FRAME_DIR.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "IMG_1375.jpeg"
COLS = ROWS = 4
FRAME_W = FRAME_H = 192

def keep_main_character_component(image):
    """Drop disconnected JPEG/background remnants; retain the main figure and nearby details."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    mask = rgba[:, :, 3] > 0
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    components = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]
            seen[sy, sx] = True
            pixels = []
            while stack:
                y, x = stack.pop()
                pixels.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if (dx or dy) and 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            components.append(pixels)
    if not components:
        return Image.fromarray(rgba, "RGBA")
    components.sort(key=len, reverse=True)
    main = components[0]
    anchor = np.zeros((h, w), dtype=bool)
    for y, x in main:
        anchor[y, x] = True
    for _ in range(4):
        expanded = anchor.copy()
        expanded[1:, :] |= anchor[:-1, :]
        expanded[:-1, :] |= anchor[1:, :]
        expanded[:, 1:] |= anchor[:, :-1]
        expanded[:, :-1] |= anchor[:, 1:]
        expanded[1:, 1:] |= anchor[:-1, :-1]
        expanded[1:, :-1] |= anchor[:-1, 1:]
        expanded[:-1, 1:] |= anchor[1:, :-1]
        expanded[:-1, :-1] |= anchor[1:, 1:]
        anchor = expanded
    keep = np.zeros((h, w), dtype=bool)
    for pixels in components:
        if any(anchor[y, x] for y, x in pixels):
            for y, x in pixels:
                keep[y, x] = True
    rgba[~keep, 3] = 0
    rgba[~keep, :3] = 0
    return Image.fromarray(rgba, "RGBA")

def extract_cell(sheet, row, col):
    cell_w, cell_h = sheet.width // COLS, sheet.height // ROWS
    x0, y0 = col*cell_w, row*cell_h
    # Walk poses sit close to the bottom of their source cells. Extend the
    # crop into the clear gap before the run row so shoe outlines are not sliced.
    bottom_extra = 18 if row == 0 else 0
    cell = remove_magenta_matte(sheet.crop((x0, y0, x0+cell_w, min(sheet.height, y0+cell_h+bottom_extra))))
    cell = keep_main_character_component(cell)
    bbox = cell.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError(f"Empty new-cartoon pose at row {row}, column {col}")
    sprite = cell.crop(bbox)
    # Fit the complete silhouette inside the shared canvas. If the recovered
    # full artwork exceeds the safe bounds, scale it proportionally instead of
    # cropping a foot or outer outline.
    max_w, max_h = FRAME_W-8, FRAME_H-8
    if sprite.width > max_w or sprite.height > max_h:
        scale = min(max_w/sprite.width, max_h/sprite.height)
        size = (max(1, round(sprite.width*scale)), max(1, round(sprite.height*scale)))
        sprite = sprite.resize(size, Image.Resampling.LANCZOS)
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
save_cycle("carry-idle", 2, (3,))  # stationary, hands-forward carrying pose for launcher wind-up
