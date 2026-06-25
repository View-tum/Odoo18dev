from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    settlement_move_ids = fields.Many2many(
        'account.move', 
        compute='_compute_settlement_move_ids', 
        string='Settlement Entries'
    )
    settlement_move_count = fields.Integer(
        compute='_compute_settlement_move_ids', 
        string='Settlement Count'
    )

    def _compute_settlement_move_ids(self):
        for move in self:
            matched_moves = self.env['account.move']
            if move.state == 'posted':
                for line in move.line_ids.filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')):
                    partials = line.matched_debit_ids | line.matched_credit_ids
                    for partial in partials:
                        matched_line = partial.debit_move_id if partial.credit_move_id == line else partial.credit_move_id
                        if matched_line.move_id.ref and matched_line.move_id.ref.startswith('PAY-SETTLE'):
                            matched_moves |= matched_line.move_id
            move.settlement_move_ids = matched_moves
            move.settlement_move_count = len(matched_moves)

    def action_view_settlement_moves(self):
        self.ensure_one()
        return {
            'name': _('Settlement Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.settlement_move_ids.ids)],
        }

    def _get_partner_settlement_wht_source_lines(self):
        self.ensure_one()
        if self.move_type != "in_invoice":
            return self.env["account.move.line"]
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and (line.wht_tax_id or getattr(line, "wht_tax_ids", False))
        )

    def _get_partner_settlement_amount_in_currency(self, amount, currency, date):
        self.ensure_one()
        source_currency = self.currency_id or self.company_currency_id
        if source_currency == currency:
            return currency.round(abs(amount))
        return currency.round(
            source_currency._convert(
                abs(amount),
                currency,
                self.company_id,
                date or fields.Date.context_today(self),
            )
        )

    def _get_partner_settlement_open_gross_amount(self, currency, date):
        self.ensure_one()
        amount = abs(self.amount_residual) or abs(self.amount_total)
        return self._get_partner_settlement_amount_in_currency(amount, currency, date)

    def _prepare_partner_settlement_wht_items(self, gross_amount, date, currency):
        self.ensure_one()
        if not currency or currency.compare_amounts(gross_amount, 0.0) <= 0:
            return []
        source_lines = self._get_partner_settlement_wht_source_lines()
        if not source_lines:
            return []

        full_gross = self._get_partner_settlement_open_gross_amount(currency, date)
        if currency.compare_amounts(full_gross, 0.0) <= 0:
            return []
        pay_ratio = min(abs(gross_amount) / full_gross, 1.0)

        if hasattr(source_lines, "_prepare_multi_wht_deduction_list"):
            deduction_list, _amount_deduct = source_lines._prepare_multi_wht_deduction_list(
                date,
                currency,
                pay_ratio=pay_ratio,
            )
        else:
            deduction_list, _amount_deduct = source_lines._prepare_deduction_list(date, currency)
            for deduction in deduction_list:
                deduction["amount"] = currency.round(deduction.get("amount", 0.0) * pay_ratio)
                deduction["wht_amount_base"] = currency.round(
                    deduction.get("wht_amount_base", 0.0) * pay_ratio
                )

        items = []
        for deduction in deduction_list:
            amount = currency.round(abs(deduction.get("amount", 0.0)))
            if currency.compare_amounts(amount, 0.0) <= 0:
                continue
            base = currency.round(abs(deduction.get("wht_amount_base", 0.0)))
            wht_tax = self.env["account.withholding.tax"].browse(deduction.get("wht_tax_id")).exists()
            account = self.env["account.account"].browse(deduction.get("account_id")).exists()
            if not wht_tax or not account:
                continue
            partner = self.env["res.partner"].browse(deduction.get("partner_id")).exists() or self.partner_id
            items.append(
                {
                    "move": self,
                    "partner": partner,
                    "wht_tax": wht_tax,
                    "account": account,
                    "name": deduction.get("name") or wht_tax.display_name,
                    "base": base,
                    "amount": amount,
                    "wht_cert_income_type": deduction.get("wht_cert_income_type"),
                    "wht_cert_income_desc": deduction.get("wht_cert_income_desc"),
                }
            )
        return items

    def _get_partner_settlement_wht_amount(self, gross_amount, date, currency):
        self.ensure_one()
        return currency.round(
            sum(item["amount"] for item in self._prepare_partner_settlement_wht_items(gross_amount, date, currency))
        )

    def _get_partner_settlement_net_amount(self, gross_amount, date, currency):
        self.ensure_one()
        wht_amount = self._get_partner_settlement_wht_amount(gross_amount, date, currency)
        return currency.round(max(gross_amount - wht_amount, 0.0))

    def _get_partner_settlement_gross_from_net_amount(self, net_amount, date, currency):
        self.ensure_one()
        if not currency or currency.compare_amounts(net_amount, 0.0) <= 0:
            return 0.0
        full_gross = self._get_partner_settlement_open_gross_amount(currency, date)
        if currency.compare_amounts(full_gross, 0.0) <= 0:
            return currency.round(net_amount)
        full_wht = self._get_partner_settlement_wht_amount(full_gross, date, currency)
        full_net = currency.round(full_gross - full_wht)
        if currency.compare_amounts(full_net, 0.0) <= 0:
            return currency.round(net_amount)
        ratio = min(abs(net_amount) / full_net, 1.0)
        return currency.round(full_gross * ratio)

    def _create_partner_settlement_wht_cert_if_ready(self):
        for move in self:
            if not move.wht_move_ids or move.wht_cert_ids:
                continue
            if move.wht_move_ids.filtered(lambda wht: not wht.wht_cert_income_type):
                continue
            move.create_wht_cert()
