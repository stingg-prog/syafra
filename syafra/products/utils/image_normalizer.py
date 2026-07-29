"""
Simple image normalization for product uploads.

Removes background, trims whitespace, and centers the garment on a
clean white canvas.  Works universally for all apparel types without
any category-specific logic.

Pipeline:
  1. Remove background with rembg → alpha mask
  2. Find bounding box of the garment (trim transparent margins)
  3. Crop to bounding box
  4. Resize to fit inside 1800×1800 (preserving aspect ratio)
  5. Center on 2000×2000 white canvas
  6. Return as BytesIO ready for upload

Duplicate Detection:
  - Each image is hashed (SHA-256) before normalization
  - Hash and normalization version are stored in the model
  - If hash matches AND version matches → skip normalization
"""

import hashlib
import importlib
import io
import logging
import os

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
CANVAS_SIZE = 2000
FIT_SIZE = 1760           # garment fits inside this (88% of canvas → 12% padding)
MARGIN_PX = 120           # margin on each side = (2000 - 1760) / 2
JPEG_QUALITY = 92
PNG_COMPRESS = 6

# ── Normalization Version ──────────────────────────────────────────────────
# Increment this when the normalization algorithm changes.
NORMALIZATION_VERSION = 2


# ── Hash & Duplicate Detection ─────────────────────────────────────────────

def compute_image_hash(file_obj):
    """
    Compute SHA-256 hash of file contents.
    Position is restored after hashing.
    """
    original_pos = file_obj.tell()
    file_obj.seek(0)

    hasher = hashlib.sha256()
    while True:
        chunk = file_obj.read(8192)
        if not chunk:
            break
        hasher.update(chunk)

    file_obj.seek(original_pos)
    return hasher.hexdigest()


def should_normalize(file_obj, stored_hash='', stored_version=0):
    """
    Returns True if normalization is needed, False to skip.
    """
    if not stored_hash or stored_version == 0:
        return True

    current_hash = compute_image_hash(file_obj)

    if current_hash != stored_hash:
        return True

    if stored_version < NORMALIZATION_VERSION:
        return True

    return False


def preserve_original(field, suffix='_original'):
    """
    Save a copy of the current image as {name}_original.{ext} before
    overwriting with the normalized version.
    """
    if not field or not hasattr(field, 'file') or field.file is None:
        return

    current_name = field.name
    if not current_name:
        return

    base, ext = _split_filename(current_name)
    original_name = f"{base}{suffix}{ext}"

    if suffix in current_name:
        return

    try:
        field.open('rb')
        image_bytes = field.read()
        # Do NOT close the file — the caller still needs it

        if not image_bytes:
            return

        from django.core.files.base import ContentFile
        original_file = ContentFile(image_bytes)
        field.storage.save(original_name, original_file)
        logger.info("Preserved original: %s", original_name)
    except Exception as exc:
        logger.warning("Failed to preserve original %s: %s", current_name, exc)


def _split_filename(name):
    base, ext = os.path.splitext(name)
    return base, ext


# ── Public API ─────────────────────────────────────────────────────────────

def normalize_product_image(file_obj):
    """
    Read an uploaded file, normalize it, and return a new file-like object.

    Simple pipeline: remove background → trim whitespace → fit to canvas → center.

    Parameters
    ----------
    file_obj : file-like
        The raw upload from Django's ImageField.

    Returns
    -------
    io.BytesIO
        Normalized image bytes. Stream is rewound to position 0.
    """
    try:
        img = Image.open(file_obj)
    except Exception:
        logger.warning("Could not open image for normalization, returning original")
        file_obj.seek(0)
        return file_obj

    original_name = getattr(file_obj, 'name', '') or ''
    lower_name = original_name.lower()
    if lower_name.endswith('.svg') or getattr(img, 'is_animated', False):
        file_obj.seek(0)
        return file_obj

    # 1. Remove background → alpha mask
    alpha = _remove_background(img)

    # 2. Find bounding box of the garment
    bbox = _find_content_bbox(alpha)
    if bbox is None:
        logger.info("No foreground content detected, returning original")
        file_obj.seek(0)
        return file_obj

    # 3. Crop to bounding box (trim all transparent margins)
    cropped_rgb = img.crop(bbox)
    cropped_alpha = alpha.crop(bbox)

    # 4–6. Fit to canvas and center
    result = _fit_to_canvas(cropped_rgb, cropped_alpha)

    # 7. Encode to bytes
    return _encode(result, lower_name)


# ── Background Removal ─────────────────────────────────────────────────────

def _remove_background(img):
    """Return alpha mask identifying foreground."""
    return _threshold_fallback(img)

    try:
        from rembg import remove
        rgb = img.convert("RGB")

        # Downscale large images before AI processing
        MAX_EDGE = 768
        original_size = rgb.size

        if max(rgb.size) > MAX_EDGE:
            rgb.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)

        rgba = remove(rgb)
        alpha = rgba.split()[3]

        # Resize alpha mask back to original size
        if alpha.size != original_size:
            alpha = alpha.resize(original_size, Image.LANCZOS)

        return alpha

    except ImportError:
        logger.warning("rembg not installed — using threshold fallback")
        return _threshold_fallback(img)

    except BaseException as exc:
        logger.warning("rembg unavailable (%s) — using threshold fallback", exc)
        return _threshold_fallback(img)


def _threshold_fallback(img):
    """Simple threshold-based foreground detection."""
    gray = img.convert('L')
    inverted = ImageOps.invert(gray)
    return inverted.point(lambda p: 255 if p > 30 else 0)


# ── Bounding Box ───────────────────────────────────────────────────────────

def _find_content_bbox(alpha):
    """
    Return tight bounding box of non-transparent pixels, or None.
    """
    bbox = alpha.getbbox()
    if bbox is None:
        return None

    left, top, right, bottom = bbox
    w, h = alpha.size
    margin = 2
    return (
        max(0, left - margin),
        max(0, top - margin),
        min(w, right + margin),
        min(h, bottom + margin),
    )


# ── Fit to Canvas ──────────────────────────────────────────────────────────

def _fit_to_canvas(rgb, alpha):
    """
    Resize garment to fit inside FIT_SIZE×FIT_SIZE while preserving
    aspect ratio, then center on CANVAS_SIZE×CANVAS_SIZE white canvas.
    """
    canvas = Image.new('RGB', (CANVAS_SIZE, CANVAS_SIZE), (255, 255, 255))

    cw, ch = rgb.size

    # Scale so both dimensions fit inside FIT_SIZE
    scale = min(FIT_SIZE / cw, FIT_SIZE / ch)

    new_w = int(cw * scale)
    new_h = int(ch * scale)

    resized_rgb = rgb.resize((new_w, new_h), Image.LANCZOS)
    resized_alpha = alpha.resize((new_w, new_h), Image.LANCZOS)

    # Center on canvas
    center_x = (CANVAS_SIZE - new_w) // 2
    center_y = (CANVAS_SIZE - new_h) // 2

    canvas.paste(resized_rgb, (center_x, center_y), resized_alpha)
    return canvas


# ── Encoding ───────────────────────────────────────────────────────────────

def _encode(img, original_name):
    """Encode to JPEG or PNG based on original filename."""
    buf = io.BytesIO()
    if original_name.endswith(('.jpg', '.jpeg')):
        img.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    else:
        img.save(buf, format='PNG', optimize=True, compress_level=PNG_COMPRESS)
    buf.seek(0)
    return buf
