import logging
from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)


def crop_profile_header(
    img: Image.Image,
    ref_width: int = 1280,
    ref_height: int = 720,
    left: int = 490,
    top: int = 65,
    right: int = 960,
    bottom: int = 270,
) -> Image.Image:
    """
    Crop to show: profile pic + username + posts/followers/following stats + first line of bio.
    Everything visible without scrolling — no nav bar, no footer.
    """
    w, h = img.size

    if w < left or h < top:
        logger.warning(
            f"Image too small ({w}x{h}) for crop region, returning original"
        )
        return img

    scale_x = w / ref_width
    scale_y = h / ref_height

    crop_left = int(left * scale_x)
    crop_top = int(top * scale_y)
    crop_right = int(right * scale_x)
    crop_bottom = int(bottom * scale_y)

    crop_right = min(crop_right, w)
    crop_bottom = min(crop_bottom, h)

    return img.crop((crop_left, crop_top, crop_right, crop_bottom))


def process_screenshot(
    image_bytes: bytes,
    ref_width: int = 1280,
    ref_height: int = 720,
    left: int = 490,
    top: int = 65,
    right: int = 960,
    bottom: int = 270,
) -> bytes:
    """
    Load PNG bytes, validate, crop to profile header, return cropped PNG bytes.
    """
    img = Image.open(BytesIO(image_bytes))

    if img.format != "PNG":
        logger.warning(f"Expected PNG, got {img.format}, converting")
        img = img.convert("RGBA")

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    cropped = crop_profile_header(
        img,
        ref_width=ref_width,
        ref_height=ref_height,
        left=left,
        top=top,
        right=right,
        bottom=bottom,
    )

    output = BytesIO()
    if cropped.mode == "RGBA":
        cropped.save(output, format="PNG")
    else:
        cropped.convert("RGB").save(output, format="PNG")

    return output.getvalue()
