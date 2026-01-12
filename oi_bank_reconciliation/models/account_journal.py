
from odoo import fields, models
import odoo

class AccountJournal(models.Model):
    _inherit = "account.journal"

    reconciliation_range = fields.Float()
    
    def _get_journal_dashboard_data_batched(self):
        res = super(AccountJournal, self)._get_journal_dashboard_data_batched()
        isEnterprise = odoo.service.common.exp_version()['server_version_info'][-1] == 'e'
        for val in res.values():
            val.update({
            'show_reconcile_items' : val.get('number_to_reconcile') and not isEnterprise
            })
        return res

    def action_statement_reconcile(self):
        ref = lambda name : self.env.ref(name).id
        return {
            'type' : 'ir.actions.act_window',
            'name' : self.name,
            'res_model' : 'account.bank.statement.line',
            'view_mode' : 'list,form',
            'views' : [(ref('oi_bank_reconciliation.view_bank_statement_line_list_reconciliation'), 'list'), 
                       (ref('oi_bank_reconciliation.view_bank_statement_line_form_reconciliation'), 'form')
                       ],
            'domain' : [('journal_id','=', self.id), ('is_reconciled','=', False)],          
            'context' : {
                'from_dashboard' : True
                }
            }
        