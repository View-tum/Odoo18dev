from odoo import api, fields, models, _
from datetime import datetime
from odoo import Command

from docutils.nodes import title


class ThecoolReceiveImport(models.Model):
    _name = "thecool.receive.import"

    # @api.depends('his_billing_type', 'his_document_unique_number', 'his_order_item_code')
    # def _compute_display_name(self):
    #     for rec in self:
    #         if rec.his_billing_type and rec.his_document_unique_number:
    #             rec.display_name = f"[{rec.his_billing_type}] {rec.his_document_unique_number} {rec.his_order_item_code}"
    #         else:
    #             rec.display_name = f"{rec.his_document_unique_number} {rec.his_order_item_code}"

    # ===== information import =====
    date_file = fields.Datetime(string='Date File', default=datetime.today())
    import_state = fields.Selection(
        selection=[
            ("draft", "Pre-Import"),
            ("import", "Imported"),
            ("fail", "Fail"),
            ("cancel", "Cancelled"),
        ],
        string="Import Status",
        required=True,
        default="draft",
    )
    date_import = fields.Datetime(string='Date Import')
    error_log = fields.Text(string="Error log", default="")

    # ===== Data import =====
    state = fields.Char(string='State')
    reference = fields.Char(string='Reference')
    old_system_number = fields.Char(string='Old System Number')
    contact_id = fields.Integer(string='Contact')
    picking_type = fields.Char(string='Picking Type')
    source_location = fields.Char(string='Source Location')
    destination_location = fields.Char(string='Destination Location')
    scheduled_date = fields.Datetime(string='Scheduled Date')
    source_document = fields.Char(string='Source Document')
    effective_date = fields.Datetime(string='Effective Date')
    date_done = fields.Datetime(string='Date Done')
    procurement_group = fields.Char(string='Procurement Group')
    line_number = fields.Integer(string='Line number')
    line_product_id = fields.Integer(string='Line Product ID')
    line_scheduled_date = fields.Datetime(string='Line Scheduled Date')
    line_qty = fields.Float(string='Line Qty')
    line_state = fields.Char(string='Line State')
    line_purchase_line_id = fields.Integer(string='Line Purchase ID')
    line_sale_line_id = fields.Integer(string='Line Sale ID')

    def import_data(self):
        print("===== Test import data =====")
        success_trans = 0
        fail_trans = 0
        try:
            for row in self:

                #  Check Import State
                if row.import_state in ('draft', 'fail'):
                    print("===== 1. import_state:", row.import_state, "=====")

                    stock_picking = self.env["stock.picking"].sudo().search([("name", "=", row.reference)])

                    state = row.state
                    reference = row.reference
                    old_system_number = row.old_system_number
                    if row.contact_id:
                        contact_id = row.contact_id
                    else:
                        contact_id = None

                    # picking_type = self.env["stock.picking.type"].sudo().search([("name", "=", row.picking_type)])
                    # if picking_type:
                    #     picking_type_id = picking_type[0].id
                    picking_type_id = 1

                    source_location = self.env["stock.location"].sudo().search([("name", "=", row.source_location)])
                    if source_location:
                        source_location_id = source_location[0].id

                    destination_location = self.env["stock.location"].sudo().search(
                        [("name", "=", row.destination_location)])
                    if destination_location:
                        destination_location_id = destination_location[0].id

                    scheduled_date = row.scheduled_date
                    source_document = row.source_document
                    effective_date = row.effective_date
                    date_done = row.date_done

                    print("row.procurement_group:", row.procurement_group)
                    if row.procurement_group:

                        procurement_group = self.env["procurement.group"].sudo().search(
                            [("name", "=", row.procurement_group)])

                        if not procurement_group:
                            print("--- create procurement_group ---")
                            self.env["procurement.group"].sudo().create(
                                {
                                    "name": row.procurement_group,
                                }
                            )
                            procurement_group = self.env["procurement.group"].sudo().search(
                                [("name", "=", row.procurement_group)])

                            procurement_group_id = procurement_group[0].id
                            print("procurement_group:", procurement_group_id)
                        else:
                            procurement_group_id = procurement_group[0].id
                    else:
                        procurement_group_id = ''


                    line_number = row.line_number
                    line_product_id = row.line_product_id
                    line_scheduled_date = row.line_scheduled_date
                    line_qty = row.line_qty
                    line_state = row.line_state
                    line_purchase_line_id = row.line_purchase_line_id
                    # line_sale_line_id = row.line_sale_line_id

                    line_purchase_line = self.env["purchase.order.line"].sudo().search([("old_line_id", "=", row.line_purchase_line_id)])
                    if line_purchase_line:
                        purchase_line_id = line_purchase_line[0].id
                    else:
                        purchase_line_id = None

                    print("line_state:", line_state)

                    print("line_number:", line_number)
                    print("line_product_id:", line_product_id)
                    print("line_scheduled_date:", line_scheduled_date)
                    print("line_qty:", line_qty)
                    print("line_state:", line_state)

                    # ----- Check stock picking -----
                    if not stock_picking:
                        print("----- Create picking -----")
                        print("name:", reference)
                        print("old_number:", old_system_number)
                        print("partner_id:", contact_id)
                        print("picking_type_id:", picking_type_id)
                        print("location_dest_id:", destination_location_id)
                        print("scheduled_date:", scheduled_date)
                        print("date_done:", date_done)
                        print("origin:", source_document)
                        print("date_of_transfer:", effective_date)
                        print("group_id:", procurement_group_id)
                        print("------------------------")
                        print("number:", line_number)
                        print("product_id:", line_product_id)
                        print("date:", line_scheduled_date)
                        print("product_uom_qty:", line_qty)

                        stock_picking = self.env["stock.picking"].sudo().create(
                            {
                                "name": reference,
                                "old_number": old_system_number,
                                "partner_id": contact_id,
                                "picking_type_id": picking_type_id,
                                "location_dest_id": destination_location_id,
                                "scheduled_date": scheduled_date,
                                "date_done": date_done,
                                "origin": source_document,
                                "date_of_transfer": effective_date,
                                "group_id": procurement_group_id,
                            }
                        )
                        print("stock_picking.id:", stock_picking[0].id)

                        product = self.env["product.product"].sudo().search(
                            [("id", "=", line_product_id)])

                        self.env["stock.move"].sudo().create(
                            {
                                "picking_id": stock_picking[0].id,
                                "number": line_number,
                                "product_id": line_product_id,
                                "name": product[0].product_tmpl_id.name,
                                "date": line_scheduled_date,
                                "product_uom_qty": line_qty,
                                "purchase_line_id": purchase_line_id,
                            }
                        )

                        print("stock_picking:",stock_picking)
                        row.import_state = 'import'
                        row.date_import = datetime.now()
                        row.error_log = ""
                        success_trans += 1

                    else:
                        print("----- Update picking -----")
                        print("stock_picking.id:", stock_picking[0].id)

                        product = self.env["product.product"].sudo().search(
                            [("id", "=", line_product_id)])

                        self.env["stock.move"].sudo().create(
                            {
                                "picking_id": stock_picking[0].id,
                                "number": line_number,
                                "product_id": line_product_id,
                                "name": product[0].product_tmpl_id.name,
                                "date": line_scheduled_date,
                                "product_uom_qty": line_qty,
                                "purchase_line_id": purchase_line_id,
                            }
                        )

                        print("stock_picking:",stock_picking)
                        row.import_state = 'import'
                        row.date_import = datetime.now()
                        row.error_log = ""
                        success_trans += 1

            if fail_trans == 0:
                notification_type = 'success'
            else:
                notification_type = 'danger'

            status = 'Success = %s transaction.\nFail = %s transaction.' % (success_trans, fail_trans)
            _title = 'Import Data.'

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'type': notification_type,
                    'sticky': True,
                    'message': status,
                    'title': _title
                }
            }

        except Exception as e:
            status = str(e)
            notification_type = 'danger'

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'type': notification_type,
                    'sticky': True,
                    'message': status,
                    'title': 'Import File'
                }
            }

    #
    # def import_data(self):
    #     print("===== import_data =====")
    #     i = 1
    #     invoices = self
    #     invoice_lines = self
    #     his_document_unique_number = ''
    #
    #     for row in invoices:
    #         # ===== Check Duplicate his_document_unique_number and import_state =====
    #         if row.his_document_unique_number != his_document_unique_number and row.import_state in ('draft', 'fail'):
    #             print("======================")
    #             print("Row Num:", i)
    #             print("======================")
    #             i += 1
    #             his_document_unique_number = row.his_document_unique_number
    #             print("doc_no:", his_document_unique_number)
    #
    #             # ===== Check document in account move =====
    #             account_move = self.env["account.move"].sudo().search(
    #                 [("his_document_unique_number", "=", his_document_unique_number)])
    #
    #             print("=================================")
    #             print("Check account_move:", account_move)
    #             print("=================================")
    #
    #             if not account_move:
    #
    #                 # ===== Check Journal & Partner =====
    #                 journal = self.env["his.billing.type.journal"].sudo().search([("name", "=", row.his_billing_type)])
    #                 partner = self.env["res.partner"].sudo().search([("ref", "=", row.his_payor_office_code)])
    #
    #                 print("Check journal:", journal)
    #                 print("Check partner:", partner)
    #
    #                 # ===== Check journal set in HIS Billing type is not bank =====
    #                 if journal and partner:
    #
    #                     print("Check journal:", journal[0].journal_id.id)
    #                     print("Check partner:", partner[0].id)
    #
    #                     invoice_date = datetime.strptime(row.his_document_print_date, '%d%m%Y').date()
    #
    #                     print("Check invoice_date:", invoice_date)
    #
    #                     # ----- Check Invoice Lines -----
    #                     product_list = []
    #                     import_list = []
    #                     for line in invoice_lines:
    #                         if line.his_document_unique_number != his_document_unique_number and line.import_state in (
    #                                 'draft',
    #                                 'fail'):
    #                             product = self.env["product.template"].sudo().search(
    #                                 [("default_code", "=", line.his_order_item_code)])
    #                             product_list.append(Command.create(
    #                                 {
    #                                     'product_id': product[0].id,
    #                                     'price_unit': line.his_order_item_amount_afdiscount,
    #                                     'quantity': line.his_quantity,
    #                                     'his_ids': line.id,
    #                                 }
    #                             ))
    #                             line.import_state = "import"
    #                             # import_list.append(line.id)
    #
    #                     print("Check product_list:", product_list)
    #                     print("Check import_list:", import_list)
    #
    #                     # ----- Create new account move -----
    #                     account_move.create(
    #                         {
    #                             "partner_id": partner[0].id,
    #                             "invoice_date": invoice_date,
    #                             "journal_id": journal[0].journal_id.id,
    #
    #                             "his_bu": row.his_bu,
    #                             "his_billing_type": row.his_billing_type,
    #                             "his_document_unique_number": row.his_document_unique_number,
    #                             "his_document_number": row.his_document_number,
    #                             "his_document_print_date": invoice_date,
    #                             "his_payor_office_code": row.his_payor_office_code,
    #                             "his_payor_office_description": row.his_payor_office_description,
    #                             "his_patient_unique_number": row.his_patient_unique_number,
    #                             "his_hn": row.his_hn,
    #                             "his_episode_unique_number": row.his_episode_unique_number,
    #                             "his_en": row.his_en,
    #                             "his_title_name": row.his_title_name,
    #                             "his_first_name": row.his_first_name,
    #                             "his_middle_name": row.his_middle_name,
    #                             "his_last_name": row.his_last_name,
    #                             "his_episode_type": row.his_episode_type,
    #                             "his_episode_location_code": row.his_episode_location_code,
    #                             "his_episode_location_description": row.his_episode_location_description,
    #                             'invoice_line_ids': product_list,
    #
    #                         }
    #                     )
    #
    #                     # })
    #
    #                 # else:
    #                 # ----- Update record-----
    #                 # ===== Check Journal ID =====
    #
    #                 # for row in headers:
    #                 #
    #                 #     if doc_no != row.his_document_unique_number and row.import_state in ('draft','fail'):
    #                 #
    #                 #         doc_no = row.his_document_unique_number
    #                 #         print("-------------------------------------------")
    #                 #         print("Row Num:",i)
    #                 #         print("-------------------------------------------")
    #                 #         i += 1
    #                 #
    #                 #         # # ===== Check Billing Type =====
    #                 #         # if row.his_billing_type == 'NOT PRINT':
    #                 #         #     doc_number = row.his_document_unique_number
    #                 #         # else:
    #                 #         #     doc_number = row.his_document_number
    #                 #
    #                 #         # ===== Check Journal ID =====
    #                 #         journal = self.env["his.billing.type.journal"].sudo().search([("name", "=", row.his_billing_type)])
    #                 #         if journal[0].journal_id:
    #                 #             journal_id = journal[0].journal_id
    #                 #
    #                 #             # ===== Check new document =====
    #                 #             account_move = self.env["account.move"].sudo().search([("his_doc_uniq_num", "=", row.his_document_unique_number)])
    #                 #             # import_lines = lines.search([("his_doc_uniq_num", "=", row.his_document_unique_number),("import_state", "in", ('draft', 'fail'))])
    #                 #
    #                 #
    #                 #             print("account_move:", account_move)
    #                 #
    #                 #             if not account_move:
    #                 #                 print("--- Create document ---")
    #                 #                 customer = self.env["res.partner"].sudo().search([("ref", "=", row.his_payor_office_code)])
    #                 #
    #                 #                 if customer:
    #                 #                     partner_id = customer[0].id
    #                 #                     invoice_date = datetime.strptime(row.his_print_date, '%d%m%Y')
    #                 #
    #                 #                     # --- follow customer ---
    #                 #                     # payment_term_id = row.his_payment_mode_type
    #                 #
    #                 #                     product_list = []
    #                 #                     for line in lines:
    #                 #                         if doc_no != line.his_document_unique_number and line.import_state in ('draft', 'fail'):
    #                 #                             product = self.env["product.template"].sudo().search([("default_code", "=", line.his_order_item_code)])
    #                 #                             product_list.append(Command.create(
    #                 #                                 {
    #                 #                                     'product_id': product[0].id,
    #                 #                                     'price_unit': line.his_order_item_amount_afdiscount,
    #                 #                                     'his_quantity': line.his_quantity,
    #                 #                                 }
    #                 #                             ))
    #                 #
    #                 #                     print("product_list:", product_list)
    #                 #
    #                 #                     account_move.sudo().create(
    #                 #                         {
    #                 #                             "partner_id": partner_id,
    #                 #                             "invoice_date": invoice_date,
    #                 #                             "journal_id": journal_id,
    #                 #                             "his_bu": row.his_bu,
    #                 #                             "his_billing_type": row.his_billing_type,
    #                 #                             "his_doc_no": row.his_document_number,
    #                 #                             "his_print_date": row.his_print_date,
    #                 #
    #                 #                             "his_payor_office_code": row.his_payor_office_code,
    #                 #                             "his_payor_office_description": row.his_payor_office_description,
    #                 #
    #                 #                             "his_patient_unique_number": row.his_patient_unique_number,
    #                 #                             "his_hn": row.his_hn,
    #                 #                             "his_episode_unique_number": row.his_episode_unique_number,
    #                 #
    #                 #                             "his_en": row.his_en,
    #                 #                             "his_title": row.his_title,
    #                 #                             "his_name": row.his_name,
    #                 #                             "his_first_name": row.his_first_name,
    #                 #                             "his_middle_name": row.his_middle_name,
    #                 #                             "his_last_name": row.his_last_name,
    #                 #
    #                 #                             "his_episode_type": row.his_episode_type,
    #                 #                             "his_episode_location_code": row.his_episode_location_code,
    #                 #                             "his_episode_location_description": row.his_episode_location_description,
    #                 #                             'invoice_line_ids': product_list,
    #                 #
    #                 #                         }
    #                 #                     )
    #                 #
    #                 #
    #                 #                 else:
    #                 #                     print("Error! The Document is not Customer.")
    #                 #
    #                 #
    #                 #             else:
    #                 #                 print("--- Update document ---")
    #                 #                 # account_move_line = self.env["account.move.line"]
    #                 #                 # account_move_line.create(
    #                 #                 #     {
    #                 #                 #
    #                 #                 #     }
    #                 #                 # )
    #                 #                 product_list = []
    #                 #                 for line in lines:
    #                 #                     if doc_no != line.his_document_unique_number and line.import_state in ('draft', 'fail'):
    #                 #                         product = self.env["product.template"].sudo().search(
    #                 #                             [("default_code", "=", line.his_order_item_code)])
    #                 #                         product_list.append(Command.create(
    #                 #                             {
    #                 #                                 'product_id': product[0].id,
    #                 #                                 'price_unit': line.his_order_item_amount_afdiscount,
    #                 #                                 'his_quantity': line.his_quantity,
    #                 #                             }
    #                 #                         ))
    #                 #
    #                 #                 print("product_list:", product_list)
    #                 #
    #                 #                 account_move.sudo().write(
    #                 #                     {
    #                 #                         'invoice_line_ids': product_list,
    #                 #                     }
    #                 #                 )
    #                 #
    #                 #
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             # # ===== Create INVOICE ใบแจ้งหนี้ =====
    #                 #             # if row.his_billing_type == 'INVOICE':
    #                 #             #     # ----- INVOICE Header -----
    #                 #             #     print("Billing Type: INVOICE")
    #                 #             #     print("Doc Number:", doc_number)
    #                 #             #     print("journal_id:", journal[0].journal_id.name)
    #                 #             #
    #                 #             #
    #                 #             #     # ----- INVOICE Lines -----
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             # # ===== Create RECEIPT ใบเสร็จรับเงิน =====
    #                 #             # if row.his_billing_type == 'RECEIPT':
    #                 #             #     # ----- RECEIPT Header -----
    #                 #             #     print("Billing Type: RECEIPT")
    #                 #             #     print("Doc Number:", doc_number)
    #                 #             #     print("journal_id:", journal[0].journal_id.name)
    #                 #             #
    #                 #             #     # ----- RECEIPT Lines -----
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             # # ===== Create DEPOSIT มัดจำ =====
    #                 #             # if row.his_billing_type == 'DEPOSIT':
    #                 #             #     # ----- DEPOSIT Header -----
    #                 #             #     print("Billing Type: DEPOSIT")
    #                 #             #     print("Doc Number:", doc_number)
    #                 #             #     print("journal_id:", journal[0].journal_id.name)
    #                 #             #     # ----- DEPOSIT Lines -----
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             # # ===== Create REFUND DEPOSIT คืนเงินมัดจำ =====
    #                 #             # if row.his_billing_type == 'REFUND DEPOSIT':
    #                 #             #     # ----- REFUND DEPOSIT Header -----
    #                 #             #     print("Billing Type: REFUND DEPOSIT")
    #                 #             #     print("Doc Number:", doc_number)
    #                 #             #     print("journal_id:", journal[0].journal_id.name)
    #                 #             #     # ----- REFUND DEPOSIT Lines -----
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             # # ===== Create NOT PRINT =====
    #                 #             # if row.his_billing_type == 'NOT PRINT':
    #                 #             #     # ----- NOT PRINT Header -----
    #                 #             #     print("Billing Type: NOT PRINT")
    #                 #             #     print("Doc Number:", doc_number)
    #                 #             #     print("journal_id:", journal[0].journal_id.name)
    #                 #             #     # ----- NOT PRINT Lines -----
    #                 #             #
    #                 #             #
    #                 #             # # ===== Create CANCELLED INVOICE =====
    #                 #             # if row.his_billing_type == 'CANCELLED INVOICE':
    #                 #             #     # ----- CANCELLED INVOICE Header -----
    #                 #             #     print("Billing Type: CANCELLED INVOICE")
    #                 #             #     print("Doc Number:", doc_number)
    #                 #             #     print("journal_id:", journal[0].journal_id.name)
    #                 #             #     # ----- CANCELLED INVOICE Lines -----
    #                 #             #
    #                 #             #
    #                 #             # # ===== Create CANCELLED RECEIPT =====
    #                 #             # if row.his_billing_type == 'CANCELLED RECEIPT':
    #                 #             #     # ----- CANCELLED RECEIPT Header -----
    #                 #             #     print("Billing Type: CANCELLED RECEIPT")
    #                 #             #     print("Doc Number:", doc_number)
    #                 #             #     print("journal_id:", journal[0].journal_id.name)
    #                 #             #     # ----- CANCELLED RECEIPT Lines -----
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #             #
    #                 #
    #                 #
