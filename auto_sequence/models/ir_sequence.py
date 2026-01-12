from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError
from odoo.exceptions import UserError

RANGE_TOKENS = ("%(range_year)s", "%(range_y)s", "%(range_month)s")

class IrSequence(models.Model):
    _inherit = "ir.sequence"

    def _uses_range_tokens(self):
        self.ensure_one()
        text = (self.prefix or "") + (self.suffix or "")
        return any(tok in text for tok in RANGE_TOKENS)

    def _month_bounds(self, day):
        start = day.replace(day=1)
        end = (start + relativedelta(months=1)) - relativedelta(days=1)
        return start, end

    def _ensure_month_range(self, date=None):
        self.ensure_one()
        date = fields.Date.to_date(date) or fields.Date.context_today(self)
        if not self.use_date_range and self._uses_range_tokens():
            self.sudo().write({"use_date_range": True})
        if not self.use_date_range:
            return None

        start, end = self._month_bounds(date)
        DateRange = self.env["ir.sequence.date_range"].sudo()
        dr = DateRange.search([("sequence_id","=",self.id),
                            ("date_from","=",start),
                            ("date_to","=",end)], limit=1)
        if dr:
            return dr

        # safe create
        self.env.cr.execute("SAVEPOINT autoseq_dr_sp")
        try:
            return DateRange.create({
                "sequence_id": self.id,
                "date_from": start,
                "date_to": end,
                "number_next": 1,
            })
        except IntegrityError:
            self.env.cr.execute("ROLLBACK TO SAVEPOINT autoseq_dr_sp")
            return DateRange.search([("sequence_id","=",self.id),
                                    ("date_from","=",start),
                                    ("date_to","=",end)], limit=1)

    @api.model
    def _next(self, sequence_date=None, **kwargs):
        self.ensure_one()
        the_date = fields.Date.to_date(sequence_date) or fields.Date.context_today(self)

        if self._uses_range_tokens() or self.use_date_range:
            self._ensure_month_range(the_date)

        # ให้แน่ใจว่า sequence_date ถูกส่งต่อไปยัง super เสมอ
        if 'sequence_date' not in kwargs:
            kwargs['sequence_date'] = sequence_date

        return super()._next(**kwargs)

    def _months_ahead(self):
        icp = self.env["ir.config_parameter"].sudo()
        raw = icp.get_param("auto_sequence.months_ahead", default="1")
        try:
            return max(0, int(raw))
        except Exception:
            return 1

    @api.model
    def cron_prefill_date_ranges(self):
        today = fields.Date.context_today(self)
        if today.day != 25:  # ✅ รันเฉพาะวันที่ 25
            return
        months = self._months_ahead()
        for seq in self.search([]):
            if not (seq._uses_range_tokens() or seq.use_date_range):
                continue
            for i in range(months + 1):
                target = today + relativedelta(months=i)
                seq._ensure_month_range(target)

    @api.model
    def next_by_code(self, sequence_code, sequence_date=None):
        company = self.env.company
        seq = self.sudo().search([
            ('code', '=', sequence_code),
            ('company_id', 'in', [company.id, False]),
        ], order='company_id desc', limit=1)

        if not seq:
            raise UserError(_("No sequence has been found for code '%s'. Please create one for company %s.")
                            % (sequence_code, company.display_name))

        the_date = fields.Date.to_date(sequence_date) or fields.Date.context_today(self)

        if seq._uses_range_tokens() or seq.use_date_range:
            seq._ensure_month_range(the_date)

        return seq._next(sequence_date=sequence_date)

    def next_by_id(self, sequence_date=None):
        self.ensure_one()
        the_date = fields.Date.to_date(sequence_date) or fields.Date.context_today(self)
        if self._uses_range_tokens() or self.use_date_range:
            self._ensure_month_range(the_date)
        return super().next_by_id(sequence_date=sequence_date)
