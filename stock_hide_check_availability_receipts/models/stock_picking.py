from odoo import api, models

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    @api.depends("state", "move_ids.product_uom_qty", "picking_type_code")
    def _compute_show_check_availability(self):
        """
        Override the compute method to *always* hide the 'Check Availability' button
        for incoming pickings (Receipts).

        This method first calls the original Odoo logic (super) to compute 
        the default visibility. It then iterates over the pickings and applies
        an additional rule:
        
        If the picking type is 'incoming', the button is forcibly hidden,
        as checking stock availability is not a relevant action for 
        receiving goods. This improves the user workflow by removing 
        a confusing and unnecessary button.
        """
        super()._compute_show_check_availability()
        
        for picking in self:
            if picking.picking_type_code == "incoming":
                picking.show_check_availability = False