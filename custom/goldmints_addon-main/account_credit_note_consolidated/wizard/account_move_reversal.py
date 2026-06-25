from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    include_vendor_returns = fields.Boolean(
        string="Include Vendor Returns",
        compute="_compute_include_vendor_returns",
    )
    available_return_picking_ids = fields.Many2many(
        "stock.picking",
        string="Available Vendor Returns",
        compute="_compute_available_return_picking_ids",
    )
    return_picking_ids = fields.Many2many(
        "stock.picking",
        "account_move_reversal_return_picking_rel",
        "wizard_id",
        "picking_id",
        string="Vendor Returns",
        check_company=True,
    )
    return_line_ids = fields.One2many(
        "account.move.reversal.return.line",
        "wizard_id",
        string="Return Lines",
    )

    @api.depends("move_ids")
    def _compute_include_vendor_returns(self):
        for wizard in self:
            wizard.include_vendor_returns = len(wizard.move_ids) == 1 and wizard.move_ids.move_type == "in_invoice"

    @api.depends("move_ids")
    def _compute_available_return_picking_ids(self):
        for wizard in self:
            wizard.available_return_picking_ids = wizard._get_available_return_pickings()

    @api.onchange("return_picking_ids")
    def _onchange_return_picking_ids(self):
        for wizard in self:
            commands = [Command.clear()]
            for stock_move in wizard._get_return_stock_moves(wizard.return_picking_ids):
                source_line = wizard._get_source_invoice_line(stock_move)
                commands.append(Command.create({
                    "picking_id": stock_move.picking_id.id,
                    "stock_move_id": stock_move.id,
                    "product_id": stock_move.product_id.id,
                    "quantity": wizard._get_stock_move_quantity(stock_move),
                    "price_unit": wizard._get_return_price_unit(stock_move, source_line),
                    "source_bill_line_id": source_line.id,
                }))
            wizard.return_line_ids = commands

    def _get_available_return_pickings(self):
        self.ensure_one()
        if not self.include_vendor_returns:
            return self.env["stock.picking"]
        origin_move = self.move_ids[:1]
        return_moves = self.env["stock.move"].search([
            ("picking_id.state", "=", "done"),
            ("picking_id.company_id", "=", origin_move.company_id.id),
            ("picking_id.partner_id.commercial_partner_id", "=", origin_move.commercial_partner_id.id),
            ("picking_id.picking_type_id.code", "=", "outgoing"),
            ("picking_id.return_id", "!=", False),
            ("origin_returned_move_id", "!=", False),
            ("state", "=", "done"),
        ])
        pickings = return_moves.mapped("picking_id")
        linked_credit_notes = self.env["account.move"].search([
            ("move_type", "=", "in_refund"),
            ("state", "!=", "cancel"),
            ("return_picking_ids", "in", pickings.ids),
        ])
        return pickings - linked_credit_notes.mapped("return_picking_ids")

    def _get_return_stock_moves(self, pickings):
        return pickings.mapped("move_ids").filtered(
            lambda move: move.state == "done"
            and move.origin_returned_move_id
            and move.product_id
            and self._get_stock_move_quantity(move)
        )

    def _get_stock_move_quantity(self, stock_move):
        return abs(stock_move.quantity or stock_move.product_uom_qty)

    def _get_source_invoice_line(self, stock_move):
        self.ensure_one()
        origin_move = self.move_ids[:1]
        lines = origin_move.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line.product_id == stock_move.product_id
        )
        if stock_move.purchase_line_id:
            exact_lines = lines.filtered(lambda line: line.purchase_line_id == stock_move.purchase_line_id)
            if exact_lines:
                lines = exact_lines
        return lines[:1]

    def _get_return_price_unit(self, stock_move, source_line):
        if source_line:
            return source_line.price_unit
        if stock_move.purchase_line_id:
            return stock_move.purchase_line_id.price_unit
        return stock_move.product_id.standard_price

    def _get_return_account(self, stock_move, source_line):
        if source_line and source_line.account_id:
            return source_line.account_id
        accounts = stock_move.product_id.with_company(self.move_ids[:1].company_id).product_tmpl_id.get_product_accounts()
        return accounts.get("expense")

    def _get_return_taxes(self, stock_move, source_line):
        if source_line and source_line.tax_ids:
            return source_line.tax_ids
        if stock_move.purchase_line_id and stock_move.purchase_line_id.taxes_id:
            return stock_move.purchase_line_id.taxes_id
        return stock_move.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.move_ids[:1].company_id)

    def _check_selected_vendor_returns(self):
        self.ensure_one()
        if not self.return_picking_ids:
            return
        if len(self.move_ids) != 1 or self.move_ids.move_type != "in_invoice":
            raise UserError(_("Vendor returns can be selected only when reversing one posted Vendor Bill."))
        origin_move = self.move_ids[:1]
        invalid_pickings = self.return_picking_ids.filtered(
            lambda picking: not (
                picking.state == "done"
                and picking.return_id
                and picking.picking_type_id.code == "outgoing"
                and picking.company_id == origin_move.company_id
                and picking.partner_id.commercial_partner_id == origin_move.commercial_partner_id
                and picking.move_ids.filtered(lambda move: move.origin_returned_move_id and move.state == "done")
            )
        )
        if invalid_pickings:
            raise UserError(_("Selected return pickings must be done vendor returns for the same vendor and company."))
        existing_credit_notes = self.env["account.move"].search([
            ("move_type", "=", "in_refund"),
            ("state", "!=", "cancel"),
            ("return_picking_ids", "in", self.return_picking_ids.ids),
        ])
        if existing_credit_notes:
            raise UserError(_("Some selected return pickings already have a vendor credit note."))

    def _prepare_return_invoice_line_vals(self, stock_move):
        self.ensure_one()
        source_line = self._get_source_invoice_line(stock_move)
        account = self._get_return_account(stock_move, source_line)
        if not account:
            raise UserError(_("No expense account is configured for %s.") % stock_move.product_id.display_name)
        vals = {
            "display_type": "product",
            "product_id": stock_move.product_id.id,
            "name": "%s: %s" % (stock_move.picking_id.name, source_line.name or stock_move.product_id.display_name),
            "quantity": self._get_stock_move_quantity(stock_move),
            "product_uom_id": stock_move.product_uom.id,
            "price_unit": self._get_return_price_unit(stock_move, source_line),
            "account_id": account.id,
            "tax_ids": [Command.set(self._get_return_taxes(stock_move, source_line).ids)],
            "return_picking_id": stock_move.picking_id.id,
            "return_stock_move_id": stock_move.id,
        }
        if source_line and source_line.purchase_line_id:
            vals["purchase_line_id"] = source_line.purchase_line_id.id
        elif stock_move.purchase_line_id:
            vals["purchase_line_id"] = stock_move.purchase_line_id.id
        if source_line and source_line.analytic_distribution:
            vals["analytic_distribution"] = source_line.analytic_distribution
        return vals

    def _apply_vendor_return_lines(self, credit_note):
        self.ensure_one()
        return_moves = self._get_return_stock_moves(self.return_picking_ids)
        if not return_moves:
            raise UserError(_("Selected return pickings do not contain done return lines."))
        credit_note.with_context(check_move_validity=False).write({
            "return_picking_ids": [Command.set(self.return_picking_ids.ids)],
            "invoice_line_ids": [
                Command.clear(),
                *[Command.create(self._prepare_return_invoice_line_vals(stock_move)) for stock_move in return_moves],
            ],
        })

    def reverse_moves(self, is_modify=False):
        self.ensure_one()
        if self.return_picking_ids and is_modify:
            raise UserError(_("Vendor returns can be used with Reverse only."))
        self._check_selected_vendor_returns()
        action = super().reverse_moves(is_modify=is_modify)
        if self.return_picking_ids:
            credit_note = self.new_move_ids.filtered(lambda move: move.move_type == "in_refund")[:1]
            if not credit_note:
                raise UserError(_("No Vendor Credit Note was created."))
            self._apply_vendor_return_lines(credit_note)
        return action


class AccountMoveReversalReturnLine(models.TransientModel):
    _name = "account.move.reversal.return.line"
    _description = "Vendor Return Credit Note Preview Line"

    wizard_id = fields.Many2one("account.move.reversal", required=True, ondelete="cascade")
    picking_id = fields.Many2one("stock.picking", string="Return", readonly=True)
    stock_move_id = fields.Many2one("stock.move", string="Stock Move", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    price_unit = fields.Float(string="Unit Price", readonly=True)
    source_bill_line_id = fields.Many2one("account.move.line", string="Bill Line", readonly=True)
