from odoo import models, fields, api, _
from odoo.tools.misc import format_date as odoo_format_date
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta, timezone as dt_timezone
import pytz
import logging

_logger = logging.getLogger(__name__)


class ContractDocument(models.Model):
    _name = 'contract.document'
    _description = 'Contract Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Contract Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Responsible', required=False, tracking=True, default=lambda self: self.env.user)
    manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    attachment = fields.Binary(string='Contract Document (PDF)', attachment=True)
    attachment_filename = fields.Char(string='Filename')
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True, string='Status')
    remaining_days = fields.Integer(string='Days Remaining', compute='_compute_remaining_days', store=True)
    total_duration_days = fields.Integer(string='Total Duration (days)', compute='_compute_total_duration_days', store=True)
    reminder_days = fields.Selection(
        selection=[('7', '7'), ('30', '30'), ('60', '60'), ('90', '90')],
        string='Reminder Before (days)',
        default='30',
        required=True,
        help='Send reminder when remaining days equals the selected value.'
    )

    @api.depends('date_end')
    def _compute_remaining_days(self):
        for rec in self:
            if rec.date_end:
                rec.remaining_days = (rec.date_end - date.today()).days
                if rec.remaining_days <= 0 and rec.state == 'open':
                    rec.state = 'expired'
                    rec.message_post(
                        body=_("Contract automatically expired - remaining days: %s") % rec.remaining_days,
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
            else:
                rec.remaining_days = 0

    @api.depends('date_start', 'date_end')
    def _compute_total_duration_days(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                days = (rec.date_end - rec.date_start).days + 1
                rec.total_duration_days = max(0, days)
            else:
                rec.total_duration_days = 0

    def _compute_recipient_email(self):
        self.ensure_one()
        recipients = []
        u_email = (self.user_id.sudo().email or '').strip()
        if u_email:
            recipients.append(u_email)
        if self.manager_id:
            m_email = (self.manager_id.sudo().email or '').strip()
            if not m_email:
                m_email = (self.manager_id.sudo().partner_id and self.manager_id.sudo().partner_id.email or '').strip()
            if m_email and m_email not in recipients:
                recipients.append(m_email)
        return ", ".join(recipients)

    def _get_sender_email(self):
        sender = (getattr(self.env.user, 'email_formatted', None) or self.env.user.email or '').strip()
        if not sender:
            company = self.env.company
            comp_email = (company.email or '').strip()
            if comp_email:
                sender = "%s <%s>" % (company.name, comp_email)
        return sender

    def _ensure_outgoing_server(self):
        if not self.env['ir.mail_server'].sudo().search_count([('active', '=', True)]):
            raise UserError(_("No outgoing mail server configured. Please configure SMTP in Settings → Technical → Outgoing Mail Servers."))

    def _get_cron_timezone(self):
        tz = (self.env['ir.config_parameter'].sudo().get_param('contract_documents.cron_tz') or '').strip()
        if not tz:
            tz = (self.env.user.tz or '').strip()
        return tz or 'UTC'

    def _get_reminder_template(self):
        """Locate the reminder email template.

        Try the canonical XML id first, then fall back to a template search by name.
        This prevents module installation failures when the XML external id is missing
        or was renamed by an update step.
        """
        template = self.env.ref('contract_documents.email_template_contract_reminder', raise_if_not_found=False)
        if template:
            return template
        # Fallback: search by technical name
        template = self.env['mail.template'].search([('name', '=', 'Contract Expiry Reminder')], limit=1)
        return template

    def _is_monday_now(self):
        return True

    def _compose_email_content(self):
        self.ensure_one()
        lang = self.env.user.lang or 'en_US'
        date_start = odoo_format_date(self.env, self.date_start, lang_code=lang) if self.date_start else 'ไม่ระบุ'
        date_end = odoo_format_date(self.env, self.date_end, lang_code=lang) if self.date_end else 'ไม่ระบุ'
        
        state_display = dict(self._fields['state'].selection).get(self.state, self.state)
        
        subject = f"แจ้งเตือน: สัญญา {self.name} จะหมดอายุเร็วๆ นี้ ({self.remaining_days} วัน)"
        body_html = f"""
            <p>เรียน คุณ {(self.user_id.name or '').strip()},</p>
            <p>
                ขอแจ้งให้ทราบว่าสัญญา <strong>{(self.name or '').strip()}</strong>
                ของลูกค้า <strong>{(self.partner_id.name or '').strip()}</strong>
                จะหมดอายุใน <strong>{self.remaining_days} วัน</strong>
            </p>

            <p><strong>รายละเอียดสัญญา:</strong></p>
            <ul>
                <li>ชื่อสัญญา: {((self.name or '').strip())}</li>
                <li>ลูกค้า: {((self.partner_id.name or '').strip())}</li>
                <li>สถานะ: <strong>{state_display}</strong></li>
                <li>วันที่เริ่มต้น: {date_start}</li>
                <li>วันที่สิ้นสุด: {date_end}</li>
                <li>จำนวนวันที่เหลือ: {self.remaining_days} วัน</li>
                <li>ผู้รับผิดชอบ: {((self.user_id.name or '').strip())}</li>
                {f'<li>ผู้จัดการ: {((self.manager_id.name or "").strip())}</li>' if self.manager_id else ''}
            </ul>

            <p>กรุณาดำเนินการต่ออายุ/ยกเลิกหากไม่ต้องการต่อสัญญา กับผู้ให้บริการ และเพิ่มหรือแก้ไขสัญญาในระบบ</p>
            <p>ขอบคุณค่ะ<br/>{(self.env.user.name or '').strip()}</p>
        """.strip()
        return subject, body_html

    def send_reminder(self):
        template = self._get_reminder_template()
        if not template:
            _logger.error("Email template contract_documents.email_template_contract_reminder not found")
            return

        contracts = self.search([
            ('date_end', '!=', False),
            ('state', '=', 'open'),
        ])

        today = date.today()
        _logger.info("Starting daily contract reminder check. Found %d open contracts", len(contracts))

        for rec in contracts:
            try:
                rec._compute_remaining_days()
                
                if rec.state != 'open':
                    _logger.info("Contract '%s' (ID %s) was auto-expired, skipping reminder", rec.name, rec.id)
                    continue
                
                rec._ensure_outgoing_server()
                if not rec.date_end or not rec.reminder_days:
                    continue
                remaining = (rec.date_end - today).days
                try:
                    threshold = int(rec.reminder_days)
                except Exception:
                    continue
                if remaining != threshold:
                    continue

                email_to = rec._compute_recipient_email()
                if not email_to:
                    raise UserError(_("No recipient email found on responsible user or manager."))
                email_from = rec._get_sender_email()
                if not email_from:
                    raise UserError(_("No sender email configured for current user or company."))
                subject, body_html = rec._compose_email_content()
                mail_id = template.send_mail(
                    rec.id,
                    force_send=True,
                    email_values={
                        'email_to': email_to,
                        'email_from': email_from,
                        'subject': subject,
                        'body_html': body_html,
                    },
                )
                mm = self.env['mail.mail'].sudo().browse(mail_id) if mail_id else self.env['mail.mail']
                if mm and mm.exists() and mm.state in ('exception', 'cancel'):
                    raise UserError(mm.failure_reason or _("Email sending failed."))
                rec.message_post(
                    body=_("Contract reminder email sent at %s days before expiry. Mail ID: %s") % (threshold, mail_id or 'n/a'),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                _logger.info("Sent contract reminder for '%s' (ID %s) at %s days before expiry. mail_id=%s", rec.name, rec.id, threshold, mail_id)
            except Exception as e:  
                _logger.exception("Failed to send reminder for contract '%s' (ID %s): %s", rec.name, rec.id, e)
                rec.message_post(
                    body=_("Failed to send contract reminder: %s") % (str(e)),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
        
        _logger.info("Completed daily contract reminder processing")

    def send_reminder_force(self):
        template = self._get_reminder_template()
        if not template:
            _logger.error("Email template contract_documents.email_template_contract_reminder not found")
            return

        contracts = self.search([
            ('date_end', '!=', False),
            ('state', '=', 'open'),
        ])

        today = date.today()
        _logger.info("Force sending contract reminders. Found %d open contracts", len(contracts))

        for rec in contracts:
            try:
                rec._compute_remaining_days()
                
                if rec.state != 'open':
                    _logger.info("Contract '%s' (ID %s) was auto-expired, skipping reminder", rec.name, rec.id)
                    continue
                
                rec._ensure_outgoing_server()
                if not rec.date_end or not rec.reminder_days:
                    continue
                remaining = (rec.date_end - today).days
                try:
                    threshold = int(rec.reminder_days)
                except Exception:
                    continue
                if remaining != threshold:
                    continue
                email_to = rec._compute_recipient_email()
                if not email_to:
                    raise UserError(_("No recipient email found on responsible user or manager."))
                email_from = rec._get_sender_email()
                if not email_from:
                    raise UserError(_("No sender email configured for current user or company."))
                subject, body_html = rec._compose_email_content()
                mail_id = template.send_mail(
                    rec.id,
                    force_send=True,
                    email_values={
                        'email_to': email_to,
                        'email_from': email_from,
                        'subject': subject,
                        'body_html': body_html,
                    },
                )
                mm = self.env['mail.mail'].sudo().browse(mail_id) if mail_id else self.env['mail.mail']
                if mm and mm.exists() and mm.state in ('exception', 'cancel'):
                    raise UserError(mm.failure_reason or _("Email sending failed."))
                rec.message_post(
                    body=_("Manual contract reminder email sent at %s days before expiry. Mail ID: %s") % (threshold, mail_id or 'n/a'),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                _logger.info("Sent manual contract reminder for '%s' (ID %s) at %s days before expiry. mail_id=%s", rec.name, rec.id, threshold, mail_id)
            except Exception as e:  
                _logger.exception("Failed to send reminder for contract '%s' (ID %s): %s", rec.name, rec.id, e)
                rec.message_post(
                    body=_("Failed to send contract reminder: %s") % (str(e)),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                
        _logger.info("Completed manual contract reminder processing")

    def send_test_reminder(self):
        recs = self.exists()
        if not recs:
            raise UserError(_("This contract record no longer exists. Please refresh the page."))
        self = recs.ensure_one()
        
        self._compute_remaining_days()
        
        if self.state != 'open':
            raise UserError(_("Test reminder can only be sent for contracts in OPEN state. Current state: %s") % dict(self._fields['state'].selection).get(self.state))
        
        template = self._get_reminder_template()
        if not template:
            raise UserError(_("Email template not found. Please contact your administrator."))
        
        self._ensure_outgoing_server()

        email_to = self._compute_recipient_email()
        if not email_to:
            raise UserError(_("No recipient email found on responsible user or manager."))
        email_from = self._get_sender_email()
        if not email_from:
            raise UserError(_("No sender email configured for current user or company."))
        
        try:
            subject, body_html = self._compose_email_content()
            mail_id = template.send_mail(
                self.id,
                force_send=True,
                email_values={
                    'email_to': email_to,
                    'email_from': email_from,
                    'subject': subject,
                    'body_html': body_html,
                },
            )
            mm = self.env['mail.mail'].sudo().browse(mail_id) if mail_id else self.env['mail.mail']
            if mm and mm.exists() and mm.state in ('exception', 'cancel'):
                raise UserError(mm.failure_reason or _("Email sending failed."))
            self.message_post(
                body=_("Test reminder email sent to %s. Mail ID: %s") % (email_to, mail_id or 'n/a'),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            _logger.info("Sent test reminder for contract '%s' (ID %s) to %s. mail_id=%s", 
                        self.name, self.id, email_to, mail_id)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success!'),
                    'message': _('Test reminder email sent to %s') % email_to,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            error_msg = _("Failed to send test reminder: %s") % str(e)
            self.message_post(
                body=error_msg,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            _logger.exception("Failed to send test reminder for contract '%s' (ID %s): %s", self.name, self.id, e)
            raise UserError(error_msg)

    def action_preview_attachment(self):
        self.ensure_one()
        if not self.attachment:
            raise UserError(_("No attachment available to preview for this contract."))

        return {
            'type': 'ir.actions.act_url',
            'url': (
                '/web/content/?model=contract.document&id=%s&field=attachment&filename_field=attachment_filename&download=false'
                % self.id
            ),
            'target': 'new',
        }

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        try:
            rec.message_post(body=("Created"), message_type='comment', subtype_xmlid='mail.mt_note')
            if rec.partner_id:
                rec.partner_id.message_post(
                    body=("Contract '%s' created.") % (rec.name),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
        except Exception:
            _logger.exception("Failed to post creation log for Contract ID %s", rec.id)
        _logger.info("Contract '%s' (ID %s) created", rec.name, rec.id)
        return rec

    def write(self, vals):
        keys = list(vals.keys()) if vals else []
        capture_fields = set(keys)
        if 'attachment' in capture_fields:
            capture_fields.add('attachment_filename')
        old_map = {rec.id: {k: rec[k] for k in capture_fields} for rec in self}
        res = super().write(vals)
        if not keys:
            return res
        for rec in self:
            try:
                parts = []
                has_attachment = 'attachment' in keys
                for k in keys:
                    field = rec._fields.get(k)
                    if not field:
                        continue
                    if field.type == 'binary':
                        if k == 'attachment':
                            old_fname = old_map.get(rec.id, {}).get('attachment_filename')
                            new_fname = rec.attachment_filename
                            att_label = (rec._fields['attachment'].string or 'Attachment')
                            if ' (' in att_label:
                                att_label = att_label.split(' (', 1)[0]
                            parts.append("%s: %s → %s" % (att_label, old_fname or "—", new_fname or "—"))
                        continue
                    if k == 'attachment_filename' and has_attachment:
                        continue
                    label = field.string or k
                    old = old_map.get(rec.id, {}).get(k)
                    new = rec[k]
                    def fmt(val):
                        if val is False or val is None:
                            return "—"
                        if field.type == 'many2one':
                            return val.display_name if val else "—"
                        if field.type == 'selection':
                            sel = dict(field.selection)
                            return sel.get(val, val)
                        s = str(val)
                        return (s[:60] + '…') if len(s) > 60 else s
                    old_s, new_s = fmt(old), fmt(new)
                    if old_s == new_s:
                        continue
                    parts.append("%s: %s → %s" % (label, old_s, new_s))
                if rec.partner_id and parts:
                    body = ("Contract '%s' updated %s") % (rec.name, "; ".join(parts))
                    rec.partner_id.message_post(
                        body=body,
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
            except Exception:
                _logger.exception("Failed to compose update log for Contract ID %s", rec.id)
        return res

    def unlink(self):
        for rec in self:
            try:
                if rec.partner_id:
                    rec.partner_id.message_post(
                        body=("Contract '%s' deleted.") % (rec.name),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
            except Exception:
                _logger.exception("Failed to post deletion log for Contract ID %s", rec.id)
        return super().unlink()

    def action_confirm(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'open'
                rec.message_post(body=_('Contract confirmed and activated.'))
            else:
                raise UserError(_('Only draft contracts can be confirmed.'))

    def action_cancel(self):
        for rec in self:
            if rec.state in ('draft', 'open'):
                rec.state = 'cancel'
                rec.message_post(body=_('Contract cancelled.'))
            else:
                raise UserError(_('Only draft or open contracts can be cancelled.'))

    def action_expire(self):
        for rec in self:
            if rec.state == 'open':
                rec.state = 'expired'
                rec.message_post(body=_('Contract manually expired.'))
            else:
                raise UserError(_('Only open contracts can be expired.'))

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state in ('open', 'expired', 'cancel'):
                rec.state = 'draft'
                rec.message_post(body=_('Contract reset to draft.'))
            else:
                raise UserError(_('Contract is already in draft state.'))

    def auto_expire_contracts(self):
        expired_count = 0
        open_contracts = self.search([
            ('state', '=', 'open'),
            ('date_end', '!=', False),
        ])
        
        today = date.today()
        _logger.info("Checking %d open contracts for auto-expiration", len(open_contracts))
        
        for contract in open_contracts:
            try:
                remaining_days = (contract.date_end - today).days
                if remaining_days <= 0:
                    contract.state = 'expired'
                    contract.message_post(
                        body=_("Contract automatically expired - remaining days: %s") % remaining_days,
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
                    expired_count += 1
                    _logger.info("Auto-expired contract '%s' (ID %s) - remaining days: %s", 
                               contract.name, contract.id, remaining_days)
            except Exception as e:
                _logger.exception("Failed to auto-expire contract '%s' (ID %s): %s", 
                                contract.name, contract.id, e)
        
        _logger.info("Auto-expiration completed. %d contracts were expired.", expired_count)
        return expired_count



class ResPartner(models.Model):
    _inherit = 'res.partner'

    contract_document_ids = fields.One2many(
        'contract.document',
        'partner_id',
        string='Contracts',
    )
    analytic_account_ids = fields.One2many(
        comodel_name='account.analytic.account',
        inverse_name='partner_id',
        string='Analytic Accounts',
    )


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
    )
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    state = fields.Selection(
        selection=[('active', 'Active'), ('inactive', 'Inactive')],
        compute='_compute_state',
        string='Status',
    )

    def _compute_state(self):
        for rec in self:
            rec.state = 'active' if getattr(rec, 'active', True) else 'inactive'
