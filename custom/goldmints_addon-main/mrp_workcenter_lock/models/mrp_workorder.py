from odoo import api, models, _
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _check_single_job_per_workcenter_before_start(self):
        """ตรวจว่าห้ามมีงานซ้อนใน Work Center เดียวกัน

        - ในการกดครั้งเดียว (recordset self) ถ้าเลือกหลาย WO ที่อยู่ Work Center เดียวกัน
          จะไม่อนุญาต (กันกรณี multi-select แล้ว start ทีเดียวหลายงานบนเครื่องเดียว)
        - ตรวจในฐานข้อมูลว่า Work Center นี้มี WO ตัวอื่นที่ state = 'progress' อยู่แล้วหรือยัง
        """

        if not self:
            return

        workorder_model = self.env["mrp.workorder"]

        # 1) กันกรณี self มีหลาย WO บน Work Center เดียวกันในครั้งเดียว
        workorders_by_wc = {}
        for wo in self:
            if not wo.workcenter_id:
                # ถ้า WO ยังไม่ได้เลือก Work Center ข้ามไป
                continue
            workorders_by_wc.setdefault(wo.workcenter_id.id, workorder_model.browse())
            workorders_by_wc[wo.workcenter_id.id] |= wo

        for wc_id, wos in workorders_by_wc.items():
            if len(wos) > 1:
                wc = wos[0].workcenter_id
                raise UserError(_(
                    "ไม่สามารถเริ่มงานหลายงานบน Work Center เดียวกันพร้อมกันได้\n\n"
                    "Work Center: %s\n"
                    "กรุณาเลือกเริ่มทีละ Work Order ต่อ Work Center."
                ) % (wc.display_name,))

            # 2) กันกรณีมี WO ตัวอื่นใน Work Center เดียวกันที่กำลังทำงานอยู่แล้ว
            sample_wo = wos[0]
            domain = [
                ("id", "not in", self.ids),
                ("workcenter_id", "=", wc_id),
                ("state", "=", "progress"),
            ]
            if sample_wo.company_id:
                domain.append(("company_id", "=", sample_wo.company_id.id))

            overlapping = workorder_model.search(domain, limit=1)

            if overlapping:
                raise UserError(_(
                    "ไม่สามารถเริ่มงานได้ เนื่องจาก Work Center นี้กำลังทำงานอยู่แล้ว\n\n"
                    "Work Center: %s\n"
                    "Work Order ที่กำลังทำงาน: %s\n\n"
                    "กรุณาจบหรือหยุดงานเดิมก่อนเริ่มงานใหม่บนเครื่องนี้."
                ) % (overlapping.workcenter_id.display_name, overlapping.display_name))

    # ใน Odoo รุ่นก่อน ๆ ใช้ชื่อ method ว่า button_start
    # ถ้า Odoo 18 ยังเรียก method นี้อยู่ เราจะดักไว้ที่นี่
    def button_start(self, *args, **kwargs):
        # Accept and forward arbitrary args/kwargs because core may pass
        # parameters like `raise_on_invalid_state`.
        self._check_single_job_per_workcenter_before_start()
        return super().button_start(*args, **kwargs)

    # เผื่อกรณี Odoo 18 ใช้ชื่อ method action_start หรือ method อื่นในการ start งาน
    # ถ้ามี method นี้ใน core การ override จะทำให้ logic เดียวกันถูกใช้ด้วย
    def action_start(self, *args, **kwargs):
        # Support being called as a recordset method; accept and forward args/kwargs.
        # This keeps behavior consistent whether core defines action_start as
        # model or record method across Odoo versions.
        self._check_single_job_per_workcenter_before_start()
        return super().action_start(*args, **kwargs)
