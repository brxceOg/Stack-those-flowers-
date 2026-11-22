from pathlib import Path
from collections import deque
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / "IMG_1371.jpeg"
FRAME_W, FRAME_H, BASELINE = 160, 208, 198

def connected_components(mask, min_area=250):
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
                    if ny < 0 or ny >= h: continue
                    for dx in (-1, 0, 1):
                        nx = x + dx
                        if (dx == 0 and dy == 0) or nx < 0 or nx >= w: continue
                        if mask[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = 1
                            stack.append((ny, nx))
            if len(xs) >= min_area:
                x0,x1,y0,y1=min(xs),max(xs)+1,min(ys),max(ys)+1
                if x1-x0 >= 38 and y1-y0 >= 65:
                    boxes.append((x0,y0,x1,y1,len(xs)))
    return boxes

def clean_crop(crop):
    a = np.asarray(crop.convert("RGBA"), dtype=np.uint8).copy()
    rgb = a[:,:,:3].astype(np.int16)
    paper = (rgb.min(axis=2) >= 218) & ((rgb.max(axis=2)-rgb.min(axis=2)) <= 48)
    # Remove only paper pixels that are connected to the crop boundary.
    h,w=paper.shape
    seen=np.zeros((h,w),dtype=bool)
    q=deque()
    for x in range(w):
        if paper[0,x]: seen[0,x]=1; q.append((0,x))
        if paper[h-1,x] and not seen[h-1,x]: seen[h-1,x]=1; q.append((h-1,x))
    for y in range(h):
        if paper[y,0] and not seen[y,0]: seen[y,0]=1; q.append((y,0))
        if paper[y,w-1] and not seen[y,w-1]: seen[y,w-1]=1; q.append((y,w-1))
    while q:
        y,x=q.popleft()
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                ny,nx=y+dy,x+dx
                if 0<=ny<h and 0<=nx<w and paper[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx]=1; q.append((ny,nx))
    a[seen,3]=0
    a[a[:,:,3]==0,:3]=0
    return Image.fromarray(a,"RGBA")

def build_sheet(source, boxes, name):
    frames=[]
    for i,(x0,y0,x1,y1,_) in enumerate(boxes):
        crop=clean_crop(source.crop((max(0,x0-5),max(0,y0-5),min(source.width,x1+5),min(source.height,y1+5))))
        bbox=crop.getchannel("A").getbbox()
        if not bbox: raise RuntimeError(f"{name} frame {i} is empty")
        sprite=crop.crop(bbox)
        if sprite.width>FRAME_W-8 or sprite.height>FRAME_H-8:
            raise RuntimeError(f"{name} frame {i} exceeds {FRAME_W}x{FRAME_H}: {sprite.size}")
        frame=Image.new("RGBA",(FRAME_W,FRAME_H),(0,0,0,0))
        frame.alpha_composite(sprite,((FRAME_W-sprite.width)//2,BASELINE-sprite.height))
        frames.append(frame)
    sheet=Image.new("RGBA",(FRAME_W*len(frames),FRAME_H),(0,0,0,0))
    for i,frame in enumerate(frames):
        sheet.alpha_composite(frame,(i*FRAME_W,0))
    path=OUT/f"worker-{name}.png"
    sheet.save(path,optimize=True)
    check=Image.open(path).convert("RGBA")
    if check.size!=(FRAME_W*len(frames),FRAME_H) or check.getchannel("A").getextrema()[0]!=0:
        raise RuntimeError(f"Alpha/canvas validation failed: {path}")
    print(f"{path}: {len(frames)} frames, {check.size}, transparent canvas verified")

im=Image.open(SOURCE).convert("RGBA")
rgb=np.asarray(im.convert("RGB"),dtype=np.int16)
paper=(rgb.min(axis=2)>=218)&((rgb.max(axis=2)-rgb.min(axis=2))<=48)
components=connected_components(~paper, min_area=250)
# Three clearly separated horizontal animation rows in IMG_1371.
bands=[(0,int(im.height*.34)),(int(im.height*.34),int(im.height*.67)),(int(im.height*.67),im.height)]
rows=[]
for y0,y1 in bands:
    row=sorted([b for b in components if b[1]>=y0 and b[3]<=y1],key=lambda b:b[0])
    rows.append(row)
counts=[len(r) for r in rows]
print(f"Detected row frame counts: {counts}; source size: {im.size}")
if counts != [10,10,10]:
    raise RuntimeError(f"Unexpected sprite layout {counts}; expected [10, 10, 10]. Refusing unsafe extraction.")
# Row 1 and row 2 begin with crouch/standing setup poses; retain only active travel poses.
build_sheet(im,rows[0][3:],"walk")
build_sheet(im,rows[1][2:],"run")
# Row 3 is the dedicated flower-picking action sequence, including its crouch-to-reach motion.
build_sheet(im,rows[2],"pick")
