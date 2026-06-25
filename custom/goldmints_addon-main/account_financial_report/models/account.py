from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    centralized = fields.Boolean(
        help="If flagged, no details will be displayed in "
        "the General Ledger report (the webkit one only), "
        "only centralized amounts per period.",
    )
    is_view = fields.Boolean(
        string="Is View/Header",
        default=False,
    )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        is_debug = False
        from odoo.http import request
        if request and getattr(request, 'session', None):
            is_debug = bool(request.session.debug)
        if not self.env.context.get('show_view_accounts') and not is_debug:
            domain = [('is_view', '=', False)] + domain
        return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        is_debug = False
        from odoo.http import request
        if request and getattr(request, 'session', None):
            is_debug = bool(request.session.debug)
        if not self.env.context.get('show_view_accounts') and not is_debug:
            args = [('is_view', '=', False)] + args
        return super().name_search(name=name, args=args, operator=operator, limit=limit)


