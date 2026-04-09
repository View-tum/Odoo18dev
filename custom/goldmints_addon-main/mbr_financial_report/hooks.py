from odoo import api, SUPERUSER_ID

def _mbr_post_init(env):
    """Auto-create default MBR account mapping on module install."""
    env["mbr.account.map"]._auto_create_default_map()
