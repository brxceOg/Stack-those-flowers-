from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image
from matte_removal import remove_magenta_matte

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "IMG_1380.jpeg"
OUT = ROOT / "assets"
FRAME_DIR = OUT / "flower-frames"
OUT.mkdir(parents=True, exist_ok=True)
FRAME_DIR.mkdir(parents=True, exist_ok=True)

# The new sheet is a 2-column by 3-row grid:
# sunflower, daisy, red bouquet, bluebells, tulip, rose.
NAMES = ("sunflower", "daisy", "red-bouquet", "bluebells", "tulip", "rose")
FRAME = 224

def remove_magenta_background(image):
    return remove_magenta_matte(image)

def clean_cell(cell):
    rgba = np.asarray(remove_magenta_background(cell), dtype=np.uint8).copy()
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
                        ny, nx = y+dy, x+dx
                        if 0 <= ny < h and 0 <= nx < w and (dx or dy) and mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            if len(pixels) >= 12:
                components.append(pixels)
    if not components:
        raise RuntimeError("A flower cell became empty during magenta removal")
    # Keep the main flower silhouette and any detached leaves/details close to it.
    # This also rejects the top edge of the neighboring flower in the staggered rows.
    components.sort(key=len, reverse=True)
    anchor = np.zeros((h, w), dtype=bool)
    for y, x in components[0]:
        anchor[y, x] = True
    near = anchor.copy()
    for _ in range(12):
        expanded = near.copy()
        expanded[1:, :] |= near[:-1, :]
        expanded[:-1, :] |= near[1:, :]
        expanded[:, 1:] |= near[:, :-1]
        expanded[:, :-1] |= near[:, 1:]
        near = expanded
    keep = anchor.copy()
    for component in components[1:]:
        if any(near[y, x] for y, x in component):
            for y, x in component:
                keep[y, x] = True
    rgba[~keep, 3] = 0
    rgba[~keep, :3] = 0
    return Image.fromarray(rgba, "RGBA")

def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    sheet = Image.open(SOURCE).convert("RGB")
    # Derive cell boundaries from the uploaded sheet dimensions; its six illustrations
    # are arranged in two columns and three staggered-height rows.
    x_edges = (0, sheet.width // 2, sheet.width)
    y_edges = (0, round(sheet.height * 0.425), round(sheet.height * 0.715), sheet.height)
    atlas = Image.new("RGBA", (FRAME*len(NAMES), FRAME), (0,0,0,0))
    for i, name in enumerate(NAMES):
        row, col = divmod(i, 2)
        cell = sheet.crop((x_edges[col], y_edges[row], x_edges[col+1], y_edges[row+1]))
        cell = clean_cell(cell)
        bbox = cell.getchannel("A").getbbox()
        if bbox is None:
            raise RuntimeError(f"{name} extraction is empty")
        sprite = cell.crop(bbox)
        if sprite.width > FRAME-8 or sprite.height > FRAME-8:
            raise RuntimeError(f"{name} artwork exceeds frame without scaling: {sprite.size}")
        frame = Image.new("RGBA", (FRAME, FRAME), (0,0,0,0))
        # Center each flower horizontally and align its bottom at a common baseline.
        frame.alpha_composite(sprite, ((FRAME-sprite.width)//2, FRAME-4-sprite.height))
        path = FRAME_DIR / f"{name}.png"
        frame.save(path, optimize=True)
        check = Image.open(path).convert("RGBA")
        alpha = np.asarray(check.getchannel("A"))
        if check.size != (FRAME, FRAME) or alpha[0,0] != 0 or np.count_nonzero(alpha) < 500:
            raise RuntimeError(f"Alpha/frame validation failed for {name}")
        atlas.alpha_composite(frame, (i*FRAME, 0))
        print(f"{path.relative_to(ROOT)}: {sprite.size} artwork on {FRAME}x{FRAME} transparent frame")
    atlas_path = OUT / "flower-sprites.png"
    atlas.save(atlas_path, optimize=True)
    check = Image.open(atlas_path).convert("RGBA")
    if check.size != (FRAME*len(NAMES), FRAME):
        raise RuntimeError("Flower atlas dimensions failed")
    for i in range(len(NAMES)):
        alpha = np.asarray(check.crop((i*FRAME,0,(i+1)*FRAME,FRAME)).getchannel("A"))
        if not np.any(alpha == 0) or not np.any(alpha > 0):
            raise RuntimeError(f"Flower atlas cell {NAMES[i]} failed transparency validation")
    print(f"{atlas_path.relative_to(ROOT)}: six isolated flower varieties; {check.size}; alpha verified")

if __name__ == "__main__":
    main()
