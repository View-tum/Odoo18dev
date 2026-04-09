# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    property_intercompany_payable_id = fields.Many2one(
        "account.account",
        string="Intercompany Payable (ติดบริษัทผู้จ่าย)",
        domain="[('deprecated', '=', False), ('account_type', 'in', ('liability_payable', 'liability_current'))]",
        help="บัญชีหนี้สินที่ใช้เวลาบริษัทนี้ติดหนี้บริษัทอื่นจากการที่อีกบริษัทจ่ายบิลแทน",
    )
    property_intercompany_receivable_id = fields.Many2one(
        "account.account",
        string="Intercompany Receivable (ลูกหนี้ระหว่างบริษัท)",
        domain="[('deprecated', '=', False), ('account_type', 'in', ('asset_receivable', 'asset_current'))]",
        help="บัญชีลูกหนี้ที่ใช้เวลาบริษัทอื่นติดหนี้บริษัทนี้จากการจ่ายบิลแทน",
    )

    @api.constrains(
        "property_intercompany_payable_id",
        "property_intercompany_receivable_id",
        "partner_id",
    )
    def _check_partner_for_intercompany(self):
        """
        ถ้าบริษัทใดตั้งค่า Intercompany Account แล้ว ต้องมี Contact (partner) ผูกกับ Company
        เพื่อใช้ผูก partner ใน JE ข้ามบริษัท
        """
        for company in self:
            if (company.property_intercompany_payable_id or company.property_intercompany_receivable_id) and not company.partner_id:
                raise ValidationError(
                    _(
                        "บริษัท %s ตั้งค่าบัญชี Intercompany แล้ว แต่ยังไม่มี Contact ผูกไว้\n"
                        "กรุณาเลือก Contact (partner) ใน Company Form ก่อนใช้งานฟีเจอร์จ่ายบิลกลุ่มบริษัท"
                    )
                    % company.display_name
                )
