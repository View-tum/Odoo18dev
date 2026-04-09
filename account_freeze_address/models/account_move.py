# account_frozen_address/models/account_move.py
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    freeze_partner_id = fields.Many2one(
        string="Partner at Posting",
        comodel_name="res.partner",
        readonly=True,
        copy=False,
        help="(365 custom) ชื่อของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_street = fields.Text(
        string="Street at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) ที่อยู่ถนนของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_street2 = fields.Text(
        string="Street2 at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) ที่อยู่ถนน2 ของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_city = fields.Char(
        string="City at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) เมืองของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_state = fields.Char(
        string="State at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) รัฐของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_zip_code = fields.Char(
        string="Zip Code at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) รหัสไปรษณีย์ของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_country = fields.Char(
        string="Country at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) ประเทศของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_address = fields.Text(
        string="Address at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) ที่อยู่ของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    freeze_tax_id = fields.Char(
        string="Tax ID at Posting",
        readonly=True,
        copy=False,
        help="(365 custom) เลขประจำตัวผู้เสียภาษีของ Partner ณ เวลาที่ยืนยันบันทึกบัญชี (Invoice/Bill)",
    )

    def action_post(self):
        res = super(AccountMove, self).action_post()

        for move in self:
            if move.partner_id:
                formatted_address = move.partner_id._display_address(
                    without_company=True
                )
                clean_address = "\n".join(
                    filter(None, (formatted_address or "").split("\n"))
                )
                if move.partner_id.vat:
                    if move.partner_id.country_id.name:
                        clean_address = f"{clean_address} - {move.partner_id.vat}"
                    else:
                        clean_address = f"{clean_address}\n{move.partner_id.vat}"

                move.write(
                    {
                        "freeze_partner_id": move.partner_id.id,
                        "freeze_street": move.partner_id.street or "",
                        "freeze_street2": move.partner_id.street2 or "",
                        "freeze_city": move.partner_id.city or "",
                        "freeze_state": move.partner_id.state_id.name or "",
                        "freeze_zip_code": move.partner_id.zip or "",
                        "freeze_country": move.partner_id.country_id.name or "",
                        "freeze_address": clean_address,
                        "freeze_tax_id": move.partner_id.vat or "",
                    }
                )

        return res
