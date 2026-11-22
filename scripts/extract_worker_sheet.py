from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "IMG_1375.jpeg"

# IMG_1375 is a 4-column x 4-row cartoon worker sheet on vivid magenta.
COLS, ROWS = 4, 4
FRAME_W, FRAME_H = 192, 224
MAGENTA = np.array([255.0, 0.0, 255.0], dtype=np.float32)


def remove_magenta_matte(image):
    """
    Remove the exterior magenta field by edge-connected flood fill.
    Antialiased boundary pixels are un-matted against the known magenta
    color, preserving the dark outline instead of leaving a pink fringe.
    """
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[:, :, :3].astype(np.float32)
    h, w = rgb.shape[:2]

    # Pixels close to the sheet's magenta background, including JPEG-softened
    # edge pixels, are eligible for the exterior flood fill.
    distance = np.max(np.abs(rgb - MAGENTA), axis=2)
    candidate = distance < 232.0
    seen = np.zeros((h, w), dtype=bool)
    q = deque()

    def add(y, x):
        if candidate[y, x] and not seen[y, x]:
            seen[y, x] = True
            q.append((y, x))

    for x in range(w):
        add(0, x)
        add(h - 1, x)
    for y in range(h):
        add(y, 0)
        add(y, w - 1)

    while q:
        y, x = q.popleft()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                add(ny, nx)

    # Estimate foreground opacity for the connected magenta matte pixels,
    # then reverse the magenta blend to keep antialiased outlines clean.
    edge = seen
    alpha = np.max(np.abs(rgb - MAGENTA), axis=2) / 255.0
    alpha = np.clip(alpha, 0.0, 1.0)
    safe = np.maximum(alpha, 1.0 / 255.0)
    unmatte = (rgb - (1.0 - alpha[:, :, None]) * MAGENTA) / safe[:, :, None]
    rgba[edge, :3] = np.clip(unmatte[edge], 0, 255).astype(np.uint8)
    rgba[edge, 3] = np.clip(alpha[edge] * 255.0, 0, 255).astype(np.uint8)
    rgba[rgba[:, :, 3] == 0, :3] = 0
    return Image.fromarray(rgba, "RGBA")


def extract_cell(sheet, row, col):
    cell_w = sheet.width / COLS
    cell_h = sheet.height / ROWS
    x0, x1 = round(col * cell_w), round((col + 1) * cell_w)
    y0, y1 = round(row * cell_h), round((row + 1) * cell_h)
    cell = remove_magenta_matte(sheet.crop((x0, y0, x1, y1)))
    bbox = cell.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError(f"Empty worker pose at row {row}, column {col}")
    sprite = cell.crop(bbox)
    if sprite.width > FRAME_W - 12 or sprite.height > FRAME_H - 12:
        raise RuntimeError(f"Worker pose {row},{col} too large: {sprite.size}")
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    frame.alpha_composite(
        sprite,
        ((FRAME_W - sprite.width) // 2, FRAME_H - 8 - sprite.height)
    )
    return frame


def write_sheet(frames, name):
    sheet = Image.new("RGBA", (FRAME_W * len(frames), FRAME_H), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sheet.alpha_composite(frame, (i * FRAME_W, 0))
    path = OUT / f"worker-{name}.png"
    sheet.save(path, optimize=True)
    check = Image.open(path).convert("RGBA")
    if check.size != (FRAME_W * len(frames), FRAME_H):
        raise RuntimeError(f"{name} sheet dimensions failed")
    alpha = np.asarray(check.getchannel("A"))
    for i in range(len(frames)):
        cell = alpha[:, i * FRAME_W:(i + 1) * FRAME_W]
        if not np.any(cell):
            raise RuntimeError(f"{name} frame {i} is empty")
    # The outer field must be genuinely transparent, not magenta-colored.
    if np.any(alpha[:, 0] == 255) and np.any(alpha[:, -1] == 255):
        raise RuntimeError(f"{name} sheet appears to retain opaque outer background")
    print(f"{path}: {len(frames)} frames, {check.size}; alpha verified")


source = Image.open(SOURCE).convert("RGBA")
if source.width < 4 or source.height < 4:
    raise RuntimeError("Worker source sheet is unexpectedly small")
if abs(source.width / source.height - 1.5) > 0.08:
    raise RuntimeError(f"Unexpected worker sheet aspect ratio: {source.size}")

# Top row: four distinct walking poses.
walk = [extract_cell(source, 0, c) for c in range(4)]
# Second row: four distinct running poses.
run = [extract_cell(source, 1, c) for c in range(4)]
# Third row: crouch/reach and effort poses only (columns 1 and 2).
pick = [extract_cell(source, 2, c) for c in (1, 2)]
# Bottom row: carrying poses, used while returning flowers to the launcher.
carry = [extract_cell(source, 3, c) for c in range(4)]
if len(pick) != 2:
    raise RuntimeError("Picking sequence must contain exactly two crouch/grab poses")

for name, frames in (("walk", walk), ("run", run), ("pick", pick), ("carry", carry)):
    write_sheet(frames, name)
