import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("STEP 1: Duplicate SOD-263215")
print("=" * 60)

so_orig = env['sale.order'].search([('name', '=', 'SOD-263215')], limit=1)
if not so_orig:
    print("ERROR: SOD-263215 not found!")
    sys.exit()
print("Original SO: %s | state: %s | lines: %d" % (so_orig.name, so_orig.state, len(so_orig.order_line)))

new_so = so_orig.copy()
print("Duplicated SO: %s | state: %s" % (new_so.name, new_so.state))
env.cr.commit()

print("\n" + "=" * 60)
print("STEP 2: Confirm the SO")
print("=" * 60)

new_so.action_confirm()
env.cr.commit()
print("SO confirmed: %s | state: %s" % (new_so.name, new_so.state))
print("Procurement group: %s (id=%s)" % (new_so.procurement_group_id.name, new_so.procurement_group_id.id))

print("\n" + "=" * 60)
print("STEP 3: Check MOs created")
print("=" * 60)

mos = env['mrp.production'].search([('source_sale_order_id', '=', new_so.id), ('state', '!=', 'cancel')])
print("Total MOs: %d" % len(mos))

mfg_types = {}
for mo in mos:
    mt = mo.manufacturing_type or 'NONE'
    if mt not in mfg_types:
        mfg_types[mt] = 0
    mfg_types[mt] += 1
for mt, cnt in sorted(mfg_types.items()):
    print("  %s: %d MOs" % (mt, cnt))

print("\n" + "=" * 60)
print("STEP 4: Check Internal Transfers (MERGE RESULT)")
print("=" * 60)

all_pg_ids = list(set(m.procurement_group_id.id for m in mos))
all_pg_ids.append(new_so.procurement_group_id.id)

picks = env['stock.picking'].search([
    ('group_id', 'in', all_pg_ids),
    ('picking_type_id.code', '=', 'internal'),
    ('state', '!=', 'cancel'),
])
print("Total internal transfers: %d" % len(picks))

picks_so_group = env['stock.picking'].search([
    ('group_id', '=', new_so.procurement_group_id.id),
    ('picking_type_id.code', '=', 'internal'),
    ('state', '!=', 'cancel'),
])
print("Transfers with SO group: %d" % len(picks_so_group))

loc_groups = {}
for p in picks:
    key = (p.picking_type_id.name, p.location_id.complete_name, p.location_dest_id.complete_name, p.manufacturing_type or 'NONE')
    if key not in loc_groups:
        loc_groups[key] = []
    loc_groups[key].append(p)

print("\n--- Transfer grouping by route ---")
total_should_be = 0
for key, plist in sorted(loc_groups.items(), key=lambda x: -len(x[1])):
    pt, src, dst, mfg = key
    total_should_be += 1
    status = "OK" if len(plist) == 1 else "FRAGMENTED (%d)" % len(plist)
    total_moves = sum(len(p.move_ids) for p in plist)
    print("  [%s] %s -> %s (mfg=%s): %d picking(s), %d moves [%s]" % (
        pt, src.split('/')[-1], dst.split('/')[-1], mfg, len(plist), total_moves, status))
    for p in plist:
        print("    %s | group=%s | moves=%d | state=%s" % (
            p.name, p.group_id.name, len(p.move_ids), p.state))

print("\n--- SUMMARY ---")
fragmented = sum(1 for plist in loc_groups.values() if len(plist) > 1)
print("Unique routes: %d" % len(loc_groups))
print("Fragmented routes: %d" % fragmented)
print("Total pickings: %d (should be ~%d)" % (len(picks), len(loc_groups)))

if fragmented == 0:
    print("\n>>> MERGE IS WORKING CORRECTLY! <<<")
else:
    print("\n>>> STILL FRAGMENTED - NEEDS MORE INVESTIGATION <<<")

print("\n" + "=" * 60)
print("STEP 5: Check Sequence Continuity")
print("=" * 60)

for key, plist in sorted(loc_groups.items()):
    if len(plist) <= 1:
        continue
    pt, src, dst, mfg = key
    names = sorted([p.name for p in plist])
    print("  [%s] %s->%s (mfg=%s):" % (pt, src.split('/')[-1], dst.split('/')[-1], mfg))
    for n in names:
        print("    %s" % n)

env.cr.rollback()
