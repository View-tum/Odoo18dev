from odoo import fields, models

class ProductCategory(models.Model):
    _inherit = "product.category"

    is_fixed_asset = fields.Boolean(
        string="Treat as Asset",
        help="If enabled, vendor bill lines using products in this category will trigger asset creation.",
        default=False,
    )
    
    # asset_profile_id = fields.Many2one(
    #     'account.asset.profile',
    #     string='Asset Profile',
    #     help='If set, vendor bill lines using products in this category will '
    #          'create an asset with this profile when posted or when the '
    #          'manual action is run.'
    # )
    #
    # auto_create_asset = fields.Boolean(
    #     string='Auto Create Asset on Vendor Bills',
    #     default=True,
    #     help='If enabled and an Asset Profile is set, assets will be created '
    #          'automatically (or by manual button) when vendor bills are posted.'
    # )