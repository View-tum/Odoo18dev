from __future__ import annotations

import html
import re
from pathlib import Path


PACKAGE = Path(r"C:\365_project\TheCool18e\Dev\output\ams_customer_r001_compare\AMS_R001_COMPARE_PACKAGE")
SOURCE = PACKAGE / "07_PRESENT_ORDER_START_TO_END_TH.md"
TARGET = PACKAGE / "08_PRESENT_ORDER_START_TO_END_TH.html"


def convert(markdown: str) -> str:
    lines = markdown.splitlines()
    parts = [
        '<!doctype html><html><head><meta charset="utf-8"><title>AMS R001 Present Order</title>',
        "<style>"
        "body{font-family:Arial,'Noto Sans Thai',sans-serif;max-width:1180px;margin:32px;line-height:1.58;color:#111827}"
        "h1{color:#5B1747;font-size:30px}h2{margin-top:34px;border-bottom:2px solid #E5E7EB;padding-bottom:8px;color:#1F2937}"
        "h3{margin-top:26px;color:#374151}.file{background:#F3F4F6;border:1px solid #E5E7EB;border-radius:6px;padding:2px 6px}"
        "li{margin:5px 0}p{margin:8px 0}.callout{background:#FFF7ED;border-left:5px solid #F97316;padding:12px 14px;margin:16px 0}"
        "code{background:#F3F4F6;padding:2px 5px;border-radius:4px}"
        "</style></head><body>",
    ]
    in_ul = False
    for raw in lines:
        line = raw.rstrip()
        if not line:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            continue
        if line.startswith("# "):
            parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            parts.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{html.escape(line[2:])}</li>")
        elif re.match(r"^\d+\. ", line):
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{html.escape(re.sub(r'^\\d+\\. ', '', line))}</li>")
        elif line.startswith("`") and line.endswith("`"):
            parts.append(f'<p><span class="file">{html.escape(line.strip("`"))}</span></p>')
        else:
            escaped = html.escape(line)
            escaped = re.sub(r"`([^`]+)`", r'<code>\1</code>', escaped)
            if line.endswith(":"):
                parts.append(f'<p class="callout"><strong>{escaped}</strong></p>')
            else:
                parts.append(f"<p>{escaped}</p>")
    if in_ul:
        parts.append("</ul>")
    parts.append("</body></html>")
    return "\n".join(parts)


def main() -> None:
    TARGET.write_text(convert(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(str(TARGET))


if __name__ == "__main__":
    main()
