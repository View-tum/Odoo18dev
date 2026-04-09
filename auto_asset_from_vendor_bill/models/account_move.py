from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    has_asset_category_line = fields.Boolean(
        string="Has Asset-Category Line",
        compute="_compute_asset_flags",
        store=False,
    )
    asset_creatd = fields.Boolean(string="Asset Ceated",)
    asset_ids = fields.One2many(
        'account.asset',
        'bill_move_id',
        string='Assets', 
        copy=False,
    )
    asset_count = fields.Integer(
        string='Assets',
        compute='_compute_asset_count',
        store=False,
    )
    
    

    @api.depends("invoice_line_ids.product_id.categ_id.is_fixed_asset", "move_type")
    def _compute_asset_flags(self):
        for move in self:
            flag = False
            if move.move_type in ("in_invoice", "in_refund"):
                for line in move.invoice_line_ids:
                    if line.product_id.categ_id.is_fixed_asset:
                        flag = True
                        break
            move.has_asset_category_line = flag

    def action_create_assets_from_bill_lines(self):
        """Always create a new asset with mandatory values and go to its form view."""
        self.ensure_one()
        Asset = self.env['account.asset']
    
        # pick any default profile (must exist in DB)
        # profile = self.env['account.asset.profile'].search(
        #     [('company_id', '=', self.company_id.id)], limit=1
        # )
        # if not profile:
        #     raise UserError(_("No Asset Profile defined for this company."))
        if not self.line_ids[0].product_id.asset_model_id:
            raise UserError(self.env._("You need to add Asset Model (Product Form -> Accounting -> Asset Models) before create assets."))
        if self.line_ids[0].product_id.asset_model_id:
            asset_model_id = self.line_ids[0].product_id.asset_model_id
            account_asset_id = asset_model_id.account_asset_id.id
            account_depreciation_id = asset_model_id.account_depreciation_id.id
            account_depreciation_expense_id =  asset_model_id.account_depreciation_expense_id.id
        vals = {
            'name': self.line_ids[0].product_id.name if self.line_ids else (self.name or _('New Asset')),
            'journal_id': self.journal_id.id,
            # 'profile_id': profile.id,  # mandatory
            'original_value': self.amount_untaxed,  # mandatory
            'acquisition_date': self.invoice_date or fields.Date.context_today(self),
            'company_id': self.company_id.id,
            'bill_move_id': self.id,
            'currency_id': self.currency_id.id,
            'account_asset_id': account_asset_id,
            'account_depreciation_id' : account_depreciation_id,
            'account_depreciation_expense_id' : account_depreciation_expense_id
            

            # 'original_move_line_ids': self.line_ids
        }
    
        asset = Asset.create(vals)
        if asset:
            self.write({'asset_ids': [(6, 0, asset.ids)]})
            print("Assets=>", self.asset_ids)
        self.asset_creatd = True
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset'),
            'res_model': 'account.asset',
            'view_mode': 'form',
            'res_id': asset.id,
            'target': 'current',
        }
        
    def _compute_asset_count(self):
        Asset = self.env['account.asset']
        # robust & fast: works even if asset_ids isn't prefetched
        grouped = self.env['account.asset'].read_group(
            [('bill_move_id', 'in', self.ids)],
            ['bill_move_id'],
            ['bill_move_id']
        )
        counts = {g['bill_move_id'][0]: g['bill_move_id_count'] for g in grouped}
        for move in self:
            move.asset_count = counts.get(move.id, 0)
        # for move in self:
        #     if move.asset_ids:
        #         move.asset_count = len(move.asset_ids)
                
            
    def _get_account_assets(self):
        asset_ids = self.env['account.asset'].search([('bill_move_id', '=', self.id)])
        self.asset_ids = asset_ids
        return asset_ids
        
    def action_view_assets(self):
        """Open the assets created from this bill."""
        self.ensure_one()
        asset_ids = self._get_account_assets().ids
        action = {
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
        }
        if len(asset_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': asset_ids[0],
            })
        else:
            action.update({
                'name': _("Purchase Order generated from %s", self.name),
                'domain': [('id', 'in', asset_ids)],
                'view_mode': 'list,form',
            })
        return action