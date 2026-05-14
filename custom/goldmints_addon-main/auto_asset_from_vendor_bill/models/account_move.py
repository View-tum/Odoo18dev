from odoo import api, fields, models, _
from odoo.exceptions import UserError


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

    def _get_asset_value_field_name(self):
        asset_model = self.env['account.asset']
        if 'purchase_value' in asset_model._fields:
            return 'purchase_value'
        if 'original_value' in asset_model._fields:
            return 'original_value'
        raise UserError(_("No supported asset value field was found on account.asset."))

    def _prepare_vendor_bill_asset_vals(self, profile, asset_name, asset_amount, source_line=None):
        self.ensure_one()
        Asset = self.env['account.asset']
        vals = {
            'name': asset_name,
            'company_id': self.company_id.id,
        }

        if 'model_id' in Asset._fields:
            vals['model_id'] = profile.id

        vals[self._get_asset_value_field_name()] = asset_amount

        if 'bill_move_id' in Asset._fields:
            vals['bill_move_id'] = self.id

        if 'date_start' in Asset._fields:
            vals['date_start'] = self.invoice_date or fields.Date.context_today(self)
        elif 'acquisition_date' in Asset._fields:
            vals['acquisition_date'] = self.invoice_date or fields.Date.context_today(self)

        if source_line and 'original_move_line_ids' in Asset._fields:
            vals['original_move_line_ids'] = [(6, 0, source_line.ids)]

        journal_field = Asset._fields.get('journal_id')
        if journal_field:
            profile_journal = getattr(profile, 'journal_id', False)
            if profile_journal:
                vals['journal_id'] = profile_journal.id
            elif getattr(self.journal_id, 'type', False) == 'general':
                vals['journal_id'] = self.journal_id.id

        currency_field = Asset._fields.get('currency_id')
        if currency_field and not getattr(currency_field, 'related', False):
            vals['currency_id'] = self.currency_id.id

        return vals

    @api.model
    def _get_asset_name_from_description(self, description):
        description = (description or '').strip()
        return description or _('New Asset')

    def action_create_assets_from_bill_lines(self):
        """Create assets from vendor bill lines, handling quantity splitting and OCA profiles."""
        self.ensure_one()
        Asset = self.env['account.asset']
        assets_to_create = []

        for line in self.invoice_line_ids:
            if not line.product_id.categ_id.is_fixed_asset:
                continue

            profile = line.product_id.asset_model_id
            if not profile:
                raise UserError(_("Product '%s' is a fixed asset but has no Asset Profile defined.") % line.product_id.name)

            # Check quantity splitting from OCA profile or Product flag
            num_assets = 1
            if line.product_id.split_assets and line.quantity > 1:
                num_assets = int(line.quantity)
                if num_assets <= 0:
                    num_assets = 1

            price_unit = line.price_subtotal / num_assets if num_assets > 0 else line.price_subtotal

            for i in range(num_assets):
                asset_name = self._get_asset_name_from_description(line.name)
                if num_assets > 1:
                    asset_name = f"{asset_name} ({i+1}/{num_assets})"
                vals = self._prepare_vendor_bill_asset_vals(
                    profile=profile,
                    asset_name=asset_name,
                    asset_amount=price_unit,
                    source_line=line,
                )
                assets_to_create.append(vals)

        if not assets_to_create:
            raise UserError(_("No fixed asset lines found in this bill."))

        created_assets = Asset.create(assets_to_create)
        for asset in created_assets.filtered(lambda rec: 'model_id' in rec._fields and rec.model_id):
            if hasattr(asset, '_onchange_model_id'):
                asset._onchange_model_id()
        self.asset_creatd = True

        if len(created_assets) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Asset'),
                'res_model': 'account.asset',
                'view_mode': 'form',
                'res_id': created_assets.id,
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Assets'),
                'res_model': 'account.asset',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_assets.ids)],
                'target': 'current',
            }

    def _compute_asset_count(self):
        # robust & fast
        grouped = self.env['account.asset'].read_group(
            [('bill_move_id', 'in', self.ids)],
            ['bill_move_id'],
            ['bill_move_id']
        )
        counts = {g['bill_move_id'][0]: g['bill_move_id_count'] for g in grouped}
        for move in self:
            move.asset_count = counts.get(move.id, 0)

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
