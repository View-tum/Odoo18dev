from odoo import models, fields
import re
import logging

_logger = logging.getLogger(__name__)

class MailTemplate(models.Model):
    
    _inherit = 'mail.template'
    
    jasper_report_ids = fields.Many2many('jasper.report')
    
    def _generate_template(self, res_ids, render_fields, find_or_create_partners=False):
        render_results = super()._generate_template(res_ids, render_fields, find_or_create_partners=find_or_create_partners)

        if self.jasper_report_ids:
            for res_id in res_ids:
                values = render_results.setdefault(res_id, {})
                attachments = values.setdefault('attachments', [])
                for report in self.jasper_report_ids:
                    
                    a = report.run_report([res_id])
                    
                    if isinstance(a, dict):
                        report_id = None
                        
                        # แบบที่ 1: รองรับรูปแบบเก่าเผื่อไว้ (params)
                        if "params" in a and "id" in a["params"]:
                            report_id = a["params"]["id"]
                        
                        # แบบที่ 2: รองรับรูปแบบใหม่จาก Log ที่เห็น (ดึง ID จาก URL)
                        elif "url" in a:
                            # ค้นหาตัวเลขที่อยู่ระหว่าง /jasper.report.run/ และ /datas/
                            match = re.search(r'/jasper\.report\.run/(\d+)/', a["url"])
                            if match:
                                report_id = int(match.group(1))
                        
                        # ถ้าระบุ ID ของรายงานได้ ให้ทำการดึงไฟล์มาแนบ
                        if report_id:
                            report_run_id = self.env['jasper.report.run'].browse(report_id)
                            
                            if report_run_id.exists() and report_run_id.filename and report_run_id.datas:
                                attachments.append((report_run_id.filename, report_run_id.datas))
                                _logger.info(f"JASPER SUCCESS: Attached {report_run_id.filename}")
                            else:
                                _logger.warning("JASPER WARNING: Report run ID found, but no data/filename.")
                        else:
                            _logger.warning(f"JASPER WARNING: Could not find report ID in result: {a}")
        
        return render_results