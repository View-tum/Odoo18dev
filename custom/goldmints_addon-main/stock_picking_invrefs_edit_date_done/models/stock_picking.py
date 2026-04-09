import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    require_invoice_info = fields.Boolean(
        string="Require Invoice Reference/Date",
        help="When enabled, related pickings must capture Invoice Reference and Invoice Date.",
    )
    propagate_invoice_info = fields.Boolean(
        string="Propagate Invoice Reference/Date",
        help="Copy the Invoice Reference and Date entered on this operation type to the next pickings.",
    )
    show_delivery_address = fields.Boolean(
        string="Show Delivery Address",
        help="If enabled, picking form will display the delivery address from the related Sale Order.",
    )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    invoice_reference = fields.Char(
        string="Invoice reference",
        help="External reference provided by the vendor during receipt.",
        copy=False,
        index=True,
    )

    invoice_date = fields.Date(
        string="Invoice date",
        help="Invoice or reference date provided by the vendor.",
        copy=False,
        index=True,
    )

    show_invoice_info = fields.Boolean(
        string="Show Invoice Info",
        related="picking_type_id.require_invoice_info",
        readonly=True,
    )

    show_so_delivery_address = fields.Boolean(
        string="Show SO Delivery Address",
        related="picking_type_id.show_delivery_address",
        readonly=True,
    )

    so_delivery_address = fields.Html(
        string="SO Delivery Address",
        compute="_compute_so_delivery_address",
        help="The delivery address from the related Sale Order.",
    )

    @api.depends("show_so_delivery_address", "sale_id.partner_shipping_id")
    def _compute_so_delivery_address(self):
        for picking in self:
            if picking.show_so_delivery_address and picking.sale_id:
                partner = picking.sale_id.partner_shipping_id
                # Use standard display_name or contact_address depending on preference
                # but partner_shipping_id usually has the full address block in contact_address
                address_parts = [
                    partner.name,
                    partner.street,
                    partner.street2,
                    f"{partner.city or ''} {partner.state_id.name or ''} {partner.zip or ''}",
                    partner.country_id.name,
                ]
                # Filter out empty parts and join with <br/> for HTML
                address_html = "<br/>".join([p for p in address_parts if p])
                picking.so_delivery_address = f"<div style='font-family: inherit; line-height: 1.4;'>{address_html}</div>"
            else:
                picking.so_delivery_address = False

    def _requires_invoice_info(self):
        self.ensure_one()
        return bool(self.picking_type_id and self.picking_type_id.require_invoice_info)

    @api.model_create_multi
    def create(self, vals_list):
        skip_ctx = self.with_context(skip_invoice_constraint=True)
        pickings = super(StockPicking, skip_ctx).create(vals_list)
        pickings._prefill_invoice_info_from_origins()
        if any({"invoice_reference", "invoice_date"} & vals.keys() for vals in vals_list):
            pickings._propagate_invoice_info_to_next_pickings()
        return pickings

    def write(self, vals):
        res = super().write(vals)
        if {"invoice_reference", "invoice_date"} & vals.keys():
            self._propagate_invoice_info_to_next_pickings()
        else:
            self._prefill_invoice_info_from_origins()
        return res

    def _propagate_invoice_info_to_next_pickings(self):
        """Copy invoice info from Receipts to linked Storage pickings."""
        for picking in self.filtered(lambda p: p.picking_type_id.propagate_invoice_info):
            if not picking.invoice_reference or not picking.invoice_date:
                continue
            dest_pickings = self._get_related_moves(picking).move_dest_ids.mapped("picking_id")
            dest_pickings = dest_pickings.filtered(lambda p: p.picking_type_id.require_invoice_info)
            to_update = dest_pickings.filtered(
                lambda p: p.invoice_reference != picking.invoice_reference
                or p.invoice_date != picking.invoice_date
            )
            if to_update:
                to_update.with_context(skip_invoice_constraint=True).write({
                    "invoice_reference": picking.invoice_reference,
                    "invoice_date": picking.invoice_date,
                })

    def _prefill_invoice_info_from_origins(self):
        """Fetch invoice info from linked invoices or upstream pickings when required."""
        for picking in self.filtered(lambda p: p.picking_type_id.require_invoice_info):
            if picking.invoice_reference and picking.invoice_date:
                _logger.debug("Picking %s already has invoice info (%s / %s)", picking.id, picking.invoice_reference, picking.invoice_date)
                continue

            # NEW: Try to fetch from linked Invoices (Sale Invoices / Vendor Bills)
            linked_invoices = picking._get_linked_invoices()
            if linked_invoices:
                invoice = linked_invoices[0]
                # Use 'ref' (for Vendor Bills) or 'name' (for Sales Invoices)
                ref = invoice.ref or invoice.name
                _logger.debug("Prefilling picking %s from Invoice %s (ref=%s date=%s)", picking.id, invoice.id, ref, invoice.invoice_date)
                picking.with_context(skip_invoice_constraint=True).write({
                    "invoice_reference": ref,
                    "invoice_date": invoice.invoice_date,
                })
                continue

            _logger.debug("Searching origins for picking %s (group_id=%s)", picking.id, getattr(picking.group_id, 'id', None))
            origin_pickings = self.env["stock.picking"]

            # RMA Integration: If linked to a claim, try the claim's source picking first
            if hasattr(picking, 'claim_id') and picking.claim_id and picking.claim_id.picking_id:
                source_do = picking.claim_id.picking_id
                if source_do.invoice_reference and source_do.invoice_date:
                    _logger.debug("Found RMA origin DO %s for picking %s", source_do.id, picking.id)
                    origin_pickings |= source_do

            if not origin_pickings:
                origin_pickings = self._get_related_moves(picking).move_orig_ids.mapped("picking_id")
                origin_pickings = origin_pickings.filtered(
                    lambda op: op.picking_type_id.propagate_invoice_info
                    and op.invoice_reference
                    and op.invoice_date
                )
                _logger.debug("Found %s origin pickings via moves for picking %s", len(origin_pickings), picking.id)

            if not origin_pickings and picking.group_id:
                origin_pickings = self.env["stock.picking"].search([
                    ("group_id", "=", picking.group_id.id),
                    ("id", "!=", picking.id),
                    ("picking_type_id.propagate_invoice_info", "=", True),
                    ("invoice_reference", "!=", False),
                    ("invoice_date", "!=", False),
                ], limit=1, order="id desc")
                _logger.debug("Fallback search by group_id returned %s records for picking %s", len(origin_pickings), picking.id)

            if not origin_pickings:
                _logger.debug("No origin with invoice info found for picking %s", picking.id)
                continue

            origin = origin_pickings[0]
            _logger.debug("Prefilling picking %s from origin %s (ref=%s date=%s)", picking.id, origin.id, origin.invoice_reference, origin.invoice_date)
            picking.with_context(skip_invoice_constraint=True).write({
                "invoice_reference": origin.invoice_reference,
                "invoice_date": origin.invoice_date,
            })
            _logger.debug("Write complete for picking %s (ref=%s date=%s)", picking.id, origin.invoice_reference, origin.invoice_date)

    def _get_linked_invoices(self):
        """Find posted invoices linked to the picking via Sale Order or Purchase Order."""
        self.ensure_one()
        invoices = self.env['account.move']

        # Check Sale Order invoices
        if hasattr(self, 'sale_id') and self.sale_id:
            invoices |= self.sale_id.invoice_ids.filtered(lambda m: m.state == 'posted' and m.move_type in ('out_invoice', 'out_refund'))

        # Check Purchase Order invoices
        if hasattr(self, 'purchase_id') and self.purchase_id:
            invoices |= self.purchase_id.invoice_ids.filtered(lambda m: m.state == 'posted' and m.move_type in ('in_invoice', 'in_refund'))

        return invoices.sorted('invoice_date', reverse=True)

    def _ensure_invoice_info_presence(self, force=False):
        """Ensure required pickings have the invoice metadata filled."""
        for picking in self:
            if not picking._requires_invoice_info():
                continue
            if not force and picking.state not in ("done",):
                # Only enforce automatically once the picking is finished
                continue
            if picking.state in ("draft", "cancel"):
                continue
            if picking.invoice_reference and picking.invoice_date:
                continue
            _logger.debug("_ensure_invoice_info_presence: picking %s missing invoice info, attempting prefill", picking.id)
            # Try to prefill invoice info from upstream pickings. The
            # prefill implementation writes values on the record; invalidate
            # the ORM cache to ensure we read the freshly written values
            # before enforcing the presence check.
            picking._prefill_invoice_info_from_origins()
            # In some environments the in-memory cache may still hold old
            # values. Some Odoo builds do not expose `invalidate_cache` on
            # records; use `invalidate_model()` which exists here to force a
            # model-level cache invalidation before re-reading fields.
            try:
                picking.invalidate_cache(keys=["invoice_reference", "invoice_date"])
            except AttributeError:
                _logger.debug(
                    "invalidate_cache not available on picking, falling back to invalidate_model()"
                )
                picking.invalidate_model()

            _logger.debug("After prefill+invalidate: picking %s has ref=%s date=%s", picking.id, picking.invoice_reference, picking.invoice_date)
            _logger.debug("After prefill+invalidate: picking %s has ref=%s date=%s", picking.id, picking.invoice_reference, picking.invoice_date)
            if not picking.invoice_reference or not picking.invoice_date:
                raise ValidationError(
                    _("Invoice Reference and Invoice Date are required for the '%s' operation type.")
                    % picking.picking_type_id.display_name
                )

    @api.constrains("invoice_reference", "invoice_date", "picking_type_id", "state")
    def _check_invoice_reference_and_date(self):
        """Ensure both fields are provided on Receipts and Storage transfers."""
        if self.env.context.get("skip_invoice_constraint"):
            return
        self._ensure_invoice_info_presence()

    @staticmethod
    def _get_related_moves(picking):
        """Return all moves to ensure propagation works with or without packages."""
        return picking.move_ids | picking.move_ids_without_package

    def button_validate(self):
        """Ensure invoice info is filled from upstream picks before validation."""
        self._prefill_invoice_info_from_origins()
        self._ensure_invoice_info_presence(force=True)
        res = super().button_validate()
        self._propagate_invoice_info_to_next_pickings()
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves.mapped("picking_id")._prefill_invoice_info_from_origins()
        return moves
