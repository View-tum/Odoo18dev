from pathlib import Path
from shutil import copy2, copytree, rmtree, make_archive

from openpyxl import load_workbook
from openpyxl.styles import Font


ROOT = Path(r"C:\365_project\TheCool18e\Dev\output\AMS_PRESENT_CUSTOMER_TH")
WORK_DIR = ROOT / "AMS_Clickable_AMS_Source_Mapping"
CUSTOMER_DIR = ROOT / "AMS_Clickable_AMS_Source_Mapping_CUSTOMER_PACKAGE"
WORKBOOK = WORK_DIR / "AWS_Present_All_Clickable_AMS_Source_Mapping.xlsx"
DOWNLOAD_COPY = Path(r"C:\Users\tumsu\Downloads\AWS_Present_All_Clickable_AMS_Source_Mapping.xlsx")
ZIP_PATH = ROOT / "AMS_Clickable_AMS_Source_Mapping_CUSTOMER_PACKAGE.zip"


def set_link(cell, text, target):
    cell.value = text
    cell.hyperlink = target
    cell.font = Font(color="0563C1", underline="single")


def r001_target(row):
    return f"ams_source_files/02_Requirement_on_New_System_R001.xlsx#Requirement!A{row}"


def workflow_target():
    return "ams_source_files/01_AMS_Workflow_ERP.xlsx#'Follow on Requirement'!A1"


def blueprint_target():
    return "ams_source_files/03_TFI_business_blueprint_22042024.jpg"


def source_row_number(value):
    if not value:
        return None
    text = str(value)
    if "A" not in text:
        return None
    try:
        return int(text.rsplit("A", 1)[1])
    except ValueError:
        return None


wb = load_workbook(WORKBOOK)

pain = wb["Pain Point Mapping"]
for row in range(9, 21):
    source_row = source_row_number(pain[f"O{row}"].value)
    if source_row:
        set_link(pain[f"L{row}"], f"เปิด R001 แถว {source_row}", r001_target(source_row))
    set_link(pain[f"M{row}"], "เปิด AMS Workflow", workflow_target())
    set_link(pain[f"N{row}"], "เปิด Blueprint", blueprint_target())

refs = wb["05 Reference Files"]
set_link(refs["F6"], "เปิด AMS Workflow", workflow_target())
set_link(refs["F7"], "เปิด R001 Requirement", r001_target(6))
set_link(refs["F8"], "เปิด Blueprint", blueprint_target())

req = wb["06 R001 Requirement Links"]
for row in range(6, 50):
    source_row = source_row_number(req[f"N{row}"].value)
    if not source_row:
        continue
    set_link(req[f"O{row}"], f"เปิด R001 แถว {source_row}", r001_target(source_row))
    set_link(req[f"P{row}"], "เปิด AMS Workflow", workflow_target())
    set_link(req[f"Q{row}"], "เปิด Blueprint", blueprint_target())

wb.save(WORKBOOK)
copy2(WORKBOOK, DOWNLOAD_COPY)

if CUSTOMER_DIR.exists():
    rmtree(CUSTOMER_DIR)
CUSTOMER_DIR.mkdir(parents=True, exist_ok=True)
copy2(WORKBOOK, CUSTOMER_DIR / WORKBOOK.name)
copytree(WORK_DIR / "ams_source_files", CUSTOMER_DIR / "ams_source_files")

if ZIP_PATH.exists():
    ZIP_PATH.unlink()
make_archive(str(ZIP_PATH.with_suffix("")), "zip", CUSTOMER_DIR.parent, CUSTOMER_DIR.name)

print(WORKBOOK)
print(DOWNLOAD_COPY)
print(CUSTOMER_DIR)
print(ZIP_PATH)
