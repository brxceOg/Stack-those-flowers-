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
    rgba = np.asarray(cell.convert("RGBA"), dtype=np.uint8).copy()
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
    # Remove the sheet matte once on the full source image, while its true outer\n    # border is available for robust background-color estimation. Cropped cells\n    # are already transparent and must not re-estimate the matte from artwork.\n    sheet = remove_magenta_matte(Image.open(SOURCE).convert("RGB"))
    # Each illustration has its own explicit crop. The uploaded sheet is NOT
    # a uniform 2x3 grid: the middle and bottom rows sit at different heights,
    # so dividing it into equal-height bands cuts petals/stems and can include
    # pixels from the neighboring illustration.
    # Coordinates are source-image pixels (IMG_1380.jpeg, 399x447).
    crop_boxes = {
        "sunflower": (24, 0, 190, 184),
        "daisy": (225, 0, 399, 184),
        "red-bouquet": (24, 174, 198, 296),
        "bluebells": (222, 172, 399, 296),
        "tulip": (48, 294, 166, 435),
        "rose": (248, 292, 370, 435),
    }
    if sheet.width < 399 or sheet.height < 437:
        raise RuntimeError(f"Unexpected flower source dimensions: {sheet.size}; expected at least 399x437")
    atlas = Image.new("RGBA", (FRAME*len(NAMES), FRAME), (0,0,0,0))
    for i, name in enumerate(NAMES):
        cell = clean_cell(sheet.crop(crop_boxes[name]))
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
