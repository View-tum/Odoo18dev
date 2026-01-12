from odoo import fields, models
import odoo


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ax_report_as_finish = fields.Char(string="Report as finished (AX)")
    ax_description = fields.Char(string="Description (AX)")
    ax_prod_id = fields.Char(string="Production ID (AX)")
    picking_type_sequence_code = fields.Char(
        related='picking_type_id.sequence_code',
        string='Picking Type Code',
        store=False
    )

class StockMove(models.Model):
    _inherit = "stock.move"

    ax_invent_trans = fields.Char(string="Invent Trans ID (AX)")


class TmpProdJournalTable(models.Model):
    _name = "tmp.prod.journal.table"

    ax_journal_id = fields.Char(string="Journal ID (AX)")
    ax_description = fields.Char(string="Description (AX)")
    ax_prod_id = fields.Char(string="Prod ID (AX)")
    ax_rec_id = fields.Char(string="Record ID (AX)")
    is_imported = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("imported", "Imported"),
            ("canceled", "Canceled"),
            ("error", "Error")
        ],
        default="draft",
    )
    imported_date = fields.Datetime(string="Imported Date")
    error_log = fields.Char(string="Error Log")


class TmpProdJournalProd(models.Model):
    _name = "tmp.prod.journal.prod"

    ax_journal_id = fields.Char(string="Journal ID (AX)")
    ax_voucher = fields.Char(string="Voucher (AX)")
    ax_line_num = fields.Char(string="Line Number (AX)")
    ax_transdate = fields.Date(string="Transdate (AX)")
    ax_item_id = fields.Char(string="Item ID (AX)")
    ax_invent_site = fields.Char(string="Invent Site (AX)")
    ax_invent_location = fields.Char(string="Invent Location (AX)")
    ax_wms_location = fields.Char(string="WMS Location (AX)")
    ax_invent_batch_id = fields.Char(string="Invent Batch ID (AX)")
    ax_invent_trans_id = fields.Char(string="Invent Trans ID (AX)")
    ax_quantity = fields.Float(string="Quantity (AX)", digits="Product Unit of Measure")
    ax_rec_id = fields.Char(string="Record ID (AX)")
    is_imported = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("imported", "Imported"),
            ("canceled", "Canceled"),
            ("error", "Error")
        ],
        default="draft",
    )
    imported_date = fields.Datetime(string="Imported Date")
    error_log = fields.Char(string="Error Log")


class StagingProdJournalTable(models.Model):
    _name = "staging.prod.journal.table"

    ax_journal_id = fields.Char(string="Journal ID (AX)")
    ax_description = fields.Char(string="Description (AX)")
    ax_prod_id = fields.Char(string="Prod ID (AX)")
    ax_rec_id = fields.Char(string="Record ID (AX)")


class StagingProdJournalProd(models.Model):
    _name = "staging.prod.journal.prod"

    ax_journal_id = fields.Char(string="Journal ID (AX)")
    ax_voucher = fields.Char(string="Voucher (AX)")
    ax_line_num = fields.Char(string="Line Number (AX)")
    ax_transdate = fields.Date(string="Transdate (AX)")
    ax_item_id = fields.Char(string="Item ID (AX)")
    ax_invent_site = fields.Char(string="Invent Site (AX)")
    ax_invent_location = fields.Char(string="Invent Location (AX)")
    ax_wms_location = fields.Char(string="WMS Location (AX)")
    ax_invent_batch_id = fields.Char(string="Invent Batch ID (AX)")
    ax_invent_trans_id = fields.Char(string="Invent Trans ID (AX)")
    ax_quantity = fields.Float(string="Quantity (AX)", digits="Product Unit of Measure")
    ax_rec_id = fields.Char(string="Record ID (AX)")
