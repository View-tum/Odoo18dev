from odoo import models

class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _run_manufacture(self, procurements):
        self.env.cr.execute("SELECT MAX(id) FROM mrp_production")
        max_id = self.env.cr.fetchone()[0] or 0
        
        res = super()._run_manufacture(procurements)
        
        new_mos = self.env['mrp.production'].search([('id', '>', max_id)])
        
        if new_mos:
            for mo in new_mos:
                m_type = mo.manufacturing_type
                if m_type in ['plastic', 'pharma', 'packaging']:
                    mo._send_auto_mo_replenishment_alert(m_type)
        
        return res

    def _run_buy(self, procurements):
        # Record max PO line ID for performance (O(1) instead of fetching all records)
        self.env.cr.execute("SELECT MAX(id) FROM purchase_order_line")
        max_id = self.env.cr.fetchone()[0] or 0
        
        res = super()._run_buy(procurements)
        
        # Identify newly created PO lines 
        new_po_lines = self.env['purchase.order.line'].search([('id', '>', max_id)])
        
        if new_po_lines:
            # Group by PO
            for po in new_po_lines.order_id:
                po_lines_for_this_po = new_po_lines.filtered(lambda l: l.order_id == po)
                
                # Check for manufacturing types in the products being bought
                manufacturing_types = po_lines_for_this_po.mapped('product_id.product_tmpl_id.manufacturing_type')
                
                dominant_type = False
                if 'plastic' in manufacturing_types:
                    dominant_type = 'plastic'
                elif 'pharma' in manufacturing_types:
                    dominant_type = 'pharma'
                elif 'packaging' in manufacturing_types:
                    dominant_type = 'packaging'
                    
                if dominant_type:
                    # Send alert
                    po._send_auto_po_replenishment_alert(dominant_type)
                    
                    # Auto assign the buyer if not directly assigned, or override it to the manager
                    if dominant_type == "plastic":
                        group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_plastic"
                    elif dominant_type == "pharma":
                        group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_pharma"
                    else:
                        group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_packaging"
                    manager_group = self.env.ref(group_xml_id, raise_if_not_found=False)
                    
                    if manager_group and manager_group.users:
                        # Grab the first active manager to act as the primary buyer
                        primary_buyer = manager_group.users.filtered(lambda u: u.active)
                        if primary_buyer:
                            po.user_id = primary_buyer[0].id
        
        return res
