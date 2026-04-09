from odoo import models, fields, api, _

class AccountAssetCreateWizard(models.TransientModel):
    _name = 'account.asset.create.wizard'
    _description = 'Wizard to create assets from Vendor Bill'

    move_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True)
    line_ids = fields.One2many('account.asset.create.wizard.line', 'wizard_id', string='Asset Lines')

    @api.model
    def _get_asset_name_from_description(self, description):
        description = (description or '').strip()
        return description or _('New Asset')

    def _get_asset_value_field_name(self):
        asset_model = self.env['account.asset']
        if 'purchase_value' in asset_model._fields:
            return 'purchase_value'
        if 'original_value' in asset_model._fields:
            return 'original_value'
        raise ValueError("No supported asset value field was found on account.asset")

    def _prepare_asset_vals(self, line, profile, asset_name, asset_amount):
        Asset = self.env['account.asset']
        vals = {
            'name': asset_name,
            'company_id': self.move_id.company_id.id,
        }

        if 'model_id' in Asset._fields:
            vals['model_id'] = profile.id

        vals[self._get_asset_value_field_name()] = asset_amount

        if 'bill_move_id' in Asset._fields:
            vals['bill_move_id'] = self.move_id.id

        if 'date_start' in Asset._fields:
            vals['date_start'] = self.move_id.invoice_date or fields.Date.context_today(self)
        elif 'acquisition_date' in Asset._fields:
            vals['acquisition_date'] = self.move_id.invoice_date or fields.Date.context_today(self)

        if line.move_line_id and 'original_move_line_ids' in Asset._fields:
            vals['original_move_line_ids'] = [(6, 0, line.move_line_id.ids)]

        journal_field = Asset._fields.get('journal_id')
        if journal_field:
            profile_journal = getattr(profile, 'journal_id', False)
            if profile_journal:
                vals['journal_id'] = profile_journal.id
            elif getattr(self.move_id.journal_id, 'type', False) == 'general':
                vals['journal_id'] = self.move_id.journal_id.id

        currency_field = Asset._fields.get('currency_id')
        if currency_field and not getattr(currency_field, 'related', False):
            vals['currency_id'] = self.move_id.currency_id.id

        if 'parent_id' in Asset._fields and line.parent_asset_id:
            vals['parent_id'] = line.parent_asset_id.id

        return vals

    @api.model
    def default_get(self, fields):
        res = super(AccountAssetCreateWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            move = self.env['account.move'].browse(active_id)
            res['move_id'] = move.id
            lines = []
            for line in move.invoice_line_ids:
                if line.product_id.categ_id.is_fixed_asset:
                    profile = line.product_id.asset_model_id
                    lines.append((0, 0, {
                        'move_line_id': line.id,
                        'product_id': line.product_id.id,
                        'name': self._get_asset_name_from_description(line.name),
                        'quantity': line.quantity,
                        'price_unit': line.price_subtotal / line.quantity if line.quantity > 0 else line.price_subtotal,
                        'asset_model_id': profile.id if profile else False,
                        'split_individual': False,
                    }))
            res['line_ids'] = lines
        return res

    def action_create_assets(self):
        self.ensure_one()
        created_assets = self.env['account.asset']
        value_field = self._get_asset_value_field_name()
        for line in self.line_ids:
            if line.target_asset_id:
                # Consolidation: Add value to existing asset
                line.target_asset_id[value_field] += line.quantity * line.price_unit
                created_assets |= line.target_asset_id
            else:
                # Creation Logic
                num_to_create = int(line.quantity) if line.split_individual else 1
                val_per_asset = line.price_unit if line.split_individual else line.quantity * line.price_unit
                
                profile = line.asset_model_id
                if not profile:
                    continue
                
                for i in range(num_to_create):
                    asset_name = self._get_asset_name_from_description(line.name)
                    if line.split_individual and num_to_create > 1:
                        asset_name = f"{asset_name} ({i+1}/{num_to_create})"

                    asset_vals = self._prepare_asset_vals(
                        line=line,
                        profile=profile,
                        asset_name=asset_name,
                        asset_amount=val_per_asset,
                    )

                    asset = self.env['account.asset'].create(asset_vals)
                    if 'model_id' in asset._fields and asset.model_id and hasattr(asset, '_onchange_model_id'):
                        asset._onchange_model_id()
                    created_assets |= asset
        
        self.move_id.asset_creatd = True
        
        return {
            'name': _('Created Assets'),
            'view_mode': 'list,form',
            'res_model': 'account.asset',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', created_assets.ids)],
        }

class AccountAssetCreateWizardLine(models.TransientModel):
    _name = 'account.asset.create.wizard.line'
    _description = 'Wizard Line to create assets'

    wizard_id = fields.Many2one('account.asset.create.wizard', string='Wizard')
    move_line_id = fields.Many2one('account.move.line', string='Bill Line', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    name = fields.Char(string='Asset Name')
    quantity = fields.Float(string='Quantity', readonly=True)
    price_unit = fields.Float(string='Price Unit', readonly=True)
    asset_model_id = fields.Many2one('account.asset', string='Asset Model', domain="[('state', '=', 'model')]")
    split_individual = fields.Boolean(string='Split Individual', default=False, help="Create one asset per unit of quantity")
    target_asset_id = fields.Many2one('account.asset', string='Add to Existing Asset')
    parent_asset_id = fields.Many2one('account.asset', string='Parent Machine')
