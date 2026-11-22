from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "IMG_1378.jpeg"
OUT = ROOT / "assets"
FRAME_DIR = OUT / "flower-launcher-frames"
COLS = ROWS = 3
FRAME_W, FRAME_H = 224, 150

def remove_magenta_background(image):
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[:, :, :3].astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    # Bright magenta field plus JPEG edge contamination; retain warm cream,
    # brown, orange and dark purple artwork by requiring strong red/blue chroma.
    candidate = (r > 105) & (b > 85) & (g < 185) & ((r-g) > 45) & ((b-g) > 35)
    h, w = candidate.shape
    seen = np.zeros((h, w), dtype=bool)
    queue = deque()
    def add(y, x):
        if candidate[y, x] and not seen[y, x]:
            seen[y, x] = True
            queue.append((y, x))
    for x in range(w):
        add(0, x); add(h-1, x)
    for y in range(h):
        add(y, 0); add(y, w-1)
    while queue:
        y, x = queue.popleft()
        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny, nx = y+dy, x+dx
            if 0 <= ny < h and 0 <= nx < w:
                add(ny, nx)
    rgba[seen] = (0, 0, 0, 0)
    return Image.fromarray(rgba, "RGBA")

def extract_cell(sheet, row, col):
    cw = sheet.width // COLS
    y0 = round(row * sheet.height / ROWS)
    y1 = round((row + 1) * sheet.height / ROWS)
    cell = remove_magenta_background(sheet.crop((col*cw, y0, (col+1)*cw, y1)))
    bbox = cell.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"Empty launcher frame at row {row}, column {col}")
    sprite = cell.crop(bbox)
    if sprite.width > FRAME_W-8 or sprite.height > FRAME_H-8:
        raise RuntimeError(f"Launcher frame too large for native-ratio canvas: {sprite.size}")
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0,0,0,0))
    frame.alpha_composite(sprite, ((FRAME_W-sprite.width)//2, FRAME_H-sprite.height-3))
    return frame

def save_cycle(name, row):
    frames = [extract_cell(sheet, row, col) for col in range(COLS)]
    atlas = Image.new("RGBA", (FRAME_W*len(frames), FRAME_H), (0,0,0,0))
    for i, frame in enumerate(frames):
        path = FRAME_DIR / f"{name}-{i+1:02d}.png"
        frame.save(path, optimize=True)
        check = Image.open(path).convert("RGBA")
        alpha = np.asarray(check.getchannel("A"))
        if check.size != (FRAME_W, FRAME_H) or alpha[0,0] != 0 or np.count_nonzero(alpha) < 1000:
            raise RuntimeError(f"Alpha/dimension validation failed: {path}")
        atlas.alpha_composite(frame, (i*FRAME_W, 0))
    path = OUT / f"flower-launcher-{name}.png"
    atlas.save(path, optimize=True)
    check = Image.open(path).convert("RGBA")
    if check.size != (FRAME_W*3, FRAME_H) or check.getchannel("A").getpixel((0,0)) != 0:
        raise RuntimeError(f"Atlas validation failed: {path}")
    print(f"{path.relative_to(ROOT)}: 3 isolated frames, {check.size}, transparent alpha verified")

if not SOURCE.is_file():
    raise FileNotFoundError(SOURCE)
sheet = Image.open(SOURCE).convert("RGBA")
if sheet.size != (657, 439):
    raise RuntimeError(f"Unexpected IMG_1378.jpeg dimensions {sheet.size}; expected 657x439 3x3")
FRAME_DIR.mkdir(parents=True, exist_ok=True)
# Row 1: flower collection; row 2: charging; row 3: firing.
for name, row in (("collection",0),("charge",1),("fire",2)):
    save_cycle(name, row)
