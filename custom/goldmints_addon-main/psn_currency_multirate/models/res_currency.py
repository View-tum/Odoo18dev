from odoo import api, fields, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    _sql_constraints = [
        ('unique_name', 'CHECK(1=1)','Error Message'),
        ('unique_type_name', 'unique (name,rate_type)',
         'The currency code already exists in this rate type!'),
        ('rounding_gt_zero', 'CHECK (rounding>0)',
         'The rounding factor must be greater than 0!')
    ]
    
    rate_type = fields.Selection([
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('avg', 'Avg'),
    ], string='Exchange rate', default='buy')

    # def name_get(self):
    #     res = []
    #     for currency in self:
    #         if currency.rate_type:
    #             if currency.rate_type == 'buy':
    #                 rate_type = 'Buy'
    #             elif currency.rate_type == 'sell':
    #                 rate_type = 'Sell'
    #             elif currency.rate_type == 'avg':
    #                 rate_type = 'Avg'
    #             complete_name = '%s / %s ' % (currency.name, rate_type)
    #         else:
    #             complete_name = currency.name
    #         res.append((currency.id, complete_name))
    #     return res

    @api.depends('name', 'rate_type')
    def _compute_display_name(self):
        for currency in self:
            if currency.id == self.env.company.currency_id.id:
                currency.display_name = currency.name
            elif not currency.rate_type:
                currency.display_name = currency.name
            else:
                rate_label = dict(currency._fields['rate_type'].selection).get(currency.rate_type, '')
                currency.display_name = f"{currency.name} / {rate_label}"

    def currency_multirate(self):
        currencies = self.search([])
        for currency in currencies:
            sell = self.search([('name', '=', currency.name), ('rate_type', '=', 'sell')])
            if not sell:
                sell_cur = currency.copy(default={'rate_type': 'sell'})

            avg = self.search([('name', '=', currency.name), ('rate_type', '=', 'avg')])
            if not avg:
                avg_cur = currency.copy(default={'rate_type': 'avg'})

            buy = self.search([('name', '=', currency.name), ('rate_type', '=', 'buy')])
            if not buy:
                buy_cur = currency.copy(default={'rate_type': 'buy'})