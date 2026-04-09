# 📌 00. ภาพรวมการไหลเวียนแบบเส้นตรง (Linear Flow)

นี่คือขั้นตอนการทำงานตั้งแต่ "ต้นน้ำ (ขาย)" ไปจนถึง "ปลายน้ำ (บัญชีเงินเข้า)" แบบเข้าใจง่ายที่สุด

---

## 🟢 ขั้นตอนการทำงานจริง (Happy Path)

| ลำดับ | กิจกรรมที่เกิดขึ้น | Module / หน้าจอที่ใช้ | ผู้รับผิดชอบหลัก |
| :--- | :--- | :--- | :--- |
| **1** | **รับคำสั่งซื้อ** <br> 🔹 ดึงรายการสั่งซื้อเข้าสู่ระบบ <br> 🔹 ตรวจเช็คยอดค้างพาร์ตเนอร์ | 📑 **Sales (SO)** <br> 🧩 `sale_order_import_goldmints` <br> 🧩 `partner_credit_limit_sale_block` | ฝ่ายขาย (Sales) |
| **2** | **กดปุ่มรันจัดสรร** <br> 🔹 วางแผนจำนวนผลิตและยอดที่ต้องซื้อ | 📅 **MPS Planning** <br> 🧩 `mrp_mps_mo_tracking` | ฝ่ายวางแผน (Planner) |
| **3** | **จัดซื้อวัตถุดิบ** <br> 🔹 ส่งขออนุมัติจัดซื้อถ้าของขาด <br> 🔹 แปลงเป็นใบสั่งซื้อ PO | 🛒 **Purchase (PR/PO)** <br> 🧩 `oi_workflow_purchase_request` | ฝ่ายจัดซื้อ (Procurement) |
| **4** | **รับของเข้าคลัง** <br> 🔹 คีย์รับของเข้า Main Location <br> 🔹 ย้ายของป้อนจุดผลิต | 📦 **Inventory (Receipt)** <br> 🧩 `nano_transfer_product_lot` | ฝ่ายคลังสินค้า (Stock) |
| **5** | **ผลิตต่อเนื่อง** <br> 🔹 กด Start/Done ทยอยจบยอดยอด <br> 🔹 สลัดเคลมวัสดุที่เสีย Auto | ⚙️ **Manufacturing (MO)** <br> 🧩 `mrp_parallel_console` <br> 🧩 `mrp_scrap_auto_replenish` | พนักงานระดับหน้างาน (Operator) |
| **6** | **จัดส่งลูกค้า** <br> 🔹 ขับรถส่งตามเส้นทางและบีบยอดออก | 🚚 **Inventory (Delivery)** <br> 🧩 `delivery_routes_management` | ฝ่ายจัดส่ง (Logistics) |
| **7** | **เปิดบิลและรับเงิน** <br> 🔹 รวมบิลจัดส่งทำดิวเดียว <br> 🔹 เก็บเช็ค Clearing ยอดบวกลบ | 🧾 **Accounting (Invoice/PDC)** <br> 🧩 `account_billing_create` <br> 🧩 `sh_pdc` | ฝ่ายบัญชี (Accounting) |

---

## 📊 แผนภาพเส้นตรง (Linear Diagram)

```mermaid
flowchart LR
    Start([เริ่ม]) --> SO[1. เปิดใบสั่งขาย <br> Check Limit]
    SO --> MPS[2. วางแผนจัดสรร <br> MPS Plan]
    MPS --> PO[3. สั่งซื้อวัสดุขาด <br> PR -> PO]
    PO --> Warehouse[4. รับของเข้าคลัง <br> ย้ายส่งเบิกผลิต]
    Warehouse --> Produce[5. ผลิตหน้างาน <br> Parallel Console]
    Produce --> Delivery[6. จัดส่งสินค้า <br> ตามรูทรถ]
    Delivery --> Account[7. วางบิล / รับเช็ค <br> Billing & PDC]
    Account --> End([ปิดจบงานขาย])
```

---

## 📊 แผนภาพมุมมองบนลงล่าง (Top-Down Flow)

![Overall Top-Down Flow](./images/04_Overall_Flow_TopDown.png)

---
💡 *ไฟล์ถัดๆ ไปในโฟลเดอร์นี้จะอธิบาย "แต่ละ Module อย่างละเอียด" ครับ*
