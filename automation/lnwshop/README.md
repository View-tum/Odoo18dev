# LnwShop Excel Automation

ชุดนี้ใช้ไฟล์ `output/spreadsheet/IMOU_LnwShop_AI_ready_watermarked.xlsx` เป็นฐานข้อมูลสินค้า แล้วเปิด Microsoft Edge ด้วยโปรไฟล์แยกสำหรับ automation

## ใช้งานแบบง่ายที่สุด

รัน PowerShell ตัวเดียวนี้ แล้วเลือกเมนู:

```powershell
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1
```

คำสั่งตรงแบบไม่เข้าเมนู:

```powershell
# เตรียม Excel + รูปลายน้ำ + หมวดหมู่
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action Prepare

# ทดสอบอ่านหมวดหมู่ row 2
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action DryCategory -Row 2

# เติมหมวดหมู่ row 2
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action CategoryOne -Row 2

# เติมหมวดหมู่ row 2-11 ต่อเนื่อง
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action CategoryBatch -StartRow 2 -EndRow 11

# เติมสินค้า row 2
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action ProductOne -Row 2
```

ค่าเริ่มต้นเป็น manual-save: script จะกรอกข้อมูลแล้วให้คุณตรวจ/บันทึกเองก่อนกด Enter กลับมาเพื่อไปต่อ

## เตรียมรูปใส่ลายน้ำและหมวดหมู่

รันคำสั่งนี้ทุกครั้งหลังแก้ไฟล์สินค้า/รูปสินค้า:

```powershell
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action Prepare
```

ผลลัพธ์:

- `output/spreadsheet/IMOU_LnwShop_AI_ready_watermarked.xlsx`
- `output/spreadsheet/IMOU_LnwShop_categories.xlsx`
- `output/spreadsheet/imou_product_images_watermarked/`

ไฟล์ลายน้ำที่ใช้:

```text
automation/lnwshop/สำเนาของ watermark (15).png
```

## ขั้นตอนใช้งานครั้งแรกสำหรับสินค้า

1. เปิดหน้าต่าง automation และ login LnwShop ในหน้าต่างนี้ โดย script จะเปิดหน้า `https://a.lnwstore.com/onetechsolution/inventory/`

```powershell
python automation/lnwshop/lnwshop_fill.py inspect
```

2. ใน Edge ที่เปิดขึ้นมา ให้ login ถ้ายังไม่ได้ login
3. กลับมาที่ terminal แล้วกด Enter; script จะพยายามกดปุ่ม `+ สินค้า` ให้เอง และจะไม่กด `+ หมวดหมู่`
4. ถ้า script กดปุ่มไม่ได้ ให้กด `+ สินค้า` เองใน Edge แล้วกลับมากด Enter เพื่อให้ script เก็บข้อมูลช่องฟอร์ม
5. ทดสอบกรอกสินค้า 1 รายการแบบยังไม่กดบันทึก

```powershell
python automation/lnwshop/lnwshop_fill.py fill --row 2
```

## โหมดสำคัญ

```powershell
# ดูข้อมูลแถวสินค้าจาก Excel โดยไม่เปิด browser
python automation/lnwshop/lnwshop_fill.py dry-run --row 2

# กรอกสินค้าแถว Excel row 2 และหยุดให้ตรวจ
python automation/lnwshop/lnwshop_fill.py fill --row 2

# ถ้าคุณกด + สินค้า เองอยู่แล้ว ให้ปิด auto-click
python automation/lnwshop/lnwshop_fill.py fill --row 2 --no-click-add-product

# หลังทดสอบ manual ผ่านแล้วเท่านั้น ค่อยให้ script กดบันทึก
python automation/lnwshop/lnwshop_fill.py fill --row 2 --auto-save
```

## ขั้นตอนสำหรับหมวดหมู่

ควรเพิ่มหมวดหมู่ก่อนลงสินค้า เพราะสินค้าต้องเลือกหมวดหมู่ที่มีอยู่แล้ว

โครงสร้างหมวดหมู่ตอนนี้คือ:

```text
IMOU
  กล้องวงจรปิด
    กล้อง IP Camera
    เครื่องบันทึกภาพ NVR
  อุปกรณ์เสริมกล้องวงจรปิด
    เมมโมรี่การ์ด Micro SD
    ขายึดกล้อง
    แผงโซลาร์เซลล์
  สมาร์ทโฮม
    อุปกรณ์ดูแลสัตว์เลี้ยง
```

หมายเหตุ: หน้าเพิ่มหมวดหมู่จริงของ LnwShop ไม่มีช่อง `ประเภทสินค้า (Product Type)`;
script จะบังคับเลือก Product Type ตอนลงสินค้าเป็น:

```text
สินค้าอุตสาหกรรม
อุปกรณ์ใช้ในโรงงานอุตสาหกรรม
```

```powershell
# ตรวจข้อมูลหมวดหมู่แถวแรก: IMOU
python automation/lnwshop/lnwshop_fill.py dry-run-category --row 2

# เปิดหน้า inventory แล้วให้ script กด + หมวดหมู่ เพื่อ inspect ฟอร์ม
python automation/lnwshop/lnwshop_fill.py inspect-category

# กรอกหมวดหมู่แถว Excel row 2 และหยุดให้ตรวจ
python automation/lnwshop/lnwshop_fill.py fill-category --row 2

# ถ้าคุณกด + หมวดหมู่ เองอยู่แล้ว
python automation/lnwshop/lnwshop_fill.py fill-category --row 2 --no-click-add-category

# หลังทดสอบ manual ผ่านแล้วเท่านั้น ค่อยให้ script กดบันทึก
python automation/lnwshop/lnwshop_fill.py fill-category --row 2 --auto-save
```

ถ้าทดสอบผ่านแล้วและต้องการให้ batch บันทึกต่อเนื่องโดยไม่หยุดทีละแถว ให้ใช้ `-AutoSave -NoPause` กับ `lnwshop.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action CategoryBatch -StartRow 2 -EndRow 11 -AutoSave -NoPause
powershell -ExecutionPolicy Bypass -File automation/lnwshop/lnwshop.ps1 -Action ProductBatch -StartRow 2 -EndRow 46 -AutoSave -NoPause
```

ไฟล์หมวดหมู่คือ:

```text
output/spreadsheet/IMOU_LnwShop_categories.xlsx
```

## เปิด URL อื่นเอง ถ้าต้องการ override ค่าเริ่มต้น
```powershell
python automation/lnwshop/lnwshop_fill.py fill --row 2 --url "https://..."
```

## หมายเหตุ

- ค่าเริ่มต้นไม่กด Save ให้เอง เพื่อกันพลาดจากราคา 0 บาท
- Session login จะอยู่ใน `automation/lnwshop/edge-profile`
- ถ้า LnwShop เปลี่ยน layout หรือชื่อช่องไม่ตรง ให้รัน `inspect` แล้วส่งไฟล์ `automation/lnwshop/last_inspect.json` กลับมาให้ปรับ selector
