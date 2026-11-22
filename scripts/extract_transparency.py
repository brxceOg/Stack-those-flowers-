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

def extract_worker_cycles():
    # Extract the actual farmer artwork from the two top-row animation groups.
    # Each group contains six visible poses in the supplied source sheet.
    # Crop boundaries are explicit, so no frame can sample its neighbor.
    atlas = Image.open(OUT / "flower-atlas.png").convert("RGBA")
    width, height = atlas.size
    if (width, height) != (1408, 768):
        raise RuntimeError(f"Unexpected source atlas size: {width}x{height}")

    walk_edges = [0, 114, 229, 343, 457, 572, 704]
    run_edges  = [704, 802, 917, 1032, 1146, 1261, 1408]
    y0, y1 = 26, 166
    frame_w, frame_h = 128, 160
    baseline = 151

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
            x = (frame_w - sprite.width) // 2
            y = baseline - sprite.height
            frame.alpha_composite(sprite, (x, y))
            frames.append(frame)

        sheet = Image.new("RGBA", (frame_w * len(frames), frame_h), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            sheet.alpha_composite(frame, (i * frame_w, 0))
        path = OUT / f"worker-{name}.png"
        sheet.save(path, optimize=True)

        # Validate each frame independently: no alpha may escape its cell.
        for i in range(len(frames)):
            frame = sheet.crop((i * frame_w, 0, (i + 1) * frame_w, frame_h))
            alpha = np.asarray(frame.getchannel("A"))
            if not np.any(alpha > 0) or not np.any(alpha == 0):
                raise RuntimeError(f"Bad alpha in {name} frame {i}")
        print(f"{path.relative_to(ROOT)}: {len(frames)} real {name} poses, isolated at {frame_w}x{frame_h}")

extract_worker_cycles():
    # The first row of IMG_1369 contains five walk poses followed by five
    # run poses. Split by fixed source cells first, then trim each cell to
    # its own alpha bounds so no adjacent pose can bleed into a frame.
    atlas = Image.open(OUT / "flower-atlas.png").convert("RGBA")
    width, height = atlas.size
    cols = 10
    cell_w = width / cols
    y0, y1 = 28, 174
    frame_w, frame_h = 128, 160
    baseline = 154

    cycles = {"walk": [], "run": []}
    for i in range(cols):
        left = round(i * cell_w)
        right = round((i + 1) * cell_w)
        cell = atlas.crop((left, y0, right, y1))
        alpha = cell.getchannel("A")
        bbox = alpha.getbbox()
        if bbox is None:
            raise RuntimeError(f"Worker frame {i} is empty")
        sprite = cell.crop(bbox)
        if sprite.width > frame_w - 8 or sprite.height > frame_h - 8:
            raise RuntimeError(f"Worker frame {i} exceeds safe canvas: {sprite.size}")
        frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        px = (frame_w - sprite.width) // 2
        py = baseline - sprite.height
        frame.alpha_composite(sprite, (px, py))
        cycles["walk" if i < 5 else "run"].append(frame)

    for name, frames in cycles.items():
        sheet = Image.new("RGBA", (frame_w * len(frames), frame_h), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            sheet.alpha_composite(frame, (i * frame_w, 0))
        path = OUT / f"worker-{name}.png"
        sheet.save(path, optimize=True)
        # Verify every frame has transparent canvas and opaque art, and no
        # frame's alpha bounds spill into its neighboring cell.
        for i in range(len(frames)):
            frame = sheet.crop((i * frame_w, 0, (i + 1) * frame_w, frame_h))
            a = np.asarray(frame.getchannel("A"))
            if not np.any(a == 0) or not np.any(a > 0):
                raise RuntimeError(f"Invalid alpha in {name} frame {i}")
        print(f"{path.relative_to(ROOT)}: {len(frames)} isolated {name} frames, {frame_w}x{frame_h} each")

extract_worker_cycles()
