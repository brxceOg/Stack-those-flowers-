from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

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
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[:, :, :3].astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    # Identify the vivid magenta field and its JPEG fringe, then remove only
    # the edge-connected region so artwork colors and highlights are retained.
    candidate = (r > 105) & (b > 95) & (g < 170) & ((r-g) > 35) & ((b-g) > 25)
    h, w = candidate.shape
    seen = np.zeros((h, w), dtype=bool)
    q = deque()
    def add(y, x):
        if candidate[y, x] and not seen[y, x]:
            seen[y, x] = True
            q.append((y, x))
    for x in range(w):
        add(0, x); add(h-1, x)
    for y in range(h):
        add(y, 0); add(y, w-1)
    while q:
        y, x = q.popleft()
        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny, nx = y+dy, x+dx
            if 0 <= ny < h and 0 <= nx < w:
                add(ny, nx)
    rgba[seen, 3] = 0
    rgba[seen, :3] = 0
    return Image.fromarray(rgba, "RGBA")

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
    # Keep all meaningful parts of the flower, including separated petals/leaves,
    # while discarding tiny JPEG noise left on the magenta field.
    keep = np.zeros((h, w), dtype=bool)
    for component in components:
        for y, x in component:
            keep[y, x] = True
    rgba[~keep, 3] = 0
    rgba[~keep, :3] = 0
    return Image.fromarray(rgba, "RGBA")

def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    sheet = Image.open(SOURCE).convert("RGB")
    if sheet.size != (399, 400):
        raise RuntimeError(f"Unexpected flower sheet size {sheet.size}; expected 399x400")
    # Explicit boundaries keep all six illustrations inside their own cells.
    x_edges = (0, 199, 399)
    y_edges = (0, 170, 300, 400)
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
