import re

filepath = r'c:\365_project\TheCool18e\Dev\custom\goldmints_addon-main\partner_payment_schedule\views\partner_payment_schedule_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for the list views
pattern = r'(<field name="selected_dates_count" string="เลือกแล้ว" invisible="mode != \'specific\'" />)(\s+)(<field name="active" />)'
replacement = r'\1\2<field name="selected_dates_display" string="วันที่เลือก" invisible="mode != \'specific\'" />\2\3'

new_content = re.sub(pattern, replacement, content)

if new_content != content:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Done - selected_dates_display added to list views')
else:
    print('Failed to find patterns in XML')
