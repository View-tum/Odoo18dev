# Stock Move Self-Loop Cancel Design

## Standard Vs Pain Point

Odoo standard stock chaining allows a move to point to upstream and downstream moves. Manufacturing cancellation traverses upstream moves to notify affected documents, assuming the graph is acyclic.

The installed custom internal-transfer consolidation groups moves from multiple MTO manufacturing demands into the same picking. When linked moves are merged, standard merge values copy links from all merged records onto the survivor. Links to records inside that same merge set can therefore become a self-link, and cancellation recursively revisits the same move.

## Confirmed Failure

Database `GoldMints_Uat_Manu` contains nine `stock_move_move_rel` self-links on picking `GMP/TRPL/02161`. The affected moves are upstream supplies for active manufacturing raw material moves. Cancellation reaches one of these links and raises `RecursionError`.

## Design

Extend the existing custom `stock.move._merge_moves_fields()` override in `mrp_mps_manufacturing_type`. For both `move_dest_ids` and `move_orig_ids`, retain only linked moves outside the recordset being merged. This preserves real external demand and supply traceability while preventing any member of the merge group from being written back onto the survivor.

Do not modify Odoo official addons. Do not alter stock quantity, valuation layers, or move states as part of the data repair.

## Data Repair

Create an audit backup table in `GoldMints_Uat_Manu` containing the confirmed self-link rows and identifying move data. Delete only `stock_move_move_rel` rows where `move_orig_id = move_dest_id`. Re-query self-links and the active affected MO traversal after deletion.

## Verification

Add a regression test that creates merge candidates with internal and external origin/destination links. The merged values must keep external links and omit internal links. Run the focused Odoo module test. After database repair, verify that no self-links remain and report any separate multi-node cycles without deleting them automatically.
