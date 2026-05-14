import sys
sys.path.append(r'C:\365_project\TheCool18e\Dev\server')
import odoo

try:
    odoo.tools.config.parse_config(['-c', r'C:\365_project\TheCool18e\Dev\server\odoo.conf', '-d', 'UAT'])
    registry = odoo.registry('UAT')
    with registry.cursor() as cr:
        cr.execute("SELECT name, state FROM ir_module_module WHERE name = 'web_widget_x2many_2d_matrix'")
        res = cr.fetchone()
        print(f"Module 'web_widget_x2many_2d_matrix' in UAT: {res}")
except Exception as e:
    print(f"Error: {e}")
