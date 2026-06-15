import io
import urllib.request
from PIL import Image, ImageDraw, ImageFont


def download_image(url: str) -> Image.Image:
    if not url:
        return Image.new("RGBA", (150, 150), (80, 80, 80, 255))
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGBA")
        return img
    except Exception:
        return Image.new("RGBA", (150, 150), (80, 80, 80, 255))


def round_crop(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([(0, 0), (size, size)], fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(img, (0, 0))
    result.putalpha(mask)
    return result


def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        if bold:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: float) -> list:
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        if dummy_draw.textlength(test, font=font) < max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_card(data: dict) -> bytes:
    PADDING = 40
    PFP_SIZE = 110
    GAP = 25

    W = 620

    bio = data.get("bio", "")
    bio_lines = wrap_text(bio, get_font(17), W - PADDING * 2 - PFP_SIZE - GAP - 20) if bio else []
    bio_height = len(bio_lines) * 28 if bio_lines else 0

    H = PADDING + PFP_SIZE + GAP + 80 + 30 + bio_height + 50 + PADDING

    BG_COLOR = (10, 10, 15, 255)
    CARD_BG = (22, 22, 30, 255)
    ACCENT = (255, 100, 100, 255)
    VERIFIED_BLUE = (30, 150, 255, 255)
    TEXT_WHITE = (255, 255, 255, 255)
    TEXT_GRAY = (160, 160, 175, 255)
    STATS_NUM = (255, 255, 255, 255)
    DIVIDER = (45, 45, 60, 255)

    img = Image.new("RGBA", (W, int(H)), BG_COLOR)
    draw = ImageDraw.Draw(img)

    radius = 35
    draw.rounded_rectangle([(20, 20), (W - 20, H - 20)], radius=radius, fill=CARD_BG)

    pfp_pos = (PADDING, PADDING)
    pfp = round_crop(download_image(data.get("profile_pic_url", "")), PFP_SIZE)
    img.paste(pfp, pfp_pos, pfp)

    text_x = pfp_pos[0] + PFP_SIZE + GAP

    y = PADDING + 5
    username = data.get("username", "unknown")
    username_font = get_font(30, bold=True)
    draw.text((text_x, y), f"@{username}", font=username_font, fill=TEXT_WHITE)

    if data.get("is_verified"):
        uname_w = draw.textlength(f"@{username}", font=username_font)
        draw.text((text_x + uname_w + 8, y + 2), "✓", font=get_font(22, bold=True), fill=VERIFIED_BLUE)

    y = PADDING + PFP_SIZE - 30
    full_name = data.get("full_name", "")
    if full_name:
        draw.text((text_x, y), full_name, font=get_font(18), fill=TEXT_GRAY)

    stats_y = PADDING + PFP_SIZE + GAP + 10
    followers = data.get("followers", 0)
    following = data.get("following", 0)
    posts = data.get("posts", 0)

    stat_label_font = get_font(13)
    stat_num_font = get_font(24, bold=True)

    stats = [
        ("Posts", format_count(posts)),
        ("Followers", format_count(followers)),
        ("Following", format_count(following))
    ]

    for i, (label, value) in enumerate(stats):
        x = text_x + i * 145
        draw.text((x, stats_y), label, font=stat_label_font, fill=TEXT_GRAY)
        draw.text((x, stats_y + 18), value, font=stat_num_font, fill=STATS_NUM)

    divider_y = stats_y + 55
    draw.line([(text_x, divider_y), (W - PADDING, divider_y)], fill=DIVIDER, width=1)

    if bio:
        bio_y = divider_y + 20
        for i, line in enumerate(bio_lines[:5]):
            draw.text((text_x, bio_y + i * 28), line, font=get_font(17), fill=TEXT_GRAY)

    external_url = data.get("external_url", "")
    if external_url:
        url_y = divider_y + 25 + bio_height + 15
        if url_y < H - PADDING - 30:
            draw.text((text_x, url_y), f"🔗 {external_url[:55]}", font=get_font(14), fill=ACCENT)

    if data.get("is_private"):
        lock_y = H - PADDING - 40
        draw.rounded_rectangle([(text_x, lock_y), (text_x + 160, lock_y + 36)], radius=10, fill=(50, 50, 65, 255))
        draw.text((text_x + 18, lock_y + 8), "🔒 Private Account", font=get_font(15, bold=True), fill=TEXT_GRAY)

    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()