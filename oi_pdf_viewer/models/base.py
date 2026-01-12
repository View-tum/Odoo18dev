from odoo import models

class Base(models.AbstractModel):
    _inherit = 'base'
    
    def action_pdf_preview(self, report_name = None, field=None, title = 'Report', type='pdf'):                                                                                 
        return {
            'name' : title,
            'type' : 'ir.actions.client',
            'tag' : 'action_pdf_viewer',
            'params' : {
                'model': self._name,
                'report_name': report_name,
                "field" : field,                
                'docids': self.ids,
                "id" : self.id if len(self) == 1 else False,
                "type" : type
            }
          }
                
