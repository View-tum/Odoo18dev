"""
Run inside Odoo shell.

Example:
    .\\.venv\\Scripts\\python.exe server/odoo-bin shell -c server/odoo.conf -d view < custom/goldmints_addon-main/mrp_product_movement_dashboard/scripts/setup_default_report_groups.py
"""

from pprint import pprint

DRY_RUN = False

result = env["product.report.group"].setup_default_groups_and_assign(dry_run=DRY_RUN)
if not DRY_RUN:
    env.cr.commit()

pprint(result)

print("verification")
print(
    {
        "groups": env["product.report.group"].search_count([]),
        "templates_with_group": env["product.template"].search_count([("report_group_id", "!=", False)]),
    }
)
