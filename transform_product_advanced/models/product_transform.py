# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ProductTransform(models.Model):
    _name = "product.transform"
    _description = "Product Transform"
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference",
        default=lambda self: _("New"),
        copy=False,
    )
    date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # 🔹 Rule drives everything
    rule_id = fields.Many2one(
        "product.transform.rule",
        string="Transform Rule",
        required=True,
        help="Predefined transformation rule (from product, to product, factor).",
    )

    # Derived from rule (readonly in UI)
    product_from_id = fields.Many2one(
        "product.product",
        string="From Product",
        related="rule_id.product_from_id",
        store=True,
        readonly=True,
    )
    product_to_id = fields.Many2one(
        "product.product",
        string="To Product",
        related="rule_id.product_to_id",
        store=True,
        readonly=True,
    )

    transform_factor = fields.Float(
        string="Factor (To per 1 From)",
        compute="_compute_transform_factor",
        store=True,
        readonly=True,
        help="How many 'To Product' are created from 1 'From Product', coming from the rule.",
    )

    qty_from = fields.Float(
        string="From Quantity",
        required=True,
        default=1.0,
    )
    qty_to = fields.Float(
        string="To Quantity",
        compute="_compute_qty_to",
        store=True,
        readonly=True,
    )

    uom_from_id = fields.Many2one(
        "uom.uom",
        string="From UoM",
        related="product_from_id.uom_id",
        store=True,
        readonly=True,
    )
    uom_to_id = fields.Many2one(
        "uom.uom",
        string="To UoM",
        related="product_to_id.uom_id",
        store=True,
        readonly=True,
    )

    location_id = fields.Many2one(
        "stock.location",
        string="Source Location",
        required=True,
        default=lambda self: self.env.ref(
            "stock.stock_location_stock", raise_if_not_found=False
        ),
    )
    dest_location_id = fields.Many2one(
        "stock.location",
        string="Destination Location",
        required=True,
        default=lambda self: self.env.ref(
            "stock.stock_location_stock", raise_if_not_found=False
        ),
    )

    lot_from_id = fields.Many2one(
        "stock.lot",
        string="Lot (From Product)",
        help="Lot/batch of the product you are transforming.",
        domain="[('product_id', '=', product_from_id)]",
    )
    lot_to_id = fields.Many2one(
        "stock.lot",
        string="Lot (To Product)",
        help="Lot for the transformed product (same lot name as From Lot).",
        readonly=True,
    )

    move_out_id = fields.Many2one(
        "stock.move",
        string="Consume Move",
        readonly=True,
    )
    move_in_id = fields.Many2one(
        "stock.move",
        string="Produce Move",
        readonly=True,
    )
    
    svl_count = fields.Integer(
        string="Valuation Layers",
        compute="_compute_svl_count",
        readonly=True,
    )
    
    
    @api.onchange("location_id")
    def _onchange_location_id(self):
        if self.location_id:
            self.dest_location_id = self.location_id.id

    # ========= COMPUTES =========

    @api.depends("rule_id", "rule_id.qty_to")
    def _compute_transform_factor(self):
        for rec in self:
            rec.transform_factor = rec.rule_id.qty_to or 1.0

    @api.depends("qty_from", "transform_factor")
    def _compute_qty_to(self):
        for rec in self:
            rec.qty_to = rec.qty_from * (rec.transform_factor or 0.0)

    @api.constrains("rule_id")
    def _check_rule_products(self):
        for rec in self:
            if not rec.rule_id:
                continue
            if not rec.product_from_id or not rec.product_to_id:
                raise ValidationError(
                    _("The chosen rule must have both From Product and To Product.")
                )
            if rec.product_from_id == rec.product_to_id:
                raise ValidationError(
                    _("From Product and To Product in the rule must be different.")
                )

    # ========= LOT HANDLING =========

    def _get_or_create_to_lot(self):
        """
        Reuse same lot number:
        - find/create lot on product_to with the same name as lot_from.
        """
        for rec in self:
            if not rec.lot_from_id:
                rec.lot_to_id = False
                continue

            StockLot = self.env["stock.lot"]
            lot = StockLot.search(
                [
                    ("product_id", "=", rec.product_to_id.id),
                    ("name", "=", rec.lot_from_id.name),
                ],
                limit=1,
            )
            if not lot:
                lot = StockLot.create(
                    {
                        "product_id": rec.product_to_id.id,
                        "name": rec.lot_from_id.name,
                        "company_id": rec.company_id.id,
                    }
                )
            rec.lot_to_id = lot.id

    # ========= MAIN ACTIONS =========

    def action_confirm(self):
        """Confirm transform and create stock moves based on the rule."""
        for rec in self:
            if rec.state != "draft":
                continue

            if rec.qty_from <= 0:
                raise UserError(_("From quantity must be > 0."))

            if rec.qty_to <= 0:
                raise UserError(_("Rule or quantity result must give To quantity > 0."))

            if not rec.rule_id:
                raise UserError(_("You must select a Transform Rule."))

            if rec.product_from_id.tracking != "none" and not rec.lot_from_id:
                raise UserError(
                    _(
                        "You must set a lot for the From Product because it is tracked."
                    )
                )

            if rec.name == _("New"):
                rec.name = (
                    self.env["ir.sequence"].next_by_code(
                        "transform_product_advanced.product_transform"
                    )
                    or _("New")
                )

            if rec.product_to_id.tracking != "none":
                rec._get_or_create_to_lot()

            rec._create_stock_moves()
            rec.state = "done"

    # -------------------------------------------------------------
    # FIFO helper: consume valuation layers for FROM product
    # -------------------------------------------------------------
    def _consume_fifo_layers(self, product, company, qty_to_consume):
        """
        Consume stock.valuation.layer rows FIFO-style for `product`
        and `company` until `qty_to_consume` is covered.

        - Reads SVLs with remaining_qty > 0
        - Consumes oldest layers first
        - Decreases remaining_qty / remaining_value on those layers
        - Returns total_value (sum of qty * unit_cost)

        Raises UserError if not enough remaining_qty.
        """
        SVL = self.env["stock.valuation.layer"]

        layers = SVL.search(
            [
                ("company_id", "=", company.id),
                ("product_id", "=", product.id),
                ("remaining_qty", ">", 0),
            ],
            order="create_date, id",
        )

        remaining_qty = qty_to_consume
        total_value = 0.0

        for layer in layers:
            if remaining_qty <= 0:
                break

            available = layer.remaining_qty
            if available <= 0:
                continue

            take_qty = min(available, remaining_qty)
            take_value = take_qty * layer.unit_cost

            # decrease remaining fields on this layer
            layer.remaining_qty -= take_qty
            layer.remaining_value -= take_value

            remaining_qty -= take_qty
            total_value += take_value

        if remaining_qty > 0:
            # not enough valuated stock for this product
            raise UserError(
                _(
                    "Not enough valuated stock for product %s. Missing quantity: %s"
                )
                % (product.display_name, remaining_qty)
            )

        return total_value

    # -------------------------------------------------------------
    # MAIN: create stock moves + FIFO valuation
    # -------------------------------------------------------------
    def _create_stock_moves(self):
        """
        Create stock moves and move lines to consume & produce products.
        Use internal Transform Location.

        Valuation:
        - OUT (From product): consume FIFO layers, create OUT SVL (negative qty/value)
        - IN  (To product)  : create IN SVL (positive qty/value) with same total value
        """
        StockMove = self.env["stock.move"]
        StockMoveLine = self.env["stock.move.line"]
        SVL = self.env["stock.valuation.layer"]

        for rec in self:
            if rec.qty_from <= 0 or rec.qty_to <= 0:
                raise UserError(_("Quantities must be > 0."))

            transform_location = self.env.ref(
                "transform_product_advanced.stock_location_transform",
                raise_if_not_found=False,
            )
            if not transform_location:
                raise UserError(
                    _(
                        "Transform Location not found. "
                        "Please ensure 'stock_location_transform' is created."
                    )
                )

            # nice labels for descriptions
            source_code_out = rec.location_id.display_name or rec.location_id.name
            dest_code_out = transform_location.display_name or transform_location.name
            source_code_in = transform_location.display_name or transform_location.name
            dest_code_in = rec.dest_location_id.display_name or rec.dest_location_id.name

            # =====================================================
            # 1) OUT MOVE: consume FROM product  (Stock -> Transform)
            # =====================================================
            move_out = StockMove.create(
                {
                    "name": rec.name or _("Product Transform Out"),
                    "product_id": rec.product_from_id.id,
                    "product_uom": rec.uom_from_id.id,
                    "product_uom_qty": rec.qty_from,
                    "location_id": rec.location_id.id,
                    "location_dest_id": transform_location.id,
                    "company_id": rec.company_id.id,
                }
            )
            move_out._action_confirm()

            move_out_line_vals = {
                "move_id": move_out.id,
                "product_id": rec.product_from_id.id,
                "product_uom_id": rec.uom_from_id.id,
                "qty_done": rec.qty_from,
                "location_id": rec.location_id.id,
                "location_dest_id": transform_location.id,
                "company_id": rec.company_id.id,
            }
            if rec.product_from_id.tracking != "none" and rec.lot_from_id:
                move_out_line_vals["lot_id"] = rec.lot_from_id.id

            StockMoveLine.create(move_out_line_vals)
            move_out._action_done()

            # check if Odoo already created SVL for this move
            vls_out = SVL.search([("stock_move_id", "=", move_out.id)])
            if vls_out:
                # use Odoo's valuation if it exists
                total_value_out = sum(vls_out.mapped("value"))
                unit_cost_from = (
                    abs(total_value_out) / rec.qty_from if rec.qty_from else 0.0
                )
            else:
                # no SVL created automatically -> do FIFO manually
                total_value_out = rec._consume_fifo_layers(
                    rec.product_from_id,
                    rec.company_id,
                    rec.qty_from,
                )
                unit_cost_from = total_value_out / rec.qty_from if rec.qty_from else 0.0

                SVL.create(
                    {
                        "company_id": rec.company_id.id,
                        "product_id": rec.product_from_id.id,
                        "stock_move_id": move_out.id,
                        "description": _("%s - Transform OUT: %s -> %s")
                        % (rec.name, source_code_out, dest_code_out),
                        "unit_cost": unit_cost_from,
                        "quantity": -rec.qty_from,
                        "value": -total_value_out,
                        "remaining_qty": 0.0,
                        "remaining_value": 0.0,
                    }
                )

            # =====================================================
            # 2) IN MOVE: produce TO product (Transform -> Stock)
            #     value = same total_value_out, spread on qty_to
            # =====================================================
            move_in = StockMove.create(
                {
                    "name": rec.name or _("Product Transform In"),
                    "product_id": rec.product_to_id.id,
                    "product_uom": rec.uom_to_id.id,
                    "product_uom_qty": rec.qty_to,
                    "location_id": transform_location.id,
                    "location_dest_id": rec.dest_location_id.id,
                    "company_id": rec.company_id.id,
                }
            )
            move_in._action_confirm()

            move_in_line_vals = {
                "move_id": move_in.id,
                "product_id": rec.product_to_id.id,
                "product_uom_id": rec.uom_to_id.id,
                "qty_done": rec.qty_to,
                "location_id": transform_location.id,
                "location_dest_id": rec.dest_location_id.id,
                "company_id": rec.company_id.id,
            }
            if rec.product_to_id.tracking != "none":
                lot_to = rec.lot_to_id
                if not lot_to:
                    rec._get_or_create_to_lot()
                    lot_to = rec.lot_to_id
                move_in_line_vals["lot_id"] = lot_to.id

            StockMoveLine.create(move_in_line_vals)
            move_in._action_done()

            vls_in = SVL.search([("stock_move_id", "=", move_in.id)])
            if not vls_in:
                # we use the SAME total_value_out for the TO product
                unit_cost_to = (
                    total_value_out / rec.qty_to if rec.qty_to else 0.0
                )

                SVL.create(
                    {
                        "company_id": rec.company_id.id,
                        "product_id": rec.product_to_id.id,
                        "stock_move_id": move_in.id,
                        "description": _("%s - Transform IN: %s -> %s")
                        % (rec.name, source_code_in, dest_code_in),
                        "unit_cost": unit_cost_to,
                        "quantity": rec.qty_to,
                        "value": total_value_out,
                        "remaining_qty": rec.qty_to,
                        "remaining_value": total_value_out,
                    }
                )

            rec.move_out_id = move_out.id
            rec.move_in_id = move_in.id
            
            
       
    # ---------- Compute count ----------
    def _compute_svl_count(self):
        SVL = self.env["stock.valuation.layer"]
        for rec in self:
            if not rec.move_out_id and not rec.move_in_id:
                rec.svl_count = 0
                continue
            domain = [
                ("stock_move_id", "in", [rec.move_out_id.id, rec.move_in_id.id]),
            ]
            rec.svl_count = SVL.search_count(domain)

    # ---------- Smart button action ----------
    def action_view_valuation_layers(self):
        """Open valuation layers related to this transform (moves OUT + IN).

        - If more than 1 SVL → list view
        - If exactly 1 SVL → open its form
        """
        self.ensure_one()
        SVL = self.env["stock.valuation.layer"]

        move_ids = [m.id for m in (self.move_out_id | self.move_in_id) if m]
        if not move_ids:
            raise UserError(_("No stock moves found for this transform."))

        domain = [("stock_move_id", "in", move_ids)]
        layers = SVL.search(domain)

        # Base action from stock_account
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "stock_account.stock_valuation_layer_action"
        )
        action["domain"] = domain

        if len(layers) == 1:
            # open directly the form view of this SVL
            form_view = self.env.ref(
                "stock_account.view_stock_valuation_layer_form"
            )
            action["views"] = [(form_view.id, "form")]
            action["res_id"] = layers.id

        return action


    def action_set_to_draft(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("Cannot reset a done transform to draft."))
            rec.state = "draft"

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("Cannot cancel a done transform."))
            rec.state = "cancel"
