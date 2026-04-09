from odoo import _, models


class CrmClaimEpt(models.Model):
    _inherit = "crm.claim.ept"

    @staticmethod
    def check_move_qty(move_id, claim_lines):
        if move_id.quantity > 0:
            claim_lines.append((0, 0, {
                'product_id': move_id.product_id.id,
                'quantity': move_id.quantity,
                'product_uom_id': move_id.product_uom.id,
                'move_id': move_id.id
            }))
        return claim_lines

    @staticmethod
    def check_retutn_qty(returned_qty, move_id, claim_lines):
        if returned_qty < move_id.quantity:
            qty = move_id.quantity - returned_qty
            if qty > 0:
                claim_lines.append((0, 0, {
                    'product_id': move_id.product_id.id,
                    'quantity': qty,
                    'product_uom_id': move_id.product_uom.id,
                    'move_id': move_id.id
                }))
        return claim_lines

    @staticmethod
    def prepare_values_for_return_picking_line(line, return_picking_wizard, move_id):
        quantity = line.quantity
        if line.product_uom_id and line.product_uom_id != move_id.product_uom:
            quantity = line.product_uom_id._compute_quantity(line.quantity, move_id.product_uom)

        return {
            'product_id': line.product_id.id,
            'quantity': quantity,
            'wizard_id': return_picking_wizard.id,
            'move_id': move_id.id
        }

    def create_move_lines(self, new_picking_id):
        self.write({'return_picking_id': new_picking_id})
        for claim_line in self.claim_line_ids:
            return_quantity = claim_line.quantity
            move_uom = claim_line.move_id.product_uom

            if claim_line.product_uom_id and claim_line.product_uom_id != move_uom:
                return_quantity = claim_line.product_uom_id._compute_quantity(claim_line.quantity, move_uom)

            if claim_line.serial_lot_ids:
                claim_line_by_lots = {}
                done_move_lines = claim_line.move_id.mapped('move_line_ids').filtered(
                    lambda line, claim_line=claim_line: line.product_id.id == claim_line.product_id.id)
                for done_move in done_move_lines:
                    move_line_lot = done_move.lot_id
                    done_qty = done_move.qty_done
                    if not claim_line_by_lots.get(move_line_lot, False):
                        claim_line_by_lots.update({move_line_lot: done_qty})
                    else:
                        existing_amount = claim_line_by_lots.get(move_line_lot, {})
                        claim_line_by_lots.update({move_line_lot: existing_amount + done_qty})

                processed_qty_by_lots = 0.0
                for serial_lot_id in claim_line.serial_lot_ids:
                    lot_quantity = claim_line_by_lots.get(serial_lot_id, 0.0)
                    processed_qty_by_lots += lot_quantity

                if return_quantity > processed_qty_by_lots:
                    from odoo.exceptions import UserError
                    raise UserError(_("Please select proper Lots/Serial Numbers for product %s.") % claim_line.product_id.name)

                update_number_lines = self.return_picking_id.move_ids.mapped('move_line_ids').filtered( \
                    lambda line,
                           claim_line=claim_line: line.product_id.id == claim_line.product_id.id and line.lot_id.id not in claim_line.serial_lot_ids.ids and line.qty_done == 0.0)

                return_move_lines = self.return_picking_id.move_ids.mapped('move_line_ids').filtered( \
                    lambda line, claim_line=claim_line: line.product_id.id == claim_line.product_id.id and line.qty_done == 0.0)

                for serial_lot_id in claim_line.serial_lot_ids:
                    return_lot_move_lines = return_move_lines.filtered(
                        lambda line, serial_lot_id=serial_lot_id: line.lot_id.id == serial_lot_id.id and line.qty_done == 0.0)
                    if not return_lot_move_lines and update_number_lines:
                        update_number_lines = update_number_lines.filtered(lambda line: line.qty_done == 0.0)
                        return_move_line = update_number_lines[0]
                        return_move_line.write({'lot_id': serial_lot_id.id})
                    else:
                        return_move_line = return_lot_move_lines[0]
                    quantity = claim_line_by_lots.get(return_move_line.lot_id)

                    if quantity >= return_quantity:
                        return_move_line.write({'qty_done': return_quantity})
                        break
                    return_quantity -= quantity
                    return_move_line.write({'qty_done': quantity})
            else:
                return_move_lines = self.return_picking_id.move_ids.mapped('move_line_ids').filtered(
                    lambda line, claim_line=claim_line: line.product_id.id == claim_line.product_id.id and line.qty_done == 0.0)
                if return_move_lines:
                    return_move_line = return_move_lines[0]
                    return_move_line.write({'qty_done': return_quantity})
        return self.return_picking_id

    def prepare_refund_invoice_dict(self, line, refund_invoice_ids, invoice_line, process_qty):
        refund_invoice_ids = super().prepare_refund_invoice_dict(line, refund_invoice_ids, invoice_line, process_qty)
        vals_list = refund_invoice_ids.get(invoice_line.move_id.id)
        if vals_list:
            last_vals = vals_list[-1]
            if line.price_unit:
                price = line.price_unit
                if line.product_uom_id != invoice_line.product_uom_id:
                    price = line.product_uom_id._compute_price(line.price_unit, invoice_line.product_uom_id)
                last_vals['price'] = price
        return refund_invoice_ids
