
from odoo import fields

def clean(v):
    return (str(v or '')).replace('?????????',' ').replace('\xa0',' ').strip()
res=[]
for move in env['account.move'].search([('asset_move_type','in',['sale','disposal'])], order='id desc', limit=10):
    res.append({
        'id': move.id,
        'name': clean(move.name),
        'type': move.asset_move_type,
        'date': str(move.date or ''),
        'lines': [
            {
                'code': line.account_id.code,
                'name': clean(line.account_id.name),
                'debit': line.debit,
                'credit': line.credit,
            }
            for line in move.line_ids.sorted(key=lambda l:(l.account_id.code or '', l.id))
        ],
    })
print(json.dumps(res, ensure_ascii=False, indent=2))
