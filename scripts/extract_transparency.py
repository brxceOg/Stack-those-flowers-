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

    # Only near-neutral, very light pixels can be paper. Flood-fill from the
    # outer border so enclosed whites (petals, highlights, shirt details)
    # remain part of the artwork.
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    paper = (mn >= 226) & ((mx - mn) <= 34)

    seen = np.zeros((h, w), dtype=np.uint8)
    q = deque()

    # Seed every eligible border pixel.
    for x in range(w):
        if paper[0, x]: seen[0, x] = 1; q.append((0, x))
        if paper[h-1, x] and not seen[h-1, x]: seen[h-1, x] = 1; q.append((h-1, x))
    for y in range(h):
        if paper[y, 0] and not seen[y, 0]: seen[y, 0] = 1; q.append((y, 0))
        if paper[y, w-1] and not seen[y, w-1]: seen[y, w-1] = 1; q.append((y, w-1))

    # 8-connected fill removes JPEG's near-white fringe without punching
    # holes through dark-outlined white artwork.
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

    # Fully clear RGB under transparent pixels to avoid white matte in tools
    # that mishandle premultiplied alpha. Preserve all visible edge colors.
    rgba[rgba[:, :, 3] == 0, :3] = 0
    Image.fromarray(rgba, "RGBA").save(dst, optimize=True)

    # Basic acceptance checks.
    check = Image.open(dst).convert("RGBA")
    alpha = np.asarray(check)[:, :, 3]
    if not np.any(alpha == 0) or not np.any(alpha == 255):
        raise RuntimeError(f"Transparency validation failed for {dst}")
    print(f"{dst.relative_to(ROOT)}: {w}x{h}, transparent={int((alpha==0).sum())}, opaque={int((alpha==255).sum())}")

remove_connected_paper("IMG_1369.jpeg", OUT / "flower-atlas.png")
remove_connected_paper("IMG_1370.jpeg", OUT / "flower-pile-atlas.png")
