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
    candidate = (dist < 280) & (chroma > 18) & (rgb[:, :, 0] > 130) & (rgb[:, :, 2] > 115)
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
    # Keep the extracted edge's original structure, but neutralize the
    # magenta channel excess on the retained antialias rim. The outline is
    # intentionally dark; subtracting the same spill from red and blue keeps
    # its luminance/detail while removing the pink cast.
    out_rgb = rgb.copy()
    spill = np.maximum(0.0, np.minimum(rgb[:, :, 0], rgb[:, :, 2]) - rgb[:, :, 1])
    out_rgb[recover, 0] = np.maximum(0.0, rgb[recover, 0] - spill[recover])
    out_rgb[recover, 2] = np.maximum(0.0, rgb[recover, 2] - 0.92 * spill[recover])
    out_rgb[connected & ~recover] = 0
    out = np.dstack((out_rgb, alpha * 255.0)).round().clip(0, 255).astype(np.uint8)
    out[out[:, :, 3] == 0, :3] = 0
    return Image.fromarray(out, "RGBA")
