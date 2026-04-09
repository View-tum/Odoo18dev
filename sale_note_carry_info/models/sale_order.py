from odoo import api, fields, models
from odoo.tools import html2plaintext


class SaleOrder(models.Model):
    _inherit = "sale.order"

    sale_note = fields.Text(
        string="Note",
        help="(365 custom) Internal note for this Sales Order. This note will be carried over to related documents like deliveries and invoices."
    )

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

            invoice_ids = invoice_partners.ids

            if len(invoice_ids) == 1:
                # only one → set as default
                order.partner_invoice_id = invoice_partners[0]
            elif len(invoice_ids) > 1:
                # multiple → no default in UI
                order.partner_invoice_id = False
            else:
                # no invoice child → decide what you want
                # e.g. fallback to partner or leave False
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

            shipping_ids = shipping_partners.ids

            if len(shipping_ids) == 1:
                # only one → set as default
                order.partner_shipping_id = shipping_ids[0]
            elif len(shipping_ids) > 1:
                # multiple → no default in UI
                order.partner_shipping_id = False
            else:
                # no invoice child → decide what you want
                # e.g. fallback to partner or leave False
                order.partner_shipping_id = order.partner_id.id

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        res = super()._onchange_partner_id_warning()
        for order in self:
            if order.partner_id and order.partner_id.comment:
                # Convert HTML to plain text
                plain_comment = html2plaintext(
                    order.partner_id.comment).strip()
                existing = (order.sale_note or '').strip()
                # f"{existing}\n\n{plain_comment}" if existing else
                order.sale_note = plain_comment if plain_comment else False
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
