import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image, UnidentifiedImageError

FORMAT_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def validate_image_file(file):
    """Valida el tipo REAL de la imagen (no la extensión) y su tamaño."""
    if file.size > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError(f"La imagen supera {settings.MAX_IMAGE_UPLOAD_BYTES // (1024 * 1024)} MB.")
    try:
        file.seek(0)
        with Image.open(file) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("El archivo no es una imagen válida.")
    finally:
        file.seek(0)
    if fmt not in settings.ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Formato no permitido. Usa JPG, PNG o WEBP.")


@deconstructible
class uuid_upload_path:
    """upload_to que renombra el archivo con un UUID conservando una extensión segura."""

    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        ext = Path(filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"
        return f"{self.folder}/{uuid.uuid4().hex}{ext}"
