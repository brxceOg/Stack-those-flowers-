from pathlib import Path
from collections import deque
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "IMG_1372.jpeg"
FRAME_W, FRAME_H = 160, 224
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

def keep_largest_art_component(crop):
    """Discard detached specks/fragments after the sprite has been isolated."""
    rgba = np.asarray(crop.convert("RGBA"), dtype=np.uint8).copy()
    mask = rgba[:, :, 3] > 0
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    largest = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]
            seen[sy, sx] = True
            component = []
            while stack:
                y, x = stack.pop()
                component.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            if len(component) > len(largest):
                largest = component
    if not largest:
        raise RuntimeError("Isolated worker cell contains no connected artwork")
    keep = np.zeros((h, w), dtype=bool)
    ys, xs = zip(*largest)
    keep[np.asarray(ys), np.asarray(xs)] = True
    rgba[~keep] = 0
    return Image.fromarray(rgba, "RGBA")


def extract_row_cells(source, row_boxes, y0, y1):
    """Use the gaps between adjacent pose bounds as hard per-frame cut lines."""
    row_boxes = sorted(row_boxes, key=lambda b: b[0])
    if len(row_boxes) != FRAME_COUNT_PER_ROW:
        raise RuntimeError(f"Expected 10 worker poses in row, found {len(row_boxes)}")
    # Prefer the true empty gutter between silhouette bounds. Where two poses'
    # bounding boxes overlap, find the least-painted vertical seam between their
    # centers instead of assigning detached components by nearest-center guessing.
    row_rgba = np.asarray(source.crop((0, y0, source.width, y1)).convert("RGBA"))
    row_rgb = row_rgba[:, :, :3].astype(np.int16)
    row_paper = (row_rgb.min(axis=2) >= 218) & ((row_rgb.max(axis=2) - row_rgb.min(axis=2)) <= 48)
    ink = (~row_paper).sum(axis=0)
    centers = [(b[0] + b[2]) / 2 for b in row_boxes]
    cuts = [0]
    for left_box, right_box, left_center, right_center in zip(
        row_boxes, row_boxes[1:], centers, centers[1:]
    ):
        gap_start, gap_end = left_box[2], right_box[0]
        if gap_end > gap_start:
            cut = (gap_start + gap_end) // 2
        else:
            lo = max(1, int(np.floor(left_center)) + 1)
            hi = min(source.width - 1, int(np.ceil(right_center)))
            if hi <= lo:
                raise RuntimeError("Cannot find a safe seam between adjacent poses")
            # Stay away from the outermost pixels of each pose; choose the
            # column with the fewest painted pixels in the overlapping span.
            candidates = np.arange(lo, hi)
            cut = int(candidates[np.argmin(ink[candidates])])
        cuts.append(cut)
    cuts.append(source.width)
    frames = []
    for i in range(FRAME_COUNT_PER_ROW):
        x0, x1 = cuts[i], cuts[i + 1]
        if x1 <= x0:
            raise RuntimeError(f"Invalid frame boundary at row frame {i}")
        # Crop the entire isolated cell, not just the connected-component bbox.
        crop = remove_connected_paper(source.crop((x0, y0, x1, y1)))
        # A pose in this source sheet is one connected silhouette. Remove any
        # disconnected flecks that crossed a seam from a neighboring pose.
        crop = keep_largest_art_component(crop)
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

def extract_pick_frames(source, row_boxes, y0, y1):
    """
    Build each picking pose from its own connected artwork components.
    Detached pixels are assigned to the nearest worker pose, not copied just
    because they happen to fall inside a rectangular crop from a neighbor.
    """
    row_boxes = sorted(row_boxes, key=lambda b: b[0])
    if len(row_boxes) != FRAME_COUNT_PER_ROW:
        raise RuntimeError(f"Expected 10 picking poses, found {len(row_boxes)}")

    # Remove only exterior paper first; intentional white shirt/highlight pixels survive.
    cleaned = remove_connected_paper(source.crop((0, y0, source.width, y1)))
    rgba = np.asarray(cleaned, dtype=np.uint8)
    mask = rgba[:, :, 3] > 0
    h, w = mask.shape

    # Label every remaining connected artwork component, including small detached
    # pieces. Each piece is assigned to the closest full-size worker pose.
    labels = np.zeros((h, w), dtype=np.int32)
    components = []
    next_label = 0
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or labels[sy, sx]:
                continue
            next_label += 1
            stack = [(sy, sx)]
            labels[sy, sx] = next_label
            xs, ys = [], []
            while stack:
                cy, cx = stack.pop()
                xs.append(cx)
                ys.append(cy)
                for dy in (-1, 0, 1):
                    ny = cy + dy
                    if ny < 0 or ny >= h:
                        continue
                    for dx in (-1, 0, 1):
                        nx = cx + dx
                        if (dx == 0 and dy == 0) or nx < 0 or nx >= w:
                            continue
                        if mask[ny, nx] and not labels[ny, nx]:
                            labels[ny, nx] = next_label
                            stack.append((ny, nx))
            if len(xs) >= 2:
                components.append((next_label, np.asarray(xs), np.asarray(ys)))

    centers = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2 - y0) for b in row_boxes]
    owner = {}
    for label, xs, ys in components:
        cx, cy = float(xs.mean()), float(ys.mean())
        nearest = min(range(len(centers)),
                      key=lambda i: (cx - centers[i][0]) ** 2 + (cy - centers[i][1]) ** 2)
        owner[label] = nearest

    frames = []
    for i, box in enumerate(row_boxes):
        keep = np.zeros((h, w), dtype=bool)
        for label, xs, ys in components:
            if owner[label] == i:
                keep[ys, xs] = True
        if not np.any(keep):
            raise RuntimeError(f"Picking frame {i} lost all artwork")

        ys, xs = np.where(keep)
        # Tight crop around only this pose's assigned pixels; add transparent padding.
        x0 = max(0, int(xs.min()) - 4)
        x1 = min(w, int(xs.max()) + 5)
        cy0 = max(0, int(ys.min()) - 4)
        cy1 = min(h, int(ys.max()) + 5)
        sprite = rgba[cy0:cy1, x0:x1].copy()
        local_keep = keep[cy0:cy1, x0:x1]
        sprite[~local_keep, 3] = 0
        sprite[sprite[:, :, 3] == 0, :3] = 0
        sprite_img = Image.fromarray(sprite, "RGBA")

        if sprite_img.width > FRAME_W - 8 or sprite_img.height > FRAME_H - 8:
            raise RuntimeError(f"Picking frame {i} artwork {sprite_img.size} exceeds safe canvas")
        frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        frame.alpha_composite(sprite_img, ((FRAME_W - sprite_img.width) // 2,
                                           FRAME_H - 8 - sprite_img.height))
        frames.append(frame)

    # Strict per-cell isolation audit: no opaque pixels may exist outside each frame.
    for i, frame in enumerate(frames):
        alpha = np.asarray(frame.getchannel("A"))
        if not np.any(alpha):
            raise RuntimeError(f"Picking frame {i} is empty")
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
walk = extract_row_cells(im, *rows[0])
run = extract_row_cells(im, *rows[1])
# The source's third row starts with the two actual crouch-and-grab poses.
# The remaining poses in that row are upright travel/transition artwork and
# must not be included in the flower-picking loop.
pick_row = extract_row_cells(im, *rows[2])
pick = pick_row[:2]
if len(pick) != 2:
    raise RuntimeError("Picking sequence must contain exactly the two crouch/grab poses")
write_sheet(walk[3:], "walk")
# Row 2 frames 0-2 are crouch/standing transitions; only frames 3-9 form the active run cycle.
write_sheet(run[3:], "run")
write_sheet(pick, "pick")
