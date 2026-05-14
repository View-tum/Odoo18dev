from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\365_project\TheCool18e\Dev")
IMAGE_DIR = ROOT / "manual" / "Accouting_Manual" / "generated_20260408" / "images"


FONT_REGULAR = Path(r"C:\Windows\Fonts\tahoma.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\tahomabd.ttf")


EXPLANATIONS: dict[str, list[str]] = {
    "journal_group_payment_real_annotated.png": [
        "Dr = เงินรับหรือบัญชีพักรับชำระ เพิ่มขึ้นจากการรับเงินของกลุ่มลูกค้า",
        "Cr = ลูกหนี้การค้า ลดลงตามใบแจ้งหนี้ของลูกค้าในกลุ่ม",
    ],
    "journal_cheque_out_confirmed_real_annotated.png": [
        "Dr = เจ้าหนี้การค้า ลดลงเพราะถือว่าจ่ายหนี้แล้ว",
        "Cr = บัญชีพักเช็คจ่าย เพิ่มขึ้นเพราะเช็คยังไม่ผ่านธนาคาร",
    ],
    "journal_cheque_out_paid_real_annotated.png": [
        "Dr = บัญชีพักเช็คจ่าย ลดลงเมื่อเช็คผ่านธนาคาร",
        "Cr = บัญชีธนาคาร ลดลงเป็นเงินออกจริง",
    ],
    "journal_cheque_in_confirmed_real_annotated.png": [
        "Dr = บัญชีพักเช็ครับ เพิ่มขึ้นเพราะรับเช็คไว้ก่อน",
        "Cr = ลูกหนี้การค้า ลดลงตามยอดที่ลูกค้าชำระ",
    ],
    "journal_cheque_in_paid_real_annotated.png": [
        "Dr = บัญชีธนาคาร เพิ่มขึ้นเมื่อเช็คผ่านธนาคารแล้ว",
        "Cr = บัญชีพักเช็ครับ ลดลงเพราะย้ายยอดเข้าธนาคารจริง",
    ],
    "journal_cheque_void_reverse_real_annotated.png": [
        "Dr = บัญชีที่เคยถูกเครดิตในรายการเดิม ถูกกลับทางเข้ามาใหม่",
        "Cr = บัญชีที่เคยถูกเดบิตในรายการเดิม ถูกกลับทางออกเพื่อยกเลิกรายการ",
    ],
    "journal_asset_depreciation_real_annotated.png": [
        "Dr = ค่าเสื่อมราคา เป็นค่าใช้จ่ายของงวด",
        "Cr = ค่าเสื่อมราคาสะสม เพิ่มขึ้นเพื่อลดมูลค่าทรัพย์สินทางบัญชี",
    ],
    "journal_asset_sale_real_annotated.png": [
        "Dr = ลูกหนี้หรือเงินรับ และค่าเสื่อมสะสมที่ต้องปิดออก",
        "Cr = บัญชีทรัพย์สินเดิม และบัญชีกำไรจากการขายถ้ามีผลกำไร",
    ],
    "journal_asset_disposal_real_annotated.png": [
        "Dr = ค่าเสื่อมสะสมและบัญชีขาดทุนจากการตัดจำหน่ายถ้ามี",
        "Cr = บัญชีทรัพย์สินเดิมที่ต้องปิดออกจากระบบ",
    ],
    "journal_mfg_finished_real_annotated.png": [
        "Dr = สินค้าสำเร็จรูป เพิ่มเข้าคลังหลังผลิตเสร็จ",
        "Cr = งานระหว่างทำ ลดลงเพราะต้นทุนถูกย้ายมาเป็น FG แล้ว",
    ],
    "journal_mfg_raw_fg02001_real_annotated.png": [
        "Dr = งานระหว่างทำ เพิ่มขึ้นเพราะรับต้นทุนวัตถุดิบเข้าไลน์ผลิต",
        "Cr = วัตถุดิบหรือกึ่งสำเร็จรูป ลดลงเพราะถูกเบิกออกจากคลัง",
    ],
    "journal_mfg_raw_packaging_real_annotated.png": [
        "Dr = งานระหว่างทำ เพิ่มขึ้นจากต้นทุนบรรจุภัณฑ์ที่นำไปใช้",
        "Cr = วัตถุดิบบรรจุภัณฑ์ ลดลงตามจำนวนที่เบิกจริง",
    ],
    "journal_general_manual_annotated.png": [
        "Dr = ฝั่งซ้ายคือบัญชีที่รับมูลค่าเข้า",
        "Cr = ฝั่งขวาคือบัญชีที่ปล่อยมูลค่าออก",
    ],
    "journal_incoming_manual_annotated.png": [
        "Dr = เงินรับหรือบัญชีพักรับชำระ เพิ่มขึ้น",
        "Cr = ลูกหนี้การค้า ลดลงตามยอดที่รับชำระ",
    ],
    "journal_outgoing_manual_annotated.png": [
        "Dr = เจ้าหนี้การค้า ลดลงตามยอดที่จ่าย",
        "Cr = เงินฝากธนาคารหรือบัญชีพักจ่าย ลดลงตามเงินที่ออก",
    ],
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_REGULAR
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def source_image_for(annotated_path: Path) -> Path:
    if annotated_path.name.endswith("_annotated.png"):
        candidate = annotated_path.with_name(annotated_path.name.replace("_annotated.png", ".png"))
        if candidate.exists():
            return candidate
    return annotated_path


def annotate_image(source_path: Path, target_path: Path, lines: list[str]) -> None:
    image = Image.open(source_path).convert("RGBA")
    width, height = image.size
    header_font = load_font(max(22, width // 38), bold=True)
    body_font = load_font(max(18, width // 48))
    draw = ImageDraw.Draw(image)

    wrapped: list[tuple[str, ImageFont.FreeTypeFont]] = [("อ่านภาพ Journal นี้อย่างไร", header_font)]
    for line in lines:
        wrapped.extend((part, body_font) for part in wrap_text(draw, line, body_font, width - 120))

    line_heights = [draw.textbbox((0, 0), txt, font=fnt)[3] + 8 for txt, fnt in wrapped]
    footer_height = sum(line_heights) + 48

    new_img = Image.new("RGBA", (width, height + footer_height), (255, 255, 255, 255))
    new_img.paste(image, (0, 0))

    overlay = Image.new("RGBA", (width, footer_height), (18, 54, 91, 235))
    new_img.alpha_composite(overlay, (0, height))
    draw = ImageDraw.Draw(new_img)

    y = height + 18
    for idx, (txt, font) in enumerate(wrapped):
        fill = (255, 233, 127, 255) if idx == 0 else (255, 255, 255, 255)
        draw.text((40, y), txt, font=font, fill=fill)
        y += line_heights[idx]

    new_img.convert("RGB").save(target_path)


def main() -> None:
    updated = 0
    for filename, lines in EXPLANATIONS.items():
        target_path = IMAGE_DIR / filename
        source_path = source_image_for(target_path)
        if not source_path.exists():
            continue
        annotate_image(source_path, target_path, lines)
        updated += 1
    print(f"annotated {updated} journal images")


if __name__ == "__main__":
    main()
