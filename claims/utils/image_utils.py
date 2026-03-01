from __future__ import annotations
import os


CLAUDE_NATIVE_IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
}


def is_image(mime: str) -> bool:
    return (mime or "").lower().startswith("image/")


def needs_conversion(mime: str) -> bool:
    return is_image(mime) and mime.lower() not in CLAUDE_NATIVE_IMAGE_MIMES


def detect_actual_mime(path: str) -> str:
    """
    Detect the actual mime type from file content, not from browser-provided headers.
    Uses Pillow to identify the real format.
    """
    try:
        from PIL import Image
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass

        with Image.open(path) as img:
            fmt = (img.format or "").upper()
            mapping = {
                "JPEG": "image/jpeg",
                "JPG":  "image/jpeg",
                "PNG":  "image/png",
                "GIF":  "image/gif",
                "WEBP": "image/webp",
                "HEIF": "image/heif",
                "HEIC": "image/heic",
                "BMP":  "image/bmp",
                "TIFF": "image/tiff",
            }
            detected = mapping.get(fmt)
            if detected:
                print(f"[ImageUtils] Detected actual mime={detected} for path={path}")
                return detected
    except Exception as e:
        print(f"[ImageUtils] Could not detect mime from file content: {e}")

    # Fallback to magic bytes if Pillow fails
    try:
        with open(path, "rb") as f:
            header = f.read(12)
        if header[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        if header[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            return "image/webp"
        if b'ftyp' in header:
            return "image/heic"
    except Exception as e:
        print(f"[ImageUtils] Magic byte detection failed: {e}")

    return "application/octet-stream"


def convert_to_jpeg(src_path: str, dest_path: str) -> bool:
    """
    Convert any image format to JPEG.
    Returns True if successful.
    """
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        print(f"[ImageUtils] pillow_heif registered")
    except ImportError as e:
        print(f"[ImageUtils] pillow_heif not available: {e}")
    except Exception as e:
        print(f"[ImageUtils] pillow_heif register failed: {e}")

    try:
        from PIL import Image
        img = Image.open(src_path)
        img.convert("RGB").save(dest_path, format="JPEG", quality=90)
        print(f"[ImageUtils] Converted via Pillow: {src_path} → {dest_path}")
        return True
    except Exception as e:
        print(f"[ImageUtils] Pillow conversion failed: {e}")

    # ImageMagick fallback
    try:
        ret = os.system(f'convert "{src_path}" "{dest_path}" 2>/dev/null')
        if ret == 0 and os.path.exists(dest_path):
            print(f"[ImageUtils] Converted via ImageMagick: {src_path} → {dest_path}")
            return True
        print(f"[ImageUtils] ImageMagick failed with return code: {ret}")
    except Exception as e:
        print(f"[ImageUtils] ImageMagick attempt failed: {e}")

    return False


def prepare_image_for_upload(
    src_path: str,
    mime: str,
    tmp_dir: str,
    base_filename: str,
) -> tuple[str, str]:
    """
    1. Detect actual mime from file content (ignore browser-provided mime)
    2. Convert to JPEG if not natively supported by Claude
    3. Return (final_path, final_mime)
    """
    # Always detect from content — never trust browser mime
    actual_mime = detect_actual_mime(src_path)
    print(f"[ImageUtils] browser_mime={mime} actual_mime={actual_mime}")

    # If actual mime is already Claude-native, return as-is
    if actual_mime in CLAUDE_NATIVE_IMAGE_MIMES:
        return src_path, actual_mime

    # Otherwise convert to JPEG
    print(f"[ImageUtils] Converting actual_mime={actual_mime} to JPEG")
    jpeg_filename = f"{base_filename}_converted.jpg"
    jpeg_path     = os.path.join(tmp_dir, jpeg_filename)

    success = convert_to_jpeg(src_path, jpeg_path)

    if success and os.path.exists(jpeg_path):
        print(f"[ImageUtils] Conversion success → {jpeg_path}")
        return jpeg_path, "image/jpeg"

    # All conversions failed — still return actual detected mime
    # so at least the mime matches the real file content
    print(f"[ImageUtils] Conversion failed, returning actual mime: {actual_mime}")
    return src_path, actual_mime