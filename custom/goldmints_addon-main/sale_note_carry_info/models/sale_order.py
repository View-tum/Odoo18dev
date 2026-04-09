from odoo import api, fields, models
from odoo.tools import html2plaintext


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_note = fields.Text(
        string="Note",
        help="(365 custom) Internal note for this Sales Order. This note will be carried over to related documents like deliveries and invoices."
    )
    internal_note = fields.Text(
        string="Internal Note",
        help="(365 custom) Partner internal note copied from the customer comment."
    )

    def _fill_missing_partner_addresses(self, vals):
        """Ensure invoice/shipping partners are set to avoid NOT NULL errors."""
        partner_id = vals.get("partner_id") or vals.get("partner_invoice_id") or vals.get("partner_shipping_id")
        if not partner_id:
            return vals
        if not vals.get("partner_invoice_id"):
            vals["partner_invoice_id"] = partner_id
        if not vals.get("partner_shipping_id"):
            vals["partner_shipping_id"] = partner_id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._fill_missing_partner_addresses(vals.copy()) for vals in vals_list]
        return super().create(vals_list)

    # helper field: all allowed invoice addresses for this order
    invoice_partner_ids = fields.Many2many(
        'res.partner',
        string="Allowed Invoice Partners",
        compute='_compute_invoice_partner_ids',
        store=False,
    )

    shipping_partner_ids = fields.Many2many(
        'res.partner',
        string="Allowed Shipping Partners",
        compute='_compute_shipping_partner_ids',
        store=False,
    )

    partner_invoice_id = fields.Many2one(
        comodel_name='res.partner',
        string="Invoice Address",
        compute='_compute_partner_invoice_id',
        store=True, readonly=False, required=True, precompute=True,
        check_company=True, domain="[('id', 'in', invoice_partner_ids)]",
        index='btree_not_null')

    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string="Delivery Address",
        compute='_compute_partner_shipping_id',
        store=True, readonly=False, required=True, precompute=True,
        check_company=True, domain="[('id', 'in', shipping_partner_ids)]",
        index='btree_not_null')

    @api.depends('partner_id', 'partner_id.child_ids.type')
    def _compute_invoice_partner_ids(self):
        for order in self:
            if not order.partner_id:
                order.invoice_partner_ids = False
                continue

            # all child partners with type == 'invoice'
            invoice_partners = order.partner_id.child_ids.filtered(
                lambda p: p.type == 'invoice')

            # if you also want to allow the main partner as invoice when no child:
            if not invoice_partners:
                invoice_partners = order.partner_id

            order.invoice_partner_ids = invoice_partners

    @api.depends('partner_id', 'partner_id.child_ids.type')
    def _compute_partner_invoice_id(self):
        # keep Odoo’s default behavior if you want:
        # super(SaleOrder, self)._compute_partner_invoice_id()

        for order in self:
            if not order.partner_id:
                order.partner_invoice_id = False
                continue

            invoice_partners = order.partner_id.child_ids.filtered(
                lambda p: p.type == 'invoice')

            # If a value was explicitly provided (e.g., during imports), keep it as long as it fits the allowed set.
            if order.partner_invoice_id and (
                order.partner_invoice_id == order.partner_id or order.partner_invoice_id in invoice_partners
            ):
                continue

            if invoice_partners:
                # pick the first available invoice address to avoid null constraint failures
                order.partner_invoice_id = invoice_partners[0]
            else:
                # fallback to the main partner when no invoice child exists
                order.partner_invoice_id = order.partner_id.id

    @api.depends('partner_id', 'partner_id.child_ids.type')
    def _compute_shipping_partner_ids(self):
        for order in self:
            if not order.partner_id:
                order.shipping_partner_ids = False
                continue

            # all child partners with type == 'delivery'
            shipping_partners = order.partner_id.child_ids.filtered(
                lambda p: p.type == 'delivery')

            # if you also want to allow the main partner as invoice when no child:
            if not shipping_partners:
                shipping_partners = order.partner_id

            order.shipping_partner_ids = shipping_partners

    @api.depends('partner_id', 'partner_id.child_ids.type')
    def _compute_partner_shipping_id(self):
        # keep Odoo’s default behavior if you want:
        # super(SaleOrder, self)._compute_partner_shipping_id()

        for order in self:
            if not order.partner_id:
                order.partner_shipping_id = False
                continue

            shipping_partners = order.partner_id.child_ids.filtered(
                lambda p: p.type == 'delivery')

            if order.partner_shipping_id and (
                order.partner_shipping_id == order.partner_id or order.partner_shipping_id in shipping_partners
            ):
                continue

            if shipping_partners:
                order.partner_shipping_id = shipping_partners[0]
            else:
                order.partner_shipping_id = order.partner_id.id

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        res = super()._onchange_partner_id_warning()
        for order in self:
            if order.partner_id and order.partner_id.comment:
                # Convert HTML to plain text
                plain_comment = html2plaintext(order.partner_id.comment).strip()
                order.internal_note = plain_comment if plain_comment else False
        return res

    # @api.depends('partner_id')
    # def _compute_partner_invoice_id(self):
    #     res = super(SaleOrder, self)._compute_partner_invoice_id()
    #     for order in self:
    #         if order.partner_id:
    #             order.partner_invoice_id = False
    #     return res

    # @api.depends('partner_id')
    # def _compute_partner_shipping_id(self):
    #     res = super(SaleOrder, self)._compute_partner_shipping_id()
    #     for order in self:
    #         if order.partner_id:
    #             order.partner_shipping_id = False
    #     return res
