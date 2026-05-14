import fitz  # PyMuPDF
import json

def extract_blue_info(pdf_path):
    doc = fitz.open(pdf_path)
    extracted_data = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. Extract text with color
        dict_page = page.get_text("dict")
        for block in dict_page.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    color = span.get("color")
                    text = span.get("text").strip()
                    if not text:
                        continue
                        
                    # Convert color to RGB
                    r = (color >> 16) & 0xFF
                    g = (color >> 8) & 0xFF
                    b = color & 0xFF
                    
                    # Blue check: b is significant and higher than r and g
                    if b > 150 and b > r and b > g:
                        extracted_data.append({
                            "type": "blue_text",
                            "page": page_num + 1,
                            "text": text,
                            "color": f"#{r:02x}{g:02x}{b:02x}"
                        })
        
        # 2. Extract annotations (for blue strike-throughs)
        for annot in page.annots():
            if annot.type[0] == 11:  # StrikeOut
                color = annot.colors.get("stroke")
                if color:
                    r, g, b = [int(c * 255) for c in color]
                    if b > 150 and b > r and b > g:
                        # Get text under annotation
                        rect = annot.rect
                        text = page.get_text("text", clip=rect).strip()
                        extracted_data.append({
                            "type": "blue_strikeout",
                            "page": page_num + 1,
                            "text": text,
                            "color": f"#{r:02x}{g:02x}{b:02x}"
                        })
    
    return extracted_data

path = r"c:\365_project\TheCool18e\Dev\manual\Accouting_Manual\generated_20260408\docx\6_Fixed_Asset_Improved.pdf"
results = extract_blue_info(path)

output_file = r"c:\365_project\TheCool18e\Dev\manual\blue_text_results.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Results saved to {output_file}")
