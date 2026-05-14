
from pathlib import Path
import json
OUT = Path(r"C:\365_project\TheCool18e\Dev\reports\accounting_manual_tools\output\menu_probe_extended_20260409.json")

def clean(v):
    return str(v or '').replace('\xa0',' ').strip()

def path_of(menu):
    names=[]
    while menu:
        names.append(clean(menu.name))
        menu=menu.parent_id
    return ' > '.join(reversed(names))

xmlids = [
    'account_asset.menu_action_account_asset_form',
    'account_asset.menu_action_account_asset_model_form',
    'account_fixed_asset_report.menu_accounting_fixed_asset_report',
    'mrp.menu_mrp_production_action',
    'stock_account.menu_valuation',
    'account_stock_card_rng8.menu_account_stock_card_rng8',
    'mrp.menu_mrp_bom_form_action',
]
res={'xmlids':{}, 'searches':{}}
for xmlid in xmlids:
    try:
        menu = env.ref(xmlid)
        res['xmlids'][xmlid] = {'id':menu.id,'name':clean(menu.name),'path':path_of(menu),'action':menu.action.id if menu.action else False}
    except Exception as e:
        res['xmlids'][xmlid] = {'error': str(e)}

terms = ['Product Categories','Products','Bills of Materials','Scrap','Valuation','Assets','Asset Models','Manufacturing Orders','??.8']
Menu = env['ir.ui.menu']
for term in terms:
    menus = Menu.search([('name','ilike',term)], limit=20)
    res['searches'][term] = [
        {'id':m.id,'name':clean(m.name),'path':path_of(m),'action':m.action.id if m.action else False}
        for m in menus
    ]
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
print(str(OUT))
