from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMultiCreditNote(models.TransientModel):
    """
    Wizard: Create a single consolidated Credit Note (in_refund)
    from multiple selected Vendor Bills (in_invoice).

    Validation order (fail-fast, most critical first):
        1. Active IDs exist
        2. All records are Vendor Bills (in_invoice)
        3. All bills are posted (state = 'posted')
        4. No bill has already been reversed (consolidated_cn_id / reversed_entry_id)
        5. All bills belong to the same company
        6. All bills belong to the same vendor (partner_id)
        7. All bills use the same currency
        8. CN date is not inside a locked fiscal or tax period

    After passing validation, the wizard:
        - Creates one account.move (in_refund) with lines merged from all bills
        - Each line name is prefixed with [BILL_NUMBER] for full traceability
        - Writes consolidated_bill_ids on the CN and consolidated_cn_id on each bill
        - Optionally sets reversed_entry_id (Odoo standard, points to first bill)
        - Posts a chatter message on each source bill linking to the CN
    """

    _name = 'account.multi.credit.note'
    _description = 'Create Credit Note from Multiple Vendor Bills'

    # ── Wizard fields ────────────────────────────────────────────────────────

    # Persist selected bills on the wizard record so the form view does not
    # depend on active_ids being present in the re-read context (Bug 2 fix).
    bill_ids = fields.Many2many(
        comodel_name='account.move',
        relation='account_multi_cn_wizard_bill_rel',
        column1='wizard_id',
        column2='move_id',
        string='Source Bills',
        readonly=True,
    )

    date = fields.Date(
        string='Credit Note Date',
        required=True,
        default=fields.Date.context_today,
    )
    reason = fields.Char(
        string='Reason',
        required=True,
        default='Credit Note for multiple vendor bills',
    )
    tax_invoice_number = fields.Char(
        string='Tax Invoice Number',
        help='Tax invoice number for the Credit Note (optional, Thai localization).',
    )
    tax_invoice_date = fields.Date(
        string='Tax Invoice Date',
        help='Tax invoice date for the Credit Note (optional, Thai localization).',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required=True,
        domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # Read-only summary shown in wizard before confirming
    bill_summary = fields.Text(
        string='Bills to Reverse',
        compute='_compute_bill_summary',
    )
    vendor_name = fields.Char(
        string='Vendor',
        compute='_compute_bill_summary',
    )
    total_amount = fields.Char(
        string='Combined Total',
        compute='_compute_bill_summary',
    )

    # ── Default get ──────────────────────────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Persist selected bills so the form view does not rely on active_ids
        # surviving the context round-trip to the client.
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['bill_ids'] = [(6, 0, active_ids)]
            # Derive company from the first selected bill so that in multi-company
            # setups the journal and company default to the bills' company, not
            # necessarily the user's currently active company.
            first_bill = self.env['account.move'].browse(active_ids[0])
            company = first_bill.company_id or self.env.company
        else:
            company = self.env.company
        journal = self.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', company.id)],
            limit=1,
        )
        if journal:
            res['journal_id'] = journal.id
        res['company_id'] = company.id
        return res

    # ── Computed summary ─────────────────────────────────────────────────────

    @api.depends('bill_ids')
    def _compute_bill_summary(self):
        for rec in self:
            bills = rec.bill_ids
            if not bills:
                rec.bill_summary = ''
                rec.vendor_name = ''
                rec.total_amount = ''
                continue

            currencies = bills.mapped('currency_id')
            mixed_currency = len(currencies) > 1
            # Use first currency for display; validation will reject mixed later.
            display_currency = currencies[:1]

            lines = []
            grand_total = 0.0
            for bill in bills:
                grand_total += bill.amount_total
                lines.append(
                    f"  • {bill.name or '(Draft)'}   "
                    f"{bill.invoice_date or '—'}   "
                    f"{bill.amount_total:,.2f} {bill.currency_id.name}"
                )

            separator = '─' * 52
            if mixed_currency:
                total_line = "  Total : (mixed currencies — see lines above)"
                rec.total_amount = '(mixed)'
            else:
                total_line = (
                    f"  Total : {grand_total:,.2f} "
                    f"{display_currency.name}"
                )
                rec.total_amount = (
                    f"{grand_total:,.2f} "
                    f"{display_currency.symbol or display_currency.name}"
                )

            rec.bill_summary = '\n'.join(lines) + f"\n{separator}\n{total_line}"
            rec.vendor_name = bills[0].partner_id.name

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _get_raw_bills(self):
        """Return account.move records — prefer stored bill_ids, fall back to context."""
        if self.bill_ids:
            return self.bill_ids
        bill_ids = self.env.context.get('active_ids', [])
        if not bill_ids:
            return self.env['account.move']
        return self.env['account.move'].browse(bill_ids)

    def _get_validated_bills(self):
        """
        Return validated account.move recordset.
        Raises UserError at the first failed rule (fail-fast).
        """
        bills = self._get_raw_bills()

        # 1. At least one record selected
        if not bills:
            raise UserError(_("No Vendor Bills selected. Please select at least one bill."))

        # 2. All must be Vendor Bills
        non_bills = bills.filtered(lambda m: m.move_type != 'in_invoice')
        if non_bills:
            raise UserError(_(
                "Only Vendor Bills (in_invoice) can be reversed with this action.\n"
                "The following selected records are not Vendor Bills:\n\n%s"
            ) % '\n'.join(f"  • {m.name or m.id}" for m in non_bills))

        # 3. All must be posted
        non_posted = bills.filtered(lambda m: m.state != 'posted')
        if non_posted:
            raise UserError(_(
                "Only posted bills can be reversed. "
                "Please confirm the following bills first:\n\n%s"
            ) % '\n'.join(f"  • {m.name or m.id} (state: {m.state})" for m in non_posted))

        # 4. None must have been reversed already.
        # Always check both mechanisms and accumulate results (Bug 3 + Bug 4 fix):
        #   a) Our custom field — skip CNs that were subsequently cancelled.
        #   b) Standard Odoo reversed_entry_id on any active CN.
        already_reversed = bills.filtered(
            lambda m: m.consolidated_cn_id and m.consolidated_cn_id.state != 'cancel'
        )
        existing_cn = self.env['account.move'].search([
            ('reversed_entry_id', 'in', bills.ids),
            ('move_type', '=', 'in_refund'),
            ('state', '!=', 'cancel'),
        ])
        if existing_cn:
            already_reversed |= existing_cn.mapped('reversed_entry_id')

        if already_reversed:
            raise UserError(_(
                "The following bills have already been reversed and cannot be reversed again:\n\n%s"
            ) % '\n'.join(
                f"  • {b.name}  →  CN: {b.consolidated_cn_id.name}"
                if b.consolidated_cn_id and b.consolidated_cn_id.state != 'cancel' else
                f"  • {b.name}  (already has a reversal entry)"
                for b in already_reversed
            ))

        # 5. All must belong to the same company
        companies = bills.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_(
                "All selected bills must belong to the same company.\n"
                "Found multiple companies:\n\n%s"
            ) % '\n'.join(f"  • {c.name}" for c in companies))

        # 6. All must have the same vendor
        vendors = bills.mapped('partner_id')
        if len(vendors) > 1:
            raise UserError(_(
                "All selected bills must belong to the same vendor.\n"
                "Found multiple vendors:\n\n%s\n\n"
                "Please select bills from one vendor at a time."
            ) % '\n'.join(f"  • {v.name}" for v in vendors))

        # 7. All must use the same currency
        currencies = bills.mapped('currency_id')
        if len(currencies) > 1:
            raise UserError(_(
                "All selected bills must use the same currency.\n"
                "Found multiple currencies:\n\n%s"
            ) % '\n'.join(f"  • {c.name}" for c in currencies))

        return bills

    def _check_lock_date(self, date):
        """
        Validate that the CN date does not fall inside a locked accounting
        or tax period. Uses self.company_id (not env.company) to support
        multi-company scenarios correctly (Bug 5 fix).
        """
        company = self.company_id

        if company.fiscalyear_lock_date and date <= company.fiscalyear_lock_date:
            raise UserError(_(
                "The Credit Note date (%s) falls within a locked fiscal period.\n"
                "The books are locked up to: %s\n\n"
                "Please choose a date after the lock date."
            ) % (date, company.fiscalyear_lock_date))

        if company.tax_lock_date and date <= company.tax_lock_date:
            raise UserError(_(
                "The Credit Note date (%s) falls within a locked tax period.\n"
                "Tax entries are locked up to: %s\n\n"
                "Please choose a date after the tax lock date."
            ) % (date, company.tax_lock_date))

    # ── Wizard actions ───────────────────────────────────────────────────────

    def action_open_wizard(self):
        """
        Called by the Server Action from the list view.
        Runs fast-fail validation BEFORE opening the popup so the user
        sees a clear error immediately rather than after filling the form.
        """
        self.ensure_one()
        self._get_validated_bills()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Consolidated Credit Note'),
            'res_model': 'account.multi.credit.note',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context),
        }

    def action_create_credit_note(self):
        """
        Main entry point called by the wizard's Confirm button.

        Steps:
            1. Re-validate (user may have taken time; lock dates may have changed)
            2. Check CN date against fiscal/tax lock dates
            3. Build merged invoice lines (one line per original bill line,
               prefixed with the source bill number)
            4. Create account.move (in_refund)
            5. Write cross-reference fields on CN and all source bills
            6. Post chatter messages on each source bill
            7. Redirect to the new CN form view
        """
        self.ensure_one()

        bills = self._get_validated_bills()
        self._check_lock_date(self.date)

        # ── Build merged lines ────────────────────────────────────────────────
        line_vals = []
        for bill in bills:
            for line in bill.invoice_line_ids:
                if line.display_type in ('line_section', 'line_note'):
                    continue
                if not line.account_id:
                    continue

                line_vals.append((0, 0, {
                    'name': f"[{bill.name}] {line.name or ''}".strip(),
                    'account_id': line.account_id.id,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'product_id': line.product_id.id or False,
                    'product_uom_id': line.product_uom_id.id or False,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                    'analytic_distribution': line.analytic_distribution or False,
                }))

        if not line_vals:
            raise UserError(_(
                "No valid invoice lines found in the selected bills.\n"
                "Please check that the bills contain product or account lines."
            ))

        # ── Create the Credit Note ────────────────────────────────────────────
        bill_numbers = ', '.join(bills.mapped('name'))
        customer_refs = ', '.join(filter(None, bills.mapped('ref')))

        cn_vals = {
            'move_type': 'in_refund',
            'partner_id': bills[0].partner_id.id,
            'invoice_date': self.date,
            'date': self.date,
            'journal_id': self.journal_id.id,
            # Use wizard's company_id field, not env.company, for multi-company
            # correctness (Bug 5 fix).
            'company_id': self.company_id.id,
            'currency_id': bills[0].currency_id.id,
            'ref': bill_numbers,
            'customer_ref': customer_refs,
            'payment_reference': '',
            # Odoo standard: point to first bill so it appears in the
            # "Reversal of" field on the CN form
            'reversed_entry_id': bills[0].id,
            'consolidated_bill_ids': [(6, 0, bills.ids)],
            'narration': self.reason,
            'invoice_line_ids': line_vals,
        }

        credit_note = self.env['account.move'].create(cn_vals)

        # ── Update Tax Invoice lines on CN (Thai localization) ───────────────
        # Guard against deployments where l10n_th_account_tax is not installed
        # to prevent KeyError when accessing an unregistered model (Bug 1 fix).
        if (self.tax_invoice_number or self.tax_invoice_date) and \
                'account.move.tax.invoice' in self.env:
            tax_invoices = self.env['account.move.tax.invoice'].search([
                ('move_id', '=', credit_note.id),
            ])
            if tax_invoices:
                vals = {}
                if self.tax_invoice_number:
                    vals['tax_invoice_number'] = self.tax_invoice_number
                if self.tax_invoice_date:
                    vals['tax_invoice_date'] = self.tax_invoice_date
                tax_invoices.write(vals)

        # ── Write back-references on source bills ─────────────────────────────
        bills.write({
            'consolidated_cn_id': credit_note.id,
        })

        # ── Chatter messages on each source bill ──────────────────────────────
        for bill in bills:
            bill.message_post(
                body=_(
                    "A consolidated Credit Note "
                    "<a href='#' data-oe-model='account.move' data-oe-id='%(cn_id)d'>"
                    "%(cn_name)s</a> has been created from this bill "
                    "(together with: %(others)s)."
                ) % {
                    'cn_id': credit_note.id,
                    'cn_name': (credit_note.name if credit_note.name != '/' else None) or _('Draft CN'),
                    'others': ', '.join(
                        (bills - bill).mapped('name')
                    ) or _('this bill only'),
                }
            )

        # ── Redirect to the new CN ────────────────────────────────────────────
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit Note'),
            'res_model': 'account.move',
            'res_id': credit_note.id,
            'view_mode': 'form',
            'target': 'current',
        }
