from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def get_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def annotate(meta_path: Path) -> Path:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    image_path = Path(meta["screenshot"])
    image = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(image)
    font = get_font(18)

    for idx, box in enumerate(meta.get("boxes", []), start=1):
        x = int(box["x"])
        y = int(box["y"])
        w = int(box["width"])
        h = int(box["height"])
        label = box.get("label") or str(idx)

        draw.rectangle((x, y, x + w, y + h), outline=(220, 38, 38, 255), width=4)
        badge_w = 28 + max(0, len(label) - 1) * 8
        badge_h = 28
        badge_x = x
        badge_y = max(0, y - badge_h - 4)
        draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
            radius=6,
            fill=(220, 38, 38, 255),
        )
        draw.text((badge_x + 8, badge_y + 5), label, fill=(255, 255, 255, 255), font=font)

    out_path = image_path.with_name(image_path.stem + "_annotated.png")
    image.save(out_path)
    return out_path


def main() -> None:
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python annotate_capture.py <meta.json>")
    out = annotate(Path(sys.argv[1]))
    print(out)


if __name__ == "__main__":
    main()
