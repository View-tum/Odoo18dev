from odoo import models, fields

class MailTemplate(models.Model):
    
    _inherit = 'mail.template'
    
    jasper_report_ids = fields.Many2many('jasper.report')
    
    def _generate_template(self, res_ids, render_fields, find_or_create_partners=False):
        render_results = super()._generate_template(res_ids, render_fields, find_or_create_partners = find_or_create_partners)

        if self.jasper_report_ids:
            for res_id in res_ids:
                values = render_results.setdefault(res_id, {})
                attachments = values.setdefault('attachments', [])
                for report in self.jasper_report_ids:
                    a = report.run_report([res_id])
                    params = a["params"]
                    report_run_id = self.env['jasper.report.run'].browse(params["id"])            
                    attachments.append((report_run_id.filename, report_run_id.datas))
        
        return render_results
    