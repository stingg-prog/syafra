"""
Hook into Django model save() to normalize product images on upload.

Simple pipeline: remove background → trim whitespace → fit to canvas → center.

Duplicate Detection:
  - Computes SHA-256 hash of uploaded image bytes
  - Compares against stored hash and normalization version
  - Skips normalization if hash matches AND version matches
"""

import logging
import threading

from .image_normalizer import (
    normalize_product_image,
    compute_image_hash,
    should_normalize,
    preserve_original,
    NORMALIZATION_VERSION,
)

logger = logging.getLogger(__name__)

# Thread-local guard to prevent double normalization during save()
_normalizing = threading.local()


def _is_normalizing(instance):
    key = f"{instance.__class__.__name__}_{instance.pk}"
    return getattr(_normalizing, key, False)


def _set_normalizing(instance, value=True):
    key = f"{instance.__class__.__name__}_{instance.pk}"
    setattr(_normalizing, key, value)


def normalize_before_save(instance, field_name='image'):
    """
    If the given ImageField has a new upload, normalize it in-place.
    """
    if _is_normalizing(instance):
        return

    field = getattr(instance, field_name, None)
    if field is None:
        return

    if not field or not hasattr(field, 'file') or field.file is None:
        return

    upload = field.file
    if not hasattr(upload, 'read'):
        return

    # ── Check if file is closed ────────────────────────────────────────
    try:
        upload.tell()
    except ValueError:
        # File is closed — skip normalization
        return

    # ── Detect new upload vs existing file ─────────────────────────────
    # If the file is closed or has no name, it's an existing file being
    # re-saved (not a new upload). Skip normalization.
    from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
    is_new_upload = isinstance(upload, (InMemoryUploadedFile, TemporaryUploadedFile))

    if not is_new_upload:
        # Not a new upload — skip normalization
        return

    # ── Duplicate Detection ────────────────────────────────────────────
    stored_hash = getattr(instance, 'image_hash', '') or ''
    stored_version = getattr(instance, 'image_norm_version', 0) or 0

    try:
        if not should_normalize(upload, stored_hash, stored_version):
            logger.debug("Image already normalized (v%d) — skipping", stored_version)
            return
    except Exception as exc:
        logger.warning("Hash check failed, proceeding: %s", exc)

    # ── Preserve Original ──────────────────────────────────────────────
    preserve_original(field)

    # ── Normalize ──────────────────────────────────────────────────────
    _set_normalizing(instance, True)

    try:
        original_pos = upload.tell()
        upload.seek(0)

        current_hash = compute_image_hash(upload)

        upload.seek(0)
        normalized = normalize_product_image(upload)

        field.save(field.name, normalized, save=False)

        instance.image_hash = current_hash
        instance.image_norm_version = NORMALIZATION_VERSION

        logger.info("Normalized %s %s (v%d)",
                     instance.__class__.__name__, instance.pk,
                     NORMALIZATION_VERSION)
    except Exception as exc:
        logger.error("Normalization failed for %s %s: %s",
                     instance.__class__.__name__, instance.pk, exc)
        try:
            upload.seek(original_pos)
        except Exception:
            pass
    finally:
        _set_normalizing(instance, False)
