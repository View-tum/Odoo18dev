import os
import re

file_path = r'c:\365_project\TheCool18e\Dev\custom\goldmints_addon-main\mrp_parallel_console\models\mrp_production_parallel_split.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '''    def _mpc_auto_split_one_mo(self, create_missing=False):
        """Distribute MO quantity across parallel workorders (incremental)."""
        self.ensure_one()

        if create_missing:'''

new_str = '''    def _mpc_auto_split_one_mo(self, create_missing=False):
        """Distribute MO quantity across parallel workorders (incremental)."""
        self.ensure_one()
        
        # Lock the MO row in PostgreSQL to prevent concurrent edits while splitting
        self.env.cr.execute("SELECT id FROM mrp_production WHERE id = %s FOR NO KEY UPDATE", [self.id])

        if create_missing:'''

if old_str in content:
    new_content = content.replace(old_str, new_str)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully patched mrp_production_parallel_split.py")
else:
    print("Could not find the string to replace.")
