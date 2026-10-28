"""
Simple image normalization for product uploads.

Removes background, trims whitespace, and centers the garment on a
warm beige studio canvas. Works for apparel without category-specific logic.

Pipeline:
  1. Remove background with rembg → alpha mask
  2. Find bounding box of the garment (trim transparent margins)
  3. Crop to bounding box
  4. Resize to fit inside 1580×1580 (preserving aspect ratio)
  5. Center on a 2000×2000 beige wall with angled sunlight and a soft shadow
  6. Return as BytesIO ready for upload

Duplicate Detection:
  - Each image is hashed (SHA-256) before normalization
  - Hash and normalization version are stored in the model
  - If hash matches AND version matches → skip normalization
"""

import hashlib
import io
import logging
import os
from decimal import Decimal, InvalidOperation

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────
CANVAS_SIZE = 2000
FIT_SIZE = 1580           # Leave room for warm studio lighting and the price callout.
JPEG_QUALITY = 94
PNG_COMPRESS = 6

# ── Normalization Version ──────────────────────────────────────────────────
# Increment this when the normalization algorithm changes.
NORMALIZATION_VERSION = 4


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

    Product-photo pipeline: remove background → trim whitespace → add soft
    beige studio lighting and a natural shadow → center on a square canvas.

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
        img = ImageOps.exif_transpose(img)
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
        logger.warning("No foreground detected; fitting the full image to the product canvas")
        alpha = Image.new('L', img.size, 255)
        bbox = (0, 0, img.width, img.height)

    # 3. Crop to bounding box (trim all transparent margins)
    cropped_rgb = img.crop(bbox)
    cropped_alpha = alpha.crop(bbox)

    # 4–6. Fit to the Syafra warm-studio canvas and center.
    result = _fit_to_canvas(cropped_rgb, cropped_alpha)

    # 7. Encode to bytes
    return _encode(result, lower_name)


# ── Background Removal ─────────────────────────────────────────────────────

def _remove_background(img):
    """Return alpha mask identifying foreground."""
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
    aspect ratio, then center on a warm beige studio canvas with a soft shadow.
    """
    canvas = _studio_background(CANVAS_SIZE, CANVAS_SIZE)

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

    # A gentle down-right shadow adds depth without changing the product pixels.
    shadow_mask = resized_alpha.filter(ImageFilter.GaussianBlur(max(10, CANVAS_SIZE // 48)))
    shadow_mask = shadow_mask.point(lambda value: int(value * 0.2))
    shadow_layer = Image.new('RGBA', (CANVAS_SIZE, CANVAS_SIZE), (73, 53, 36, 0))
    shadow_full_mask = Image.new('L', (CANVAS_SIZE, CANVAS_SIZE), 0)
    shadow_full_mask.paste(shadow_mask, (center_x + 12, center_y + 20))
    shadow_layer.putalpha(shadow_full_mask)
    canvas = Image.alpha_composite(canvas.convert('RGBA'), shadow_layer).convert('RGB')
    canvas.paste(resized_rgb, (center_x, center_y), resized_alpha)
    return canvas


def _studio_background(width, height):
    """Create the warm beige wall and angled window light used in Syafra product photos."""
    top = (197, 171, 140)
    bottom = (229, 211, 185)
    gradient = Image.new('RGB', (1, height))
    gradient.putdata([
        tuple(round(start + (end - start) * y / max(1, height - 1)) for start, end in zip(top, bottom))
        for y in range(height)
    ])
    background = gradient.resize((width, height), Image.Resampling.BICUBIC).convert('RGBA')

    light = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(light)
    draw.ellipse(
        (-width // 2, -height // 3, width * 3 // 4, height * 3 // 4),
        fill=(255, 238, 198, 112),
    )
    light = light.filter(ImageFilter.GaussianBlur(max(32, width // 12)))
    background = Image.alpha_composite(background, light)

    window_shadow = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(window_shadow)
    shadow_draw.polygon(
        [
            (width * 18 // 100, -height // 10),
            (width * 25 // 100, -height // 10),
            (width * 66 // 100, height * 105 // 100),
            (width * 56 // 100, height * 105 // 100),
        ],
        fill=(88, 64, 43, 43),
    )
    shadow_draw.polygon(
        [
            (width * 56 // 100, -height // 10),
            (width * 62 // 100, -height // 10),
            (width * 104 // 100, height * 105 // 100),
            (width * 95 // 100, height * 105 // 100),
        ],
        fill=(88, 64, 43, 38),
    )
    shadow_draw.polygon(
        [
            (-width // 10, height * 30 // 100),
            (width * 75 // 100, -height // 10),
            (width * 78 // 100, height * 2 // 100),
            (-width // 10, height * 40 // 100),
        ],
        fill=(88, 64, 43, 32),
    )
    window_shadow = window_shadow.filter(ImageFilter.GaussianBlur(max(8, width // 180)))
    return Image.alpha_composite(background, window_shadow).convert('RGB')


def _price_font(size):
    """Choose a system font that includes the Indian rupee glyph when present."""
    candidates = [
        os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf'),
        r'C:\Windows\Fonts\arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
    ]
    for path in candidates:
        try:
            if os.path.isfile(path):
                return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_product_price_callout(image_bytes, price):
    """Return a product photo with an administrator-provided rupee price label."""
    try:
        amount = Decimal(str(price))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('A valid administrator-entered product price is required.') from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError('A valid administrator-entered product price is required.')

    image = Image.open(io.BytesIO(image_bytes))
    output_format = image.format if image.format in {'JPEG', 'PNG'} else 'JPEG'
    canvas = image.convert('RGB')
    draw = ImageDraw.Draw(canvas)

    formatted = f'{amount:,.2f}'.rstrip('0').rstrip('.')
    label = f'₹{formatted}/-'
    font = _price_font(max(42, CANVAS_SIZE // 18))
    try:
        text_width = draw.textbbox((0, 0), label, font=font)[2]
    except (UnicodeEncodeError, OSError):
        label = f'INR {formatted}/-'
        text_width = draw.textbbox((0, 0), label, font=font)[2]

    right = CANVAS_SIZE - CANVAS_SIZE // 14
    x = max(CANVAS_SIZE // 2, right - text_width)
    y = CANVAS_SIZE // 9
    draw.text((x + 4, y + 5), label, font=font, fill=(80, 61, 43))
    draw.text((x, y), label, font=font, fill=(255, 250, 241))

    # Fine hand-drawn arrow pointing from the price toward the product.
    arrow_start = (right - CANVAS_SIZE // 10, y + CANVAS_SIZE // 13)
    arrow_end = (right - CANVAS_SIZE // 4, y + CANVAS_SIZE // 4)
    curve = [
        arrow_start,
        (arrow_start[0] - CANVAS_SIZE // 24, arrow_start[1] + CANVAS_SIZE // 16),
        (arrow_end[0] + CANVAS_SIZE // 28, arrow_end[1] - CANVAS_SIZE // 20),
        arrow_end,
    ]
    draw.line(curve, fill=(255, 250, 241), width=max(5, CANVAS_SIZE // 180), joint='curve')
    tip = curve[-1]
    draw.line([tip, (tip[0] + CANVAS_SIZE // 45, tip[1] - CANVAS_SIZE // 90)], fill=(255, 250, 241), width=max(5, CANVAS_SIZE // 180))
    draw.line([tip, (tip[0] + CANVAS_SIZE // 55, tip[1] + CANVAS_SIZE // 60)], fill=(255, 250, 241), width=max(5, CANVAS_SIZE // 180))

    output = io.BytesIO()
    if output_format == 'JPEG':
        canvas.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    else:
        canvas.save(output, format='PNG', optimize=True, compress_level=PNG_COMPRESS)
    return output.getvalue()


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
