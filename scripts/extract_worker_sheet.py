from pathlib import Path
from collections import deque
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "IMG_1371.jpeg"
FRAME_W, FRAME_H = 160, 208
FRAME_COUNT_PER_ROW = 10
ROW_COUNT = 3

def connected_components(mask, min_area=250):
    """Locate each large worker pose; do not use this tight box as the crop."""
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=np.uint8)
    boxes = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]
            seen[sy, sx] = 1
            xs, ys = [], []
            while stack:
                y, x = stack.pop()
                xs.append(x); ys.append(y)
                for dy in (-1, 0, 1):
                    ny = y + dy
                    if ny < 0 or ny >= h:
                        continue
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if (dx == 0 and dy == 0) or nx < 0 or nx >= w:
                            continue
                        if mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = 1
                            stack.append((ny, nx))
            if len(xs) >= min_area:
                x0, x1 = min(xs), max(xs) + 1
                y0, y1 = min(ys), max(ys) + 1
                if x1 - x0 >= 38 and y1 - y0 >= 65:
                    boxes.append((x0, y0, x1, y1, len(xs)))
    return boxes

def remove_connected_paper(crop):
    """Make only exterior paper transparent, preserving white pixels inside art."""
    a = np.asarray(crop.convert("RGBA"), dtype=np.uint8).copy()
    rgb = a[:, :, :3].astype(np.int16)
    paper = (rgb.min(axis=2) >= 218) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 48)
    h, w = paper.shape
    seen = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if paper[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if paper[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and paper[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
    a[seen, 3] = 0
    a[a[:, :, 3] == 0, :3] = 0
    return Image.fromarray(a, "RGBA")

def extract_row_cells(source, row_boxes, y0, y1):
    """Use the gaps between adjacent pose bounds as hard per-frame cut lines."""
    row_boxes = sorted(row_boxes, key=lambda b: b[0])
    if len(row_boxes) != FRAME_COUNT_PER_ROW:
        raise RuntimeError(f"Expected 10 worker poses in row, found {len(row_boxes)}")
    cuts = [0]
    for left, right in zip(row_boxes, row_boxes[1:]):
        gap_start, gap_end = left[2], right[0]
        if gap_end <= gap_start:
            raise RuntimeError("Adjacent worker artwork touches/overlaps; cannot safely split frames")
        cuts.append((gap_start + gap_end) // 2)
    cuts.append(source.width)
    frames = []
    for i in range(FRAME_COUNT_PER_ROW):
        x0, x1 = cuts[i], cuts[i + 1]
        if x1 <= x0:
            raise RuntimeError(f"Invalid frame boundary at row frame {i}")
        # Crop the entire isolated cell, not just the connected-component bbox.
        crop = remove_connected_paper(source.crop((x0, y0, x1, y1)))
        bbox = crop.getchannel("A").getbbox()
        if bbox is None:
            raise RuntimeError(f"Frame {i} has no visible pixels")
        sprite = crop.crop(bbox)
        if sprite.width > FRAME_W - 8 or sprite.height > FRAME_H - 8:
            raise RuntimeError(f"Frame {i} artwork {sprite.size} exceeds safe canvas")
        frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        # Align feet to a common baseline; center the full artwork horizontally.
        frame.alpha_composite(sprite, ((FRAME_W - sprite.width) // 2, FRAME_H - 8 - sprite.height))
        alpha = np.asarray(frame.getchannel("A"))
        ys, xs = np.where(alpha > 0)
        if len(xs) == 0 or xs.min() < 0 or xs.max() >= FRAME_W or ys.min() < 0 or ys.max() >= FRAME_H:
            raise RuntimeError(f"Frame {i} failed boundary validation")
        frames.append(frame)
    return frames

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
    # Every frame must contain artwork only within its own 160px cell.
    for i in range(len(frames)):
        cell = alpha[:, i * FRAME_W:(i + 1) * FRAME_W]
        if not np.any(cell):
            raise RuntimeError(f"{name} frame {i} is empty")
    print(f"{path}: {len(frames)} frames, {check.size}; frame boundaries validated")

im = Image.open(SOURCE).convert("RGBA")
rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
paper = (rgb.min(axis=2) >= 218) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 48)
components = connected_components(~paper, min_area=250)
row_edges = [round(im.height * i / ROW_COUNT) for i in range(ROW_COUNT + 1)]
rows = []
for row_index in range(ROW_COUNT):
    y0, y1 = row_edges[row_index], row_edges[row_index + 1]
    row = [b for b in components if b[1] >= y0 and b[3] <= y1]
    row = sorted(row, key=lambda b: b[0])
    if len(row) != FRAME_COUNT_PER_ROW:
        raise RuntimeError(f"Row {row_index + 1}: expected 10 poses, detected {len(row)}")
    rows.append((row, y0, y1))

# Keep the intended action groups: active walk strides, active run strides,
# and the complete crouch/reach/stand flower-picking action.
walk, wy0, wy1 = extract_row_cells(im, *rows[0])
run, ry0, ry1 = extract_row_cells(im, *rows[1])
pick, py0, py1 = extract_row_cells(im, *rows[2])
write_sheet(walk[3:], "walk")
write_sheet(run[2:], "run")
write_sheet(pick, "pick")
