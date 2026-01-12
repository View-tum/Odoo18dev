from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    so_type_id = fields.Many2one(
        "sale.sequence.type", string="SO Type", required=True)
    
    market_scope = fields.Selection(
        related="so_type_id.market_scope",
        string="Market Scope",
        readonly=True,
    )
    
    inter_vat_id = fields.Many2one(
        "account.tax",
        string="Foreign VAT",
        readonly=True,
        help="VAT fetched from settings when SO Type is Foreign",
    )

    @api.onchange("so_type_id")
    def _onchange_so_type_id(self):
        if self.so_type_id and self.so_type_id.market_scope == "inter":
            company = self.company_id or self.env.company
            
            # Set Journal from settings
            if company.inter_journal_id:
                self.journal_id = company.inter_journal_id

            # Special case: Domestic Purchase (Export)
            if self.partner_id.is_domestic_export:
                self.inter_vat_id = False
                return

            vat = company.inter_vat_id
            if not vat:
                return {
                    'warning': {
                        'title': "Missing Foreign VAT Setting",
                        'message': "Please configure the Foreign VAT in Sales Settings."
                    }
                }
            self.inter_vat_id = vat
            
            # Set Fiscal Position from settings
            if company.inter_fiscal_position_id:
                self.fiscal_position_id = company.inter_fiscal_position_id
        else:
            self.inter_vat_id = False
            # Reset to default logic if switching back from inter
            # We don't necessarily want to clear them if the user set them manually before,
            # but usually switching type implies resetting defaults.
            # However, standard Odoo recomputes fiscal position based on partner on change.
            # Here we just leave it as is or could trigger recomputation.
            # For safety, let's only reset if they match the inter settings to avoid clearing manual changes.
            company = self.company_id or self.env.company
            if self.journal_id == company.inter_journal_id:
                self.journal_id = False
            if self.fiscal_position_id == company.inter_fiscal_position_id:
                # Re-trigger standard compute logic for fiscal position
                self._compute_fiscal_position_id()

    @api.onchange("partner_id")
    def _onchange_partner_id_so_type(self):
        if self.so_type_id.market_scope == "inter":
            if self.partner_id.is_domestic_export:
                self.inter_vat_id = False
            else:
                company = self.company_id or self.env.company
                if company.inter_vat_id:
                    self.inter_vat_id = company.inter_vat_id
                if company.inter_fiscal_position_id:
                    self.fiscal_position_id = company.inter_fiscal_position_id

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.so_type_id.market_scope == 'inter':
             company = self.company_id or self.env.company
             if company.inter_journal_id:
                 vals['journal_id'] = company.inter_journal_id.id
        return vals


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_id', 'company_id', 'order_id.inter_vat_id', 'order_id.market_scope')
    def _compute_tax_id(self):
        super()._compute_tax_id()
        for line in self:
            if line.order_id.market_scope == "inter" and line.order_id.inter_vat_id:
                line.tax_id = line.order_id.inter_vat_id
