'''
Created on Jun 8, 2020

@author: Zuhair Hammadi
'''
from odoo import models, fields
from odoo.exceptions import UserError
import requests
import base64
from odoo.tools.pdf import merge_pdf
from urllib.parse import quote
import zipfile
from .. import EXPORT_FORMAT

import logging
import io
import os
_logger = logging.getLogger(__name__)


class JasperReportRun(models.TransientModel):
    _name = 'jasper.report.run'
    _description = 'Jasper Report Run'

    report_id = fields.Many2one('jasper.report', required=True)
    format = fields.Selection(EXPORT_FORMAT, required=True, default='pdf')

    ignore_pagination = fields.Boolean()
    one_page_per_sheet = fields.Boolean()

    datas = fields.Binary(attachment=False, copy=False)
    filename = fields.Char()
    mimetype = fields.Char()

    preview = fields.Boolean()

    def action_download(self):
        if len(self) == 1:
            # For single result: open PDF/HTML inline in browser (regardless of preview flag)
            if self.format in ('pdf', 'html') or self.preview:
                # Stream the file via /web/content to force inline preview in browser
                # Use dotted model name (required by /web/content route)
                model = self._name  # e.g. 'jasper.report.run'
                # Sanitize filename: remove path separators and URL-encode fully (including '/')
                raw_filename = self.filename or (
                    f"{self.report_id.name}.{self.format if self.format else 'pdf'}"
                )
                safe_filename = raw_filename.replace(
                    '/', '-').replace('\\', '-')
                filename = quote(safe_filename, safe='')
                try:
                    get_param = self.env['ir.config_parameter'].sudo(
                    ).get_param
                    post_val = get_param('jasper_report.post_chatter')
                    norm = str(post_val).strip().lower() if post_val is not None else None
                    should_post = (post_val is None) or (norm in ('1', 'true', 'yes', 'y', 't', 'on'))
                    if should_post:
                        model_name = self.report_id.model_id.model if self.report_id.model_id else None
                        ids_src = self._context.get('docid') or self._context.get(
                            'docids') or self._context.get('active_ids')
                        if ids_src and model_name:
                            try:
                                if isinstance(ids_src, (list, tuple)):
                                    ids_list = [int(x) for x in ids_src]
                                else:
                                    ids_list = [int(x) for x in str(
                                        ids_src).split(',') if x.strip()]
                                target_recs = self.env[model_name].browse(
                                    ids_list)
                                user = self.env.user
                                partner_id = user.partner_id.id if user and user.partner_id else None
                                try:
                                    model_label = self.env[model_name]._description or model_name
                                except Exception:
                                    model_label = model_name
                                report_label = self.report_id.name or 'เอกสาร'
                                body = "เอกสาร %s ใน%s ถูกพิมพ์โดย: %s" % (
                                    report_label, model_label, (user.name or ('user:%s' % user.id)))
                                for rec in target_recs:
                                    try:
                                        if partner_id:
                                            rec.sudo().message_post(body=body, author_id=partner_id, message_type='comment')
                                        else:
                                            rec.sudo().message_post(body=body, message_type='comment')
                                    except Exception:
                                        continue
                            except Exception:
                                pass
                except Exception:
                    pass

                return {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': '/web/content/%s/%s/%s/%s?download=false' % (model, self.id, 'datas', filename),
                }

            return {
                'type': 'ir.actions.client',
                'tag': 'file_download',
                'params': {
                        'model': self._name,
                        'field': 'datas',
                        'id': self.id,
                        'filename': self.filename,
                        'filename_field': 'filename',
                        'download': True
                }
            }

        if set(self.mapped('mimetype')) == {'application/pdf'}:
            pdf_data = []
            for record in self:
                data = base64.decodebytes(record.datas)
                pdf_data.append(data)
            data = merge_pdf(pdf_data)
            datas = base64.encodebytes(data)
            return self[0].copy({'datas': datas}).action_download()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
            filename, extension = os.path.splitext(self[0].filename)
            no = 0
            for record in self:
                no += 1
                data = base64.decodebytes(record.datas)
                zip_file.writestr("%s%s%s" % (filename, no, extension), data)

        datas = base64.encodebytes(zip_buffer.getvalue())
        return self[0].copy({'datas': datas, 'filename': self[0].filename + ".zip", 'mimetype': 'application/zip'}).action_download()

    def run_report(self, values=None):
        if self.report_id.multi:
            records = self.browse()
            for docid in self._context.get('docids'):
                record = self.copy()
                record.with_context(docid=docid)._run_report(
                    values=values, return_action=False)
                records += record
            return records.action_download()

        return self._run_report(values=values)

    def _run_report(self, values=None, return_action=True):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        url = "%(server_url)s/rest_v2/reports%(report_path)s.%(format)s" % {
            'server_url': get_param('jasper_report.url'),
            'report_path': self.report_id.report_path,
            'format': self.format
        }
        params = dict(self._context)
        if values:
            params.update(values)
        params.update({
            'ignorePagination': self.ignore_pagination,
            'onePagePerSheet': self.one_page_per_sheet
        })

        for name in ['docids', 'active_ids']:
            if isinstance(params.get(name), list):
                params[name] = ','.join(map(str, params[name]))

        res = requests.get(url, params=params, auth=(get_param(
            'jasper_report.user'), get_param('jasper_report.password')), timeout=30)

        # --- Custom: set filename to record.name (เลขที่เอกสาร) ---
        filename = None
        # Try to get the model and docids from context
        model_name = self.report_id.model_id.model if self.report_id.model_id else None
        docids = params.get('docids') or params.get('active_ids')
        if docids and model_name:
            # docids may be comma-separated string
            try:
                ids = [int(x) for x in str(docids).split(',') if x.strip()]
                records = self.env[model_name].browse(ids)
                if len(records) == 1:
                    filename = records[0].name if hasattr(
                        records[0], 'name') else None
                elif len(records) > 1:
                    names = [r.name for r in records if hasattr(
                        r, 'name') and r.name]
                    if names:
                        filename = '&'.join(names)
            except Exception:
                pass
        if not filename:
            filename = self.report_id.name
        filename = f"{filename}.{self.format}"
        # --- End custom ---

        if res.status_code == 200:
            mimetype = res.headers['content-type']
            self.write({
                'datas': base64.encodebytes(res.content),
                'filename': filename,
                'mimetype': mimetype
            })
            return self.action_download() if return_action else self

        status = requests.status_codes._codes[res.status_code][0]
        _logger.warning(res.content)
        raise UserError(status)
