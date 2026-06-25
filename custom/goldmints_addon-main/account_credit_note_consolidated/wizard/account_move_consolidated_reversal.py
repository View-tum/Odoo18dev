from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveConsolidatedReversal(models.TransientModel):
    _name = "account.move.consolidated.reversal"
    _description = "Consolidate Bills and Returns Wizard"

    move_id = fields.Many2one("account.move", string="Target Credit Note", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Vendor/Customer", required=True)
    
    filter_type = fields.Selection([
        ('all', 'All Items'),
        ('return', 'Only Return Pickings'),
        ('bill', 'Only Invoices/Bills'),
    ], string="Filter Type", default='all')
    search_ref = fields.Char(string="Search Reference")
    
    line_ids = fields.One2many(
        "account.move.consolidated.reversal.line", "wizard_id", string="Select Items"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "account.move":
            move = self.env["account.move"].browse(self.env.context.get("active_id"))
            res["move_id"] = move.id
            res["partner_id"] = move.partner_id.id
        return res

    @api.onchange("partner_id", "filter_type", "search_ref")
    def _onchange_partner_id(self):
        if not self.partner_id:
            self.line_ids = [(5, 0, 0)]
            return

        lines = []
        
        # 1. Fetch Posted Bill/Invoice Lines
        if self.filter_type in ('all', 'bill'):
            move_types = ["in_invoice"]
            if self.move_id.move_type == "out_refund":
                move_types = ["out_invoice"]
    
            domain = [
                ("partner_id", "=", self.partner_id.id),
                ("move_id.move_type", "in", move_types),
                ("move_id.state", "=", "posted"),
                ("display_type", "=", "product"),
                ("quantity", ">", 0),
            ]
            if self.search_ref:
                domain.append("|")
                domain.append(("move_id.name", "ilike", self.search_ref))
                domain.append(("name", "ilike", self.search_ref))
                
            move_lines = self.env["account.move.line"].search(domain)
            
            for ml in move_lines:
                lines.append((0, 0, {
                    "source_type": "bill",
                    "bill_line_id": ml.id,
                    "product_id": ml.product_id.id,
                    "quantity": ml.quantity,
                    "price_unit": ml.price_unit,
                    "name": f"{ml.move_id.name}: {ml.name}",
                }))

        # 2. Fetch Done Return Picking Lines
        if self.filter_type in ('all', 'return'):
            domain = [
                ("picking_id.partner_id", "=", self.partner_id.id),
                ("picking_id.state", "=", "done"),
                ("origin_returned_move_id", "!=", False),
                ("state", "=", "done"),
            ]
            
            if self.move_id.move_type == "out_refund":
                # For Sales Return, it's incoming from customer.
                domain.append(("picking_id.picking_type_id.code", "=", "incoming"))
            else:
                # For Purchase Return, it's outgoing to vendor.
                domain.append(("picking_id.picking_type_id.code", "=", "outgoing"))
                
            if self.search_ref:
                domain.append("|")
                domain.append(("picking_id.name", "ilike", self.search_ref))
                domain.append(("product_id.name", "ilike", self.search_ref))
                
            return_moves = self.env["stock.move"].search(domain)
    
            for rm in return_moves:
                # Find price from PO/SO if available
                price_unit = rm.product_id.standard_price
                if rm.purchase_line_id:
                    price_unit = rm.purchase_line_id.price_unit
                elif rm.sale_line_id:
                    price_unit = rm.sale_line_id.price_unit
                
                # Automation: Check for linked Product Transform
                name = f"{rm.picking_id.name}: {rm.product_id.display_name}"
                transform = self.env["product.transform"].search([
                    ("picking_id", "=", rm.picking_id.id)
                ], limit=1)
                if transform:
                    name += f" (Transformed: {transform.name})"
    
                lines.append((0, 0, {
                    "source_type": "return",
                    "stock_move_id": rm.id,
                    "product_id": rm.product_id.id,
                    "quantity": rm.product_uom_qty,
                    "price_unit": price_unit,
                    "name": name,
                }))

        self.line_ids = [(5, 0, 0)] + lines

    def action_confirm(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered(lambda l: l.is_selected)
        if not selected_lines:
            raise UserError(_("Please select at least one line."))

        invoice_lines = []
        return_pickings = self.env["stock.picking"]
        for line in selected_lines:
            vals = {
                "display_type": "product",
                "product_id": line.product_id.id,
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "name": line.name,
            }
            if line.source_type == "bill" and line.bill_line_id:
                vals.update({
                    "tax_ids": [(6, 0, line.bill_line_id.tax_ids.ids)],
                    "account_id": line.bill_line_id.account_id.id,
                })
            elif line.source_type == "return" and line.stock_move_id:
                rm = line.stock_move_id
                return_pickings |= rm.picking_id
                vals.update({
                    "return_picking_id": rm.picking_id.id,
                    "return_stock_move_id": rm.id,
                })
                if rm.purchase_line_id and rm.purchase_line_id.taxes_id:
                    vals.update({"tax_ids": [(6, 0, rm.purchase_line_id.taxes_id.ids)]})
                elif rm.sale_line_id and rm.sale_line_id.tax_id:
                    vals.update({"tax_ids": [(6, 0, rm.sale_line_id.tax_id.ids)]})
                    
                # Ensure account is set based on the move type and product
                accounts = line.product_id.product_tmpl_id.get_product_accounts()
                if self.move_id.move_type in ('out_invoice', 'out_refund'):
                    vals.update({"account_id": accounts.get('income').id if accounts.get('income') else False})
                else:
                    vals.update({"account_id": accounts.get('expense').id if accounts.get('expense') else False})

            invoice_lines.append((0, 0, vals))

        write_vals = {"invoice_line_ids": invoice_lines}
        if return_pickings:
            write_vals["return_picking_ids"] = [Command.set((self.move_id.return_picking_ids | return_pickings).ids)]
        self.move_id.write(write_vals)
        return {"type": "ir.actions.act_window_close"}


class AccountMoveConsolidatedReversalLine(models.TransientModel):
    _name = "account.move.consolidated.reversal.line"
    _description = "Consolidate Bills and Returns Wizard Line"

    wizard_id = fields.Many2one("account.move.consolidated.reversal")
    is_selected = fields.Boolean(string="Select")
    source_type = fields.Selection([
        ("bill", "Vendor Bill"),
        ("return", "Return Picking")
    ], string="Type", readonly=True)
    
    bill_line_id = fields.Many2one("account.move.line", string="Bill Line", readonly=True)
    stock_move_id = fields.Many2one("stock.move", string="Stock Move", readonly=True)
    
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    name = fields.Char(string="Description", readonly=True)
    quantity = fields.Float(string="Quantity")
    price_unit = fields.Float(string="Price Unit")
