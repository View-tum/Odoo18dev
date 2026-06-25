import io
import xlsxwriter
from datetime import datetime


class AccountExpenseTransactionXlsx:
    def generate_excel(self, report_data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        self._write_sheet(workbook, report_data)
        workbook.close()
        output.seek(0)
        return output.read()

    def _write_sheet(self, workbook, report_data):
        # สไตล์การจัดฟอร์แมตใน Excel
        base_style = {"font_name": "Angsana New", "font_size": 16}
        header_style = workbook.add_format({**base_style, "bold": True})
        date_style = workbook.add_format(
            {**base_style, "num_format": "dd/mm/yyyy", "align": "left"}
        )
        amount_style = workbook.add_format({**base_style, "num_format": "#,##0.00"})
        normal_style = workbook.add_format(base_style)

        header_bottom_style = workbook.add_format(
            {**base_style, "bold": True, "bottom": 1}
        )
        total_style = workbook.add_format(
            {**base_style, "bold": True, "top": 1, "bottom": 2}
        )
        total_amount_style = workbook.add_format(
            {
                **base_style,
                "bold": True,
                "top": 1,
                "bottom": 2,
                "num_format": "#,##0.00",
            }
        )

        now = datetime.now()

        for product_group in report_data:
            p_code = product_group.get("product_code", "")
            p_name = product_group.get("product_name", "")
            expense_data = product_group.get("expense_data", [])

            # ตั้งชื่อชีตจาก รหัส + ชื่อสินค้า (Excel จำกัดความยาวชื่อชีตไม่เกิน 31 ตัวอักษร)
            sheet_name = f"[{p_code}] {p_name}" if p_code else p_name
            sheet_name = (
                sheet_name[:31].replace("[", "").replace("]", "").strip()
            )  # ปรับแต่งอักขระให้ Excel ยอมรับง่ายขึ้น
            if not sheet_name:
                sheet_name = "Expense Report"

            # สร้าง Sheet ใหม่ให้กับ Product ตัวนี้
            worksheet = workbook.add_worksheet(sheet_name)

            # ปรับขนาดคอลัมน์ให้เหมาะสม (A-H)
            worksheet.set_column("A:A", 20)  # Vendor Bill / (Blank)
            worksheet.set_column("B:B", 32)  # Vendor Name / Transaction date
            worksheet.set_column("C:C", 20)  # Label / Voucher
            worksheet.set_column("D:D", 25)  # Start Date
            worksheet.set_column("E:E", 20)  # End Date
            worksheet.set_column("F:F", 16)  # Status / Description
            worksheet.set_column("G:G", 12)  # Acquisition / Transaction type
            worksheet.set_column("H:H", 20)  # Balance / Amount

            worksheet.write("A1", "Expense transactions", header_style)
            product_title = expense_data[0].get("product", "") if expense_data else ""
            worksheet.write("B1", f"Product: {product_title}", header_style)
            worksheet.write("H1", f"Date: {now.strftime('%d/%m/%Y')}", normal_style)
            worksheet.write("A2", "GOLD MINTS PRODUCTS CO., LTD.", header_style)
            worksheet.write("H2", f"Time: {now.strftime('%H:%M:%S')}", normal_style)

            row = 3
            for expense in expense_data:
                # --- ส่วนที่ 1: ข้อมูลบิลหลัก (Original Bill) ---
                transactions = expense.get("transactions", [])
                sum_transactions = sum(t.get("amount", 0) for t in transactions)
                headers_4 = [
                    "Vendor Bill",
                    "Vendor Name",
                    "Label",
                    "Start Date",
                    "End Date",
                    "Status",
                    "Acquisition",
                    "Balance",
                ]
                for col, text in enumerate(headers_4):
                    worksheet.write(row, col, text, header_bottom_style)
                row += 1

                worksheet.write(row, 0, expense.get("vendor_bill", ""), normal_style)
                worksheet.write(row, 1, expense.get("vendor_name", ""), normal_style)
                worksheet.write(row, 2, expense.get("label", ""), normal_style)
                worksheet.write(row, 3, expense.get("start_date", ""), date_style)
                worksheet.write(row, 4, expense.get("end_date", ""), date_style)
                worksheet.write(row, 5, expense.get("status", ""), normal_style)
                worksheet.write(row, 6, expense.get("acquisition", 0), amount_style)
                worksheet.write(row, 7, sum_transactions, amount_style)
                row += 2

                # --- ส่วนที่ 2: รายการบิลตัดจำหน่ายรายเดือน (Deferred Transactions) ---
                headers_6 = [
                    "",
                    "Transaction date",
                    "Voucher",
                    "Description",
                    "Transaction type",
                    "Amount",
                    "Currency",
                ]
                for col, text in enumerate(headers_6):
                    if text:
                        worksheet.write(row, col, text, header_bottom_style)
                row += 1

                for line in transactions:
                    worksheet.write(row, 1, line.get("date", ""), date_style)
                    worksheet.write(row, 2, line.get("voucher", ""), normal_style)
                    worksheet.write(row, 3, line.get("description", ""), normal_style)
                    worksheet.write(row, 4, line.get("type", ""), normal_style)
                    worksheet.write(row, 5, line.get("amount", 0), amount_style)
                    worksheet.write(row, 6, line.get("currency", ""), normal_style)
                    row += 1

                # ใส่เส้นขีดรวมเงินคู่ตามมาตรฐานบัญชี
                worksheet.write(row, 1, "Total", total_style)
                for c in range(2, 5):
                    worksheet.write(row, c, "", total_style)
                worksheet.write(row, 5, sum_transactions, total_amount_style)
                worksheet.write(row, 6, "", total_style)

                row += 3  # เว้นช่องว่างระหว่างก้อนบิลหลักใบถัดไป
