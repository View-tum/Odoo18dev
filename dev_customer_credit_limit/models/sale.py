# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class sale_order(models.Model):
    _inherit= 'sale.order'
    
    exceeded_amount = fields.Float('Exceeded Amount')
    
    state = fields.Selection(selection_add=[('sent',),('credit_limit','Credit limit'),('sale',)])
    
    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        super(sale_order,self)._onchange_partner_id_warning()
        partner_id = self.partner_id
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id
            
        if partner_id:
            if partner_id.credit_limit_on_hold:
                msg = "Customer '" + partner_id.name + "' is on credit limit hold."
                return {'warning':
                            {'title': 'Credit Limit On Hold', 'message': msg
                             }
                        }
    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent','credit_limit'}

    def _show_cancel_wizard(self):
        """ Decide whether the sale.order.cancel wizard should be shown to cancel specified orders.

        :return: True if there is any non-draft order in the given orders
        :rtype: bool
        """
        if self.env.context.get('disable_cancel_warning'):
            return False
        return any(so.state in ['draft', 'credit_limit'] for so in self)
    
    def action_sale_ok(self):
        partner_id = self.partner_id
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id
        partner_ids = [partner_id.id]
        for partner in partner_id.child_ids:
            partner_ids.append(partner.id)
    
        if partner_id.check_credit:
            domain = [
                ('order_id.partner_id', 'in', partner_ids),
                ('order_id.state', 'in', ['sale', 'credit_limit','done'])]
            order_lines = self.env['sale.order.line'].search(domain)
            
            order = []
            to_invoice_amount = 0.0
            for line in order_lines:
                not_invoiced = line.product_uom_qty - line.qty_invoiced
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(
                    price, line.order_id.currency_id,
                    not_invoiced,
                    product=line.product_id, partner=line.order_id.partner_id)
                if line.order_id.id not in order:
                    if line.order_id.invoice_ids:
                        for inv in line.order_id.invoice_ids:
                            if inv.state == 'draft':
                                order.append(line.order_id.id)
                                break
                    else:
                        order.append(line.order_id.id)
                    
                to_invoice_amount += taxes['total_included']
            
            domain = [
                ('move_id.partner_id', 'in', partner_ids),
                ('move_id.state', '=', 'draft'),
                ('sale_line_ids', '!=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            for line in draft_invoice_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id, partner=line.move_id.partner_id)
                to_invoice_amount += taxes['total_included']

            # We sum from all the invoices lines that are in draft and not linked
            # to a sale order
            domain = [
                ('move_id.partner_id', 'in', partner_ids),
                ('move_id.state', '=', 'draft'),
                ('sale_line_ids', '=', False)]
            draft_invoice_lines = self.env['account.move.line'].search(domain)
            draft_invoice_lines_amount = 0.0
            invoice=[]
            for line in draft_invoice_lines:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(
                    price, line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id, partner=line.move_id.partner_id)
                draft_invoice_lines_amount += taxes['total_included']
                if line.move_id.id not in invoice:
                    invoice.append(line.move_id.id)

            draft_invoice_lines_amount = "{:.2f}".format(draft_invoice_lines_amount)
            to_invoice_amount = "{:.2f}".format(to_invoice_amount)
            draft_invoice_lines_amount = float(draft_invoice_lines_amount)
            to_invoice_amount = float(to_invoice_amount)
            available_credit = partner_id.credit_limit - partner_id.credit - to_invoice_amount - draft_invoice_lines_amount

            if self.amount_total > available_credit:
                imd = self.env["ir.actions.actions"].sudo()
                exceeded_amount = (to_invoice_amount + draft_invoice_lines_amount + partner_id.credit + self.amount_total) - partner_id.credit_limit
                exceeded_amount = "{:.2f}".format(exceeded_amount)
                exceeded_amount = float(exceeded_amount)
                vals_wiz={
                    'partner_id':partner_id.id,
                    'sale_orders':str(len(order))+ ' Sale Order Worth : '+ str(to_invoice_amount),
                    'invoices':str(len(invoice))+' Draft Invoice worth : '+ str(draft_invoice_lines_amount),
                    'current_sale':self.amount_total or 0.0,
                    'exceeded_amount':exceeded_amount,
                    'credit':partner_id.credit,
                    'credit_limit_on_hold':partner_id.credit_limit_on_hold,
                    }
                wiz_id = self.env['customer.limit.wizard'].create(vals_wiz)
                action = imd._for_xml_id("dev_customer_credit_limit.action_customer_limit_wizard")
                action['res_id'] = wiz_id.id
                return action
            else:
                self.action_confirm()
        else:
            self.action_confirm()
        return True
        
        
    def _make_url(self,model='sale.order'):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069')
        if base_url:
            base_url += '/web?db=%s&login=%s&key=%s#id=%s&model=%s' % (self._cr.dbname, '', '', self.id, model)
        return base_url

    def send_mail_approve_credit_limit(self): 
        manager_group_id = self.env.ref('sales_team.group_sale_manager').ids
        browse_group = self.env['res.groups'].browse(manager_group_id) 
        partner_id = self.partner_id
        if self.partner_id.parent_id:
            partner_id = self.partner_id.parent_id
        
        url = self._make_url('sale.order')
        subject = self.name + '-' + 'Require to Credit Limit Approval'
        for user in browse_group.users:
            partner = user.partner_id
            body = '''
                        <b>Dear ''' " %s</b>," % (partner.name) + '''
                        <p> A Sale Order ''' "<b><i>%s</i></b>" % self.name + '''  for customer ''' "<b><i>%s</i></b>" % partner_id.name +''' require your Credit Limit Approval.</p> 
                        <p>You can access sale order from  below url <br/>
                        ''' "%s" % url +''' </p> 
                        
                        <p><b>Regards,</b> <br/>
                        ''' "<b><i>%s</i></b>" % self.user_id.name +''' </p> 
                        ''' 
            
            mail_values = {
                        'email_from': self.user_id.email,
                        'email_to': partner.email,
                        'subject': subject,
                        'body_html': body,
                        'state': 'outgoing',
                    }
            mail_id =self.env['mail.mail'].create(mail_values)
            mail_id.send(True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
