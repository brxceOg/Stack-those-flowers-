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

def extract_worker_cycles():
    # Extract the actual source-sheet farmer walk and run poses as transparent animation frames.
    # Explicit, non-overlapping cells keep each pose isolated from its neighbors.
    atlas = Image.open(OUT / "flower-atlas.png").convert("RGBA")
    width, height = atlas.size
    if (width, height) != (1408, 768):
        raise RuntimeError(f"Unexpected source atlas size: {width}x{height}")
    walk_edges = [0, 114, 229, 343, 457, 572, 704]
    run_edges = [704, 802, 917, 1032, 1146, 1261, 1408]
    y0, y1 = 26, 166
    frame_w, frame_h, baseline = 128, 160, 151
    for name, edges in (("walk", walk_edges), ("run", run_edges)):
        frames = []
        for i, (left, right) in enumerate(zip(edges, edges[1:])):
            cell = atlas.crop((left, y0, right, y1))
            bbox = cell.getchannel("A").getbbox()
            if bbox is None:
                raise RuntimeError(f"{name} frame {i} is empty")
            sprite = cell.crop(bbox)
            if sprite.width > frame_w - 8 or sprite.height > frame_h - 8:
                raise RuntimeError(f"{name} frame {i} crop too large: {sprite.size}")
            frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
            frame.alpha_composite(sprite, ((frame_w-sprite.width)//2, baseline-sprite.height))
            frames.append(frame)
        sheet = Image.new("RGBA", (frame_w*len(frames), frame_h), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            sheet.alpha_composite(frame, (i*frame_w, 0))
        path = OUT / f"worker-{name}.png"
        sheet.save(path, optimize=True)
        for i in range(len(frames)):
            alpha = np.asarray(sheet.crop((i*frame_w, 0, (i+1)*frame_w, frame_h)).getchannel("A"))
            if not np.any(alpha > 0) or not np.any(alpha == 0):
                raise RuntimeError(f"Invalid {name} frame {i}")
        print(f"{path.relative_to(ROOT)}: {len(frames)} isolated real {name} poses")

remove_connected_paper("IMG_1369.jpeg", OUT / "flower-atlas.png")
remove_connected_paper("IMG_1370.jpeg", OUT / "flower-pile-atlas.png")
extract_worker_cycles()
