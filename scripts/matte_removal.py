"""Color-aware removal of JPEG magenta mattes with edge un-matting."""
import numpy as np
from PIL import Image
from scipy import ndimage

def remove_magenta_matte(image):
    """Remove border-connected magenta and reconstruct antialiased edge pixels."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[:, :, :3].astype(np.float32)
    h, w = rgb.shape[:2]
    border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]), axis=0)
    samples = border[(border[:, 0] > 90) & (border[:, 2] > 70)
                     & ((np.minimum(border[:, 0], border[:, 2]) - border[:, 1]) > 25)]
    if len(samples) < 8:
        raise RuntimeError("Could not reliably estimate magenta sheet color")
    bg = np.median(samples, axis=0)
    dist = np.sqrt(np.sum((rgb - bg) ** 2, axis=2))
    chroma = np.minimum(rgb[:, :, 0], rgb[:, :, 2]) - rgb[:, :, 1]
    candidate = (dist < 250) & (chroma > 8) & (rgb[:, :, 0] > 65) & (rgb[:, :, 2] > 55)
    seeds = np.zeros((h, w), dtype=bool)
    seeds[0, :] = candidate[0, :]
    seeds[-1, :] = candidate[-1, :]
    seeds[:, 0] |= candidate[:, 0]
    seeds[:, -1] |= candidate[:, -1]
    connected = ndimage.binary_propagation(seeds, structure=np.ones((3, 3), dtype=bool), mask=candidate)
    if not np.any(connected):
        raise RuntimeError("No border-connected magenta background detected")
    _, nearest = ndimage.distance_transform_edt(connected, return_indices=True)
    foreground = rgb[nearest[0], nearest[1]]
    delta = foreground - bg
    denom = np.sum(delta * delta, axis=2)
    observed = rgb - bg
    alpha = np.divide(np.sum(observed * delta, axis=2), denom,
                      out=np.zeros((h, w), dtype=np.float32), where=denom > 1.0)
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha[~connected] = 1.0
    alpha[connected & (alpha < 0.055)] = 0.0
    recover = connected & (alpha >= 0.055)
    recovered = np.zeros_like(rgb)
    a = alpha[recover][:, None]
    recovered[recover] = np.clip((rgb[recover] - (1.0 - a) * bg) / a, 0, 255)
    out_rgb = rgb.copy()
    out_rgb[recover] = recovered[recover]
    out_rgb[connected & ~recover] = 0
    out = np.dstack((out_rgb, alpha * 255.0)).round().clip(0, 255).astype(np.uint8)
    out[out[:, :, 3] == 0, :3] = 0
    return Image.fromarray(out, "RGBA")
