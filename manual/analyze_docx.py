import docx

def get_docx_text(path):
    doc = docx.Document(path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# Example doc
example_path = r"c:\365_project\TheCool18e\Dev\manual\Accouting_Manual\เอกสารคู่มือการวิเคราะห์และออกแบบระบบ Gold Mints (Accounting).docx"
try:
    example_text = get_docx_text(example_path)
    with open(r"c:\365_project\TheCool18e\Dev\manual\example_text.txt", "w", encoding="utf-8") as f:
        f.write(example_text[:5000]) # Just first 5000 chars for style check
except Exception as e:
    print(f"Error reading example: {e}")

# Target doc
target_path = r"c:\365_project\TheCool18e\Dev\manual\Accouting_Manual\generated_20260408\docx\6_Fixed_Asset_Improved.docx"
try:
    target_text = get_docx_text(target_path)
    with open(r"c:\365_project\TheCool18e\Dev\manual\target_text.txt", "w", encoding="utf-8") as f:
        f.write(target_text)
except Exception as e:
    print(f"Error reading target: {e}")
