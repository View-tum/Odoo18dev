# Contract Documents - Cron Job และ Email Testing Guide (Odoo 18)

## สรุปการเปลี่ยนแปลง

### 1. การปรับปรุง Cron Job สำหรับ Odoo 18
- **ไฟล์**: `data/contract_reminder_cron.xml`
- **เปลี่ยนแปลง**: 
  - ลบฟิลด์ที่ไม่รองรับใน Odoo 18: `numbercall`, `doall`, `weekday`, `nextcall`
  - ใช้การตรวจสอบวันจันทร์ในโค้ดแทน
  - Cron job จะทำงานทุกสัปดาห์ แต่จะส่งอีเมล์เฉพาะวันจันทร์เท่านั้น

### 2. การปรับปรุง Logic ในโมเดล
- **ไฟล์**: `models/contract_document.py`
- **เปลี่ยนแปลง**:
  - เมธอด `send_reminder()`: ตรวจสอบวันจันทร์ก่อนส่งอีเมล์
  - เพิ่มเมธอด `send_reminder_force()`: ส่งอีเมล์ทันทีโดยไม่รอวันจันทร์ (สำหรับทดสอบ)

### 3. การปรับปรุง Email Template
- **ไฟล์**: `data/email_template_contract_reminder.xml`
- **เปลี่ยนแปลง**:
  - เพิ่ม `email_to="${object.user_id.email}"` เพื่อส่งถึงผู้รับผิดชอบโดยตรง
  - เปลี่ยนเนื้อหาเป็นภาษาไทย
  - เพิ่มรายละเอียดสัญญามากขึ้น

### 4. การเพิ่ม Test Button และ Server Actions
- **ไฟล์**: `views/contract_document_views.xml`
  - เพิ่มปุ่ม "Test Email for This Contract" ในหน้าฟอร์มสัญญา
  
- **ไฟล์**: `data/server_action_preview.xml`
  - Server Action 1: "Send Contract Expiry Reminders" (ตามปกติ - เช็ควันจันทร์)
  - Server Action 2: "Force Send Contract Expiry Reminders" (บังคับส่ง - ไม่เช็ควัน)

## วิธีทดสอบระบบ

### 1. ทดสอบผ่าน Form View
1. เปิดหน้าสัญญา (Contract Document)
2. คลิกปุ่ม "Test Email for This Contract" (สีเหลือง)
3. ระบบจะส่งอีเมล์ทดสอบไปยังผู้รับผิดชอบของสัญญานั้น

### 2. ทดสอบผ่าน Server Action (แนะนำ)
1. ไปที่ Settings > Technical > Server Actions
2. หา "Force Send Contract Expiry Reminders (Ignore Monday Check)"
3. คลิก "Run" เพื่อส่งอีเมล์แจ้งเตือนทันทีโดยไม่รอวันจันทร์

### 3. ทดสอบ Cron Job
1. ไปที่ Settings > Technical > Scheduled Actions
2. หา "Contract Expiry Reminder - Every Monday"
3. คลิก "Run Manually" (จะทำงานเฉพาะวันจันทร์เท่านั้น)

### 4. การตั้งค่า Cron Job ให้ทำงานในเวลาที่ต้องการ
หลังจากติดตั้งโมดูลแล้ว:
1. ไปที่ Settings > Technical > Scheduled Actions
2. หา "Contract Expiry Reminder - Every Monday"
3. กำหนดเวลาที่ต้องการ (เช่น 9:00 น.)
4. Save

## การแก้ไขปัญหา Odoo 18

ปัญหาเดิม:
```
ValueError: Invalid field 'numbercall' on model 'ir.cron'
```

การแก้ไข:
- ลบฟิลด์ที่ไม่รองรับ: `numbercall`, `doall`, `weekday`, `nextcall`
- ใช้การตรวจสอบ `date.today().weekday() != 0` ในโค้ดแทน
- เพิ่มเมธอด `send_reminder_force()` สำหรับทดสอบ

## เงื่อนไขการส่งอีเมล์

ระบบจะส่งอีเมล์แจ้งเตือนเมื่อ:
- วันจันทร์เท่านั้น (สำหรับ cron job ปกติ)
- สัญญามี `date_end` ระหว่างวันนี้ถึง 90 วันข้างหน้า
- สัญญามีสถานะ `state = 'open'`
- สัญญามี `user_id` (ผู้รับผิดชอบ) และมีอีเมล์

## โครงสร้างอีเมล์ที่จะส่ง

อีเมล์จะประกอบด้วย:
- ชื่อสัญญา
- ชื่อลูกค้า  
- วันที่เริ่มต้นและสิ้นสุดสัญญา
- จำนวนวันที่เหลือ
- ชื่อผู้รับผิดชอบ
- ข้อความเป็นภาษาไทย

## การติดตาม Log

ระบบจะบันทึก log ใน:
1. **Chatter**: บันทึกในแต่ละสัญญาว่าส่งอีเมล์เมื่อใด
2. **Server Log**: บันทึกใน Odoo log file รวมถึงการข้ามการส่งเมื่อไม่ใช่วันจันทร์
3. **Partner**: บันทึกในหน้าลูกค้าเกี่ยวกับสัญญา