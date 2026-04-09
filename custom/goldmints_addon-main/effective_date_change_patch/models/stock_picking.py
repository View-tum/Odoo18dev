from odoo import api, fields, models
from odoo.addons.effective_date_change.models import update_effective


def silent_button_validate(self):
    return super(update_effective.UpdateEffective, self).button_validate()

update_effective.UpdateEffective.button_validate = silent_button_validate


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for picking in self:
            if picking.date_of_transfer:
                selected_date = picking.date_of_transfer
            else:
                selected_date = fields.Datetime.now()

            picking.date_done = selected_date

            self.env.cr.execute("UPDATE stock_valuation_layer SET create_date = (%s) WHERE description LIKE (%s)", [
                                selected_date, str(picking.name + "%")])

            for stock_move_line in self.env['stock.move.line'].search([('reference', 'ilike', str(picking.name + "%"))]):
                stock_move_line.date = selected_date

            for stock_move in self.env['stock.move'].search([('reference', 'ilike', str(picking.name + "%"))]):
                stock_move.date = selected_date

            self.env.cr.execute("UPDATE account_move_line SET date = (%s) WHERE ref SIMILAR TO %s", [
                                selected_date, str(picking.name + "%")])

            self.env.cr.execute("UPDATE account_move set date = (%s) WHERE ref SIMILAR TO %s", [
                                selected_date, str(picking.name + "%")])

            system_default_currency = picking.company_id.currency_id.id
            purchase_order = picking.purchase_id

            if picking.picking_type_id.code == 'internal':
                pass

            elif picking.picking_type_id.code == 'outgoing':
                if not picking.return_id:
                    journal_entry_ids = []

                    for line in picking.move_ids_without_package:
                        product_id = line.product_id.id
                        valuation_layers = self.env['stock.valuation.layer'].search([
                            ('product_id', '=', product_id),
                            ('reference', 'ilike', str(picking.name + "%"))
                        ])

                        if valuation_layers:
                            for valuation_layer in valuation_layers:
                                account_move = valuation_layer.account_move_id

                                if account_move:
                                    journal_entry_ids.append(account_move.id)

                                    self.env.cr.execute("""
                                        UPDATE account_move
                                            SET name = '/',
                                            state = 'draft',
                                            date = %s
                                            WHERE id = %s
                                            """, (selected_date, account_move.id))

                                    self.env.cr.commit()

                        line.product_id._run_fifo_vacuum(picking.company_id)

                    if journal_entry_ids:
                        for journal_entry_id in set(journal_entry_ids):
                            if not journal_entry_id:
                                continue
                            account_move = self.env['account.move'].sudo().browse(journal_entry_id)
                            if account_move.exists():
                                # Core re-sequencing via action_post()
                                account_move.action_post()
                        self.env.cr.commit()

            elif picking.picking_type_id.code == 'incoming':
                if not picking.return_id:
                    if picking.picking_type_id.code == 'incoming' and int(purchase_order.currency_id.id) != system_default_currency:

                        stock_move_id = None
                        duplicate_product = []
                        seen_product_ids = []

                        for product in purchase_order.order_line:
                            product_id = product.product_id.id

                            if product_id in seen_product_ids and product_id not in duplicate_product:
                                duplicate_product.append(product_id)
                            else:
                                seen_product_ids.append(product_id)

                        po_details = {}
                        po_details_duplicate_product = []

                        for product in purchase_order.order_line:
                            product_id = product.product_id.id
                            if product_id not in po_details and product_id not in duplicate_product:
                                po_details[product_id] = {
                                    'quantity': product.product_qty,
                                    'price_subtotal': product.price_subtotal,
                                    'price_unit': product.price_unit
                                }
                            elif product_id in duplicate_product:
                                po_details_duplicate_product.append({
                                    'product_id': product_id,
                                    'quantity': product.product_qty,
                                    'price_subtotal': product.price_subtotal,
                                    'price_unit': product.price_unit
                                })

                        price_unit = {}
                        rate = picking._get_purchase_currency_rate_for_valuation(purchase_order, selected_date)

                        journal_entry_ids = []
                        for line in picking.move_ids_without_package:
                            if stock_move_id is None:
                                stock_move_id = line.id
                            product_id = line.product_id.id
                            line_qty = line.quantity if line.quantity > 0 else line.product_uom_qty

                            if product_id in po_details:
                                po_product = po_details[product_id]
                                po_qty = po_product['quantity']
                                unit_price = po_product['price_unit']
                                if line_qty <= po_qty:
                                    total_value = unit_price * line_qty * rate
                                    price_unit[product_id] = total_value
                                    po_details[product_id]['quantity'] -= line_qty
                                else:
                                    unit_value = po_product['price_subtotal'] * rate
                                    price_unit[product_id] = unit_value
                                    line_qty -= po_qty
                                    po_details[product_id]['quantity'] = 0

                        for line in picking.move_ids_without_package:
                            product_id = line.product_id.id

                            if product_id not in duplicate_product:
                                valuation_layers = self.env['stock.valuation.layer'].search([
                                    ('product_id', '=', product_id),
                                    ('description', 'ilike', str(picking.name + "%"))
                                ])

                                for valuation_layer in valuation_layers:
                                    if product_id in price_unit:
                                        unit_value = price_unit[product_id]
                                        unit_value_new = (unit_value / valuation_layer.quantity) * valuation_layer.quantity
                                        valuation_layer.unit_cost = unit_value / valuation_layer.quantity
                                        valuation_layer.value = (unit_value / valuation_layer.quantity) * valuation_layer.quantity
                                        valuation_layer.remaining_value = valuation_layer.remaining_qty * (unit_value / valuation_layer.quantity)

                                        journal_entry = valuation_layer.account_move_id
                                        if journal_entry:
                                            for journal in journal_entry:
                                                for move_line in journal.line_ids:
                                                    with self.env.cr.savepoint():
                                                        move_line.with_context(check_move_validity=False).write({
                                                            'debit': unit_value_new if move_line.debit > 0 else move_line.debit,
                                                            'credit': unit_value_new if move_line.credit > 0 else move_line.credit,
                                                        })

                                                journal_entry_ids.append(journal.id)
                                                self.env.cr.execute("""
                                                    UPDATE account_move
                                                    SET state = 'draft',
                                                        name = '/',
                                                        date = %s
                                                    WHERE id = %s
                                                    """, (selected_date, journal.id))
                                                self.env.cr.commit()

                            elif product_id in duplicate_product:
                                valuation_layers = self.env['stock.valuation.layer'].search([
                                    ('product_id', '=', product_id),
                                    ('reference', 'ilike', str(picking.name + "%"))
                                ])
                                for valuation_layer in valuation_layers:
                                    if valuation_layer.account_move_id:
                                        valuation_layer.account_move_id.sudo().button_draft()
                                        valuation_layer.account_move_id.sudo().unlink()
                                    valuation_layer.sudo().unlink()

                        for product in po_details_duplicate_product:
                            if product['quantity'] > 0:
                                unit_cost = (product['price_subtotal'] / product['quantity']) * rate
                            else:
                                unit_cost = 0

                            new_valuation_layer = self.env['stock.valuation.layer'].sudo().create({
                                'product_id': product['product_id'],
                                'quantity': product['quantity'],
                                'remaining_qty': product['quantity'],
                                'unit_cost': unit_cost,
                                'value': product['price_subtotal'] * rate,
                                'company_id': picking.company_id.id,
                                'stock_move_id': stock_move_id,
                            })

                            self.env.cr.execute("""
                                UPDATE stock_valuation_layer SET create_date = %s WHERE id = %s
                            """, (picking.date_of_transfer, new_valuation_layer.id))

                            prod = self.env['product.product'].browse(product['product_id'])
                            product_category = prod.product_tmpl_id.categ_id
                            journal_id = product_category.property_stock_journal.id
                            interim_stock_account_id = product_category.property_stock_account_input_categ_id.id
                            inventory_account_id = product_category.property_stock_valuation_account_id.id

                            move_vals = {
                                'ref': picking.name,
                                'journal_id': journal_id,
                                'date': picking.date_of_transfer.date(),
                                'company_id': picking.company_id.id,
                                'line_ids': [
                                    (0, 0, {
                                        'name': f"{picking.name} - {prod.name}",
                                        'account_id': interim_stock_account_id,
                                        'partner_id': picking.partner_id.id,
                                        'debit': 0.0,
                                        'credit': product['price_subtotal'] * rate,
                                        'company_id': picking.company_id.id,
                                    }),
                                    (0, 0, {
                                        'name': f"{picking.name} - {prod.name}",
                                        'account_id': inventory_account_id,
                                        'partner_id': picking.partner_id.id,
                                        'debit': product['price_subtotal'] * rate,
                                        'credit': 0.0,
                                        'company_id': picking.company_id.id,
                                    })
                                ]
                            }
                            journal_entry = self.env['account.move'].sudo().create(move_vals)
                            journal_entry.sudo().action_post()
                            new_valuation_layer.account_move_id = journal_entry.id
                            journal_entry_ids.append(journal_entry.id)

                        if journal_entry_ids:
                            for journal_entry_id in set(journal_entry_ids):
                                if not journal_entry_id:
                                    continue
                                account_move = self.env['account.move'].sudo().browse(journal_entry_id)
                                if account_move.exists():
                                    account_move.action_post()
                        self.env.cr.commit()
                        if hasattr(self, 'action_update_valuation_layers'):
                            self.action_update_valuation_layers()

            self.env.cr.commit()
            for move in picking.move_ids_without_package:
                if move.lot_ids:
                    self.env.cr.execute("""
                        UPDATE stock_lot SET create_date = %s WHERE id IN %s
                    """, (picking.date_done, tuple(move.lot_ids.ids)))

                    valuation_layers = self.env['stock.valuation.layer'].search([
                        ('product_id', '=', move.product_id.id),
                        ('reference', 'ilike', picking.name + "%")
                    ])
                    for valuation_layer in valuation_layers:
                        if not valuation_layer.lot_id:
                            valuation_layer.lot_id = move.lot_ids[0]
                            self.env.cr.execute("""
                                UPDATE stock_lot
                                SET standard_price = jsonb_build_object('1', %s::numeric)
                                WHERE id IN %s
                            """, (valuation_layer.unit_cost, tuple(move.lot_ids.ids)))
        return res
