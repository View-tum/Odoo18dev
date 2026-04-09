from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from inventory_manual_annotations import ANNOTATIONS


BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "inventory_manual_assets"
OUT_DIR = BASE_DIR / "inventory_manual_assets_annotated"


def load_font(size: int):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT = load_font(22)


def draw_badge(draw: ImageDraw.ImageDraw, x: int, y: int, label: str):
    badge_w, badge_h = 28, 28
    draw.rounded_rectangle((x, y, x + badge_w, y + badge_h), radius=6, fill=(220, 20, 60), outline=(255, 255, 255), width=2)
    bbox = draw.textbbox((0, 0), label, font=FONT)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = x + (badge_w - text_w) / 2
    ty = y + (badge_h - text_h) / 2 - 1
    draw.text((tx, ty), label, font=FONT, fill=(255, 255, 255))


def annotate_image(image_name: str, items: list[dict]):
    src = SRC_DIR / image_name
    if not src.exists():
        raise FileNotFoundError(f"Missing source image: {src}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    for item in items:
        x1, y1, x2, y2 = item["box"]
        draw.rectangle((x1, y1, x2, y2), outline=(220, 20, 60, 255), width=4)
        draw.rectangle((x1, y1, x2, y2), outline=(255, 255, 255, 180), width=1)
        # Keep the callout number aligned with the annotated area instead of floating above nearby UI.
        badge_x = max(0, x1 - 30)
        badge_y = max(0, y1 + 2)
        draw_badge(draw, badge_x, badge_y, item["id"])

    out = Image.alpha_composite(img, overlay).convert("RGB")
    out.save(OUT_DIR / image_name, quality=95)


def build():
    for image_name, items in ANNOTATIONS.items():
        annotate_image(image_name, items)
    return OUT_DIR


if __name__ == "__main__":
    print(build())
