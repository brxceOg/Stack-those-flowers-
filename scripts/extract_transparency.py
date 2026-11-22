from pathlib import Path
from collections import deque
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)

def remove_connected_paper(src, dst):
    im = Image.open(ROOT / src).convert("RGBA")
    rgb = np.asarray(im.convert("RGB"), dtype=np.int16)
    h, w = rgb.shape[:2]
    paper = (rgb.min(axis=2) >= 226) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 34)
    seen = np.zeros((h, w), dtype=np.uint8)
    q = deque()
    for x in range(w):
        if paper[0, x]: seen[0, x] = 1; q.append((0, x))
        if paper[h-1, x] and not seen[h-1, x]: seen[h-1, x] = 1; q.append((h-1, x))
    for y in range(h):
        if paper[y, 0] and not seen[y, 0]: seen[y, 0] = 1; q.append((y, 0))
        if paper[y, w-1] and not seen[y, w-1]: seen[y, w-1] = 1; q.append((y, w-1))
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            ny = y + dy
            if ny < 0 or ny >= h: continue
            for dx in (-1, 0, 1):
                nx = x + dx
                if (dx == 0 and dy == 0) or nx < 0 or nx >= w: continue
                if paper[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = 1
                    q.append((ny, nx))
    rgba = np.asarray(im, dtype=np.uint8).copy()
    rgba[seen.astype(bool), 3] = 0
    rgba[rgba[:, :, 3] == 0, :3] = 0
    Image.fromarray(rgba, "RGBA").save(dst, optimize=True)
    alpha = np.asarray(Image.open(dst).convert("RGBA"))[:, :, 3]
    if not np.any(alpha == 0) or not np.any(alpha == 255):
        raise RuntimeError(f"Transparency validation failed for {dst}")
    print(f"{dst.relative_to(ROOT)}: {w}x{h}, transparent={int((alpha==0).sum())}, opaque={int((alpha==255).sum())}")

def connected_components(mask):
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=np.uint8)
    components = []
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
                    if ny < 0 or ny >= h: continue
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if (dx == 0 and dy == 0) or nx < 0 or nx >= w: continue
                        if mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = 1
                            stack.append((ny, nx))
            if len(xs) >= 700:
                components.append((min(xs), min(ys), max(xs)+1, max(ys)+1, len(xs)))
    return components

def clean_isolated_paper(crop):
    rgba = np.asarray(crop.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3] > 0
    paper = alpha & (rgb.min(axis=2) >= 220) & ((rgb.max(axis=2)-rgb.min(axis=2)) <= 42)
    support = alpha & ~paper
    near_support = support.copy()
    # Keep intentional white pixels that touch or sit immediately beside the colored/outlined sprite.
    for _ in range(2):
        expanded = near_support.copy()
        expanded[1:, :] |= near_support[:-1, :]
        expanded[:-1, :] |= near_support[1:, :]
        expanded[:, 1:] |= near_support[:, :-1]
        expanded[:, :-1] |= near_support[:, 1:]
        expanded[1:, 1:] |= near_support[:-1, :-1]
        expanded[1:, :-1] |= near_support[:-1, 1:]
        expanded[:-1, 1:] |= near_support[1:, :-1]
        expanded[:-1, :-1] |= near_support[1:, 1:]
        near_support = expanded
    rgba[paper & ~near_support, 3] = 0
    rgba[rgba[:, :, 3] == 0, :3] = 0
    return Image.fromarray(rgba, "RGBA")

def remove_tiny_alpha_components(crop, minimum_area=16):
    rgba = np.asarray(crop.convert("RGBA"), dtype=np.uint8).copy()
    mask = rgba[:, :, 3] > 0
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=np.uint8)
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]
            seen[sy, sx] = 1
            component = []
            while stack:
                y, x = stack.pop()
                component.append((y, x))
                for dy in (-1, 0, 1):
                    ny = y + dy
                    if ny < 0 or ny >= h: continue
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if (dx == 0 and dy == 0) or nx < 0 or nx >= w: continue
                        if mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = 1
                            stack.append((ny, nx))
            if len(component) < minimum_area:
                for y, x in component:
                    rgba[y, x, 3] = 0
                    rgba[y, x, :3] = 0
    return Image.fromarray(rgba, "RGBA")

def retain_sprite_components(crop, max_gap=3):
    rgba = np.asarray(crop.convert("RGBA"), dtype=np.uint8).copy()
    mask = rgba[:, :, 3] > 0
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=np.uint8)
    comps = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            stack = [(sy, sx)]
            seen[sy, sx] = 1
            pixels = []
            while stack:
                y, x = stack.pop()
                pixels.append((y, x))
                for dy in (-1, 0, 1):
                    ny = y + dy
                    if ny < 0 or ny >= h: continue
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if (dx == 0 and dy == 0) or nx < 0 or nx >= w: continue
                        if mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = 1
                            stack.append((ny, nx))
            comps.append(pixels)
    if not comps:
        return Image.fromarray(rgba, "RGBA")
    main = max(comps, key=len)
    keep = np.zeros((h, w), dtype=bool)
    for y, x in main:
        keep[y, x] = True
    for _ in range(max_gap):
        expanded = keep.copy()
        expanded[1:, :] |= keep[:-1, :]
        expanded[:-1, :] |= keep[1:, :]
        expanded[:, 1:] |= keep[:, :-1]
        expanded[:, :-1] |= keep[:, 1:]
        expanded[1:, 1:] |= keep[:-1, :-1]
        expanded[1:, :-1] |= keep[:-1, 1:]
        expanded[:-1, 1:] |= keep[1:, :-1]
        expanded[:-1, :-1] |= keep[1:, 1:]
        keep = expanded
    for pixels in comps:
        if any(keep[y, x] for y, x in pixels):
            for y, x in pixels:
                rgba[y, x, 3] = np.asarray(crop)[y, x, 3]
        else:
            for y, x in pixels:
                rgba[y, x, 3] = 0
                rgba[y, x, :3] = 0
    return Image.fromarray(rgba, "RGBA")

def extract_flower_sprite_sheet():
    """
    Extract only the four flower cutouts used in-game.
    The source labels sit above the flower row and were entering the old broad
    crops. Start below that heading, then retain the flower's connected artwork
    and nearby detached petals/leaves only.
    """
    atlas = Image.open(OUT / "flower-atlas.png").convert("RGBA")
    frame_w, frame_h = 65, 90
    # These are the established source columns for each flower variety.
    source_x = [145, 440, 720, 910]
    sheet = Image.new("RGBA", (frame_w * 4, frame_h), (0, 0, 0, 0))
    for i, sx in enumerate(source_x):
        # Exclude the heading band; the flower artwork sits below it.
        crop = atlas.crop((sx, 454, sx + frame_w, 520))
        crop = remove_tiny_alpha_components(crop, minimum_area=5)
        crop = retain_sprite_components(crop, max_gap=6)
        bbox = crop.getchannel("A").getbbox()
        if bbox is None:
            raise RuntimeError(f"Flower variety {i} produced an empty cutout")
        sprite = crop.crop(bbox)
        if sprite.width > frame_w or sprite.height > frame_h - 20:
            raise RuntimeError(f"Flower variety {i} exceeds its clean frame: {sprite.size}")
        frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        # Keep the original bottom alignment while removing the label pixels.
        frame.alpha_composite(sprite, ((frame_w - sprite.width) // 2,
                                       frame_h - sprite.height))
        sheet.alpha_composite(frame, (i * frame_w, 0))
        print(f"flower variety {i}: isolated artwork bounds={bbox}, canvas={frame_w}x{frame_h}")
    path = OUT / "flower-sprites.png"
    sheet.save(path, optimize=True)
    check = Image.open(path).convert("RGBA")
    if check.size != (frame_w * 4, frame_h):
        raise RuntimeError("Flower sprite sheet dimensions failed")
    alpha = np.asarray(check.getchannel("A"))
    for i in range(4):
        cell = alpha[:, i * frame_w:(i + 1) * frame_w]
        if not np.any(cell):
            raise RuntimeError(f"Flower sprite frame {i} is empty")
    print(f"{path.relative_to(ROOT)}: four isolated flower cutouts; {check.size}")


def extract_worker_cycles():
    # Segment each farmer pose from the transparent source by its connected silhouette.
    # Five clean frames per source cycle are present in the supplied top row.
    # This avoids fixed-width cells that can cut a pose or include its neighbor.
    atlas = Image.open(OUT / "flower-atlas.png").convert("RGBA")
    arr = np.asarray(atlas, dtype=np.uint8)
    if atlas.size != (1408, 768):
        raise RuntimeError(f"Unexpected source atlas size: {atlas.width}x{atlas.height}")
    # Only the top animation band; exclude the heading above it and all lower-row assets.
    top = arr[28:170, :, 3] > 0
    boxes = connected_components(top)
    boxes = [(x0, y0+28, x1, y1+28, area) for x0,y0,x1,y1,area in boxes
             if (y1-y0) >= 70 and (x1-x0) >= 45 and (x1-x0) <= 125]
    boxes.sort(key=lambda b: b[0])
    print("Detected top-row farmer components:", boxes)
    if len(boxes) != 10:
        raise RuntimeError(f"Expected 10 individually isolated farmer poses in the top row, detected {len(boxes)}. Refusing to create overlapping frames.")
    frame_w, frame_h, baseline = 128, 160, 151
    for name, group in (("walk", boxes[:5]), ("run", boxes[5:])):
        frames = []
        for i, (x0,y0,x1,y1,area) in enumerate(group):
            pad = 3
            crop = atlas.crop((max(0,x0-pad), max(30,y0-pad), min(atlas.width,x1+pad), min(atlas.height,y1+pad)))
            crop = clean_isolated_paper(crop)
            crop = remove_tiny_alpha_components(crop)
            crop = retain_sprite_components(crop, max_gap=3)
            bbox = crop.getchannel("A").getbbox()
            if bbox is None:
                raise RuntimeError(f"{name} frame {i} is empty")
            sprite = crop.crop(bbox)
            if sprite.width > frame_w-8 or sprite.height > frame_h-8:
                raise RuntimeError(f"{name} frame {i} exceeds frame canvas: {sprite.size}")
            frame = Image.new("RGBA", (frame_w, frame_h), (0,0,0,0))
            frame.alpha_composite(sprite, ((frame_w-sprite.width)//2, baseline-sprite.height))
            frames.append(frame)
        sheet = Image.new("RGBA", (frame_w*len(frames), frame_h), (0,0,0,0))
        for i, frame in enumerate(frames):
            sheet.alpha_composite(frame, (i*frame_w,0))
        path = OUT / f"worker-{name}.png"
        sheet.save(path, optimize=True)
        print(f"{path.relative_to(ROOT)}: {len(frames)} individually segmented poses; source boxes={group}")

remove_connected_paper("IMG_1369.jpeg", OUT / "flower-atlas.png")
remove_connected_paper("IMG_1370.jpeg", OUT / "flower-pile-atlas.png")
extract_flower_sprite_sheet()
# Worker extraction is intentionally owned only by extract_worker_sheet.py.
