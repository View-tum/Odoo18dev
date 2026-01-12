from odoo import http
from odoo.http import request
import base64
import urllib.parse

class OiPdfViewerController(http.Controller):
    @http.route('/oi_pdf_viewer/preview/<int:res_id>', type='http', auth='user')
    def preview_pdf(self, res_id, **kw):
        # ตัวอย่าง: สมมติเป็น sale.order และ attachment ชื่อขึ้นต้นด้วย SaleOrder
        model = 'sale.order'
        record = request.env[model].browse(res_id)
        attachment = request.env['ir.attachment'].search([
            ('res_model', '=', model),
            ('res_id', '=', res_id),
            ('mimetype', '=', 'application/pdf'),
        ], limit=1, order='id desc')
        if not attachment:
            return request.not_found()
        # Determine records (support single res_id or multiple ids passed in query)
        ids_param = kw.get('ids') or kw.get('res_ids') or kw.get('active_ids')
        records = None
        if ids_param:
            # ids_param may be a comma-separated string, list, or similar
            try:
                if isinstance(ids_param, (list, tuple)):
                    ids_list = [int(x) for x in ids_param]
                else:
                    import re
                    ids_list = [int(x) for x in re.findall(r"\d+", str(ids_param))]
                records = request.env[model].browse(ids_list)
            except Exception:
                records = record
        else:
            records = record

        # Prefer the record's name for the filename; if multiple, join with &
        def _name_of(r):
            return (getattr(r, 'name', None) or getattr(r, 'display_name', None) or attachment.name or 'document')

        if hasattr(records, '__iter__') and len(records) > 1:
            base_names = [str(_name_of(r)) for r in records]
            filename_base = '&'.join(base_names)
        else:
            # single record
            single = records[0] if hasattr(records, '__iter__') else records
            filename_base = str(_name_of(single))

        filename = filename_base if filename_base.lower().endswith('.pdf') else (filename_base + '.pdf')
        # filename* provides a UTF-8 encoded filename for non-ASCII characters
        filename_star = urllib.parse.quote(filename, safe='')
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', "inline; filename=\"%s\"; filename*=UTF-8''%s" % (filename, filename_star))
        ]
        # Posting to chatter is handled centrally in the jasper report flow
        # (see `jasper_report_run.action_download`) to avoid duplicate messages.
        # attachment.datas is base64-encoded; decode it for the HTTP response
        data = base64.b64decode(attachment.datas or b'')
        return request.make_response(data, headers)
