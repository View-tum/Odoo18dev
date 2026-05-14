from odoo import models

class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _run_manufacture(self, procurements):
        self.env.cr.execute("SELECT MAX(id) FROM mrp_production")
        max_id = self.env.cr.fetchone()[0] or 0
        
        res = super()._run_manufacture(procurements)
        
        new_mos = self.env['mrp.production'].search([
            ('id', '>', max_id),
            ('state', '!=', 'cancel'),
        ])

        for m_type in ('plastic', 'pharma', 'packaging'):
            mos_for_type = new_mos.filtered(lambda mo: mo.manufacturing_type == m_type)
            if mos_for_type:
                self.env['mrp.production']._queue_auto_mo_replenishment_batch_alert(
                    m_type,
                    mos_for_type,
                )
        
        return res

    def _run_buy(self, procurements):
        # 1. Pre-process procurements to determine the correct buyer before standard logic
        for procurement, rule in procurements:
            m_type = procurement.product_id.product_tmpl_id.manufacturing_type
            if m_type in ('plastic', 'pharma', 'packaging'):
                group_xml_id = f"mrp_mps_manufacturing_type.group_mrp_manager_{m_type}"
                manager_group = self.env.ref(group_xml_id, raise_if_not_found=False)
                if manager_group and manager_group.users:
                    primary_buyer = manager_group.users.filtered(lambda u: u.active)
                    if primary_buyer:
                        procurement.values['custom_buyer_id'] = primary_buyer[0].id

        # Record max PO line ID for performance to send alerts later
        self.env.cr.execute("SELECT MAX(id) FROM purchase_order_line")
        max_id = self.env.cr.fetchone()[0] or 0
        
        res = super()._run_buy(procurements)
        
        # 2. Identify newly created PO lines and send alerts
        new_po_lines = self.env['purchase.order.line'].search([('id', '>', max_id)])
        
        if new_po_lines:
            for po in new_po_lines.order_id:
                po_lines_for_this_po = new_po_lines.filtered(lambda l: l.order_id == po)
                manufacturing_types = po_lines_for_this_po.mapped('product_id.product_tmpl_id.manufacturing_type')
                
                dominant_type = False
                if 'plastic' in manufacturing_types:
                    dominant_type = 'plastic'
                elif 'pharma' in manufacturing_types:
                    dominant_type = 'pharma'
                elif 'packaging' in manufacturing_types:
                    dominant_type = 'packaging'
                    
                if dominant_type:
                    po._send_auto_po_replenishment_alert(dominant_type)
        
        return res

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super()._make_po_get_domain(company_id, values, partner)
        if 'custom_buyer_id' in values:
            domain_list = list(domain)
            for i, condition in enumerate(domain_list):
                if isinstance(condition, tuple) and condition[0] == 'user_id':
                    domain_list[i] = ('user_id', '=', values['custom_buyer_id'])
            domain = tuple(domain_list)
        return domain

    def _prepare_purchase_order(self, company_id, origins, values):
        res = super()._prepare_purchase_order(company_id, origins, values)
        if values and values[0].get('custom_buyer_id'):
            res['user_id'] = values[0]['custom_buyer_id']
        return res
