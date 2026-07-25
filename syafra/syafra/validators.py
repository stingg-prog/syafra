import os
from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.avif'}
ALLOWED_IMAGE_MIMES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'image/svg+xml', 'image/avif',
}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

DANGEROUS_URI_SCHEMES = {'javascript', 'data', 'vbscript'}
ALLOWED_URI_SCHEMES = {'http', 'https', 'mailto', 'tel', ''}


def validate_image_file(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Invalid file extension "{ext}". Allowed: {", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))}'
        )
    if hasattr(file_obj, 'content_type') and file_obj.content_type:
        if file_obj.content_type not in ALLOWED_IMAGE_MIMES:
            raise ValidationError(
                f'Invalid file type "{file_obj.content_type}". Allowed image types: {", ".join(sorted(ALLOWED_IMAGE_MIMES))}'
            )
    if file_obj.size > MAX_UPLOAD_SIZE:
        size_mb = file_obj.size / (1024 * 1024)
        raise ValidationError(f'File too large ({size_mb:.1f} MB). Maximum allowed: 5 MB.')


def validate_file_upload(file_obj):
    ext = os.path.splitext(file_obj.name)[1].lower()
    dangerous_exts = {'.exe', '.bat', '.cmd', '.sh', '.ps1', '.msi', '.com', '.scr', '.pif', '.vbs', '.js', '.jar', '.php', '.py', '.rb', '.pl'}
    if ext in dangerous_exts:
        raise ValidationError(f'File type "{ext}" is not allowed for upload.')
    if file_obj.size > MAX_UPLOAD_SIZE:
        size_mb = file_obj.size / (1024 * 1024)
        raise ValidationError(f'File too large ({size_mb:.1f} MB). Maximum allowed: 5 MB.')


def validate_safe_url(value):
    if not value:
        return
    value_lower = value.strip().lower()
    for scheme in DANGEROUS_URI_SCHEMES:
        if value_lower.startswith(f'{scheme}:'):
            raise ValidationError(f'URL scheme "{scheme}:" is not allowed.')
    if 'javascript:' in value_lower or 'data:' in value_lower or 'vbscript:' in value_lower:
        raise ValidationError('Dangerous URL scheme detected.')
