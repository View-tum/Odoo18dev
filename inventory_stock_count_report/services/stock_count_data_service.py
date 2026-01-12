from collections import OrderedDict

from odoo.tools import float_round


class StockCountDataService:
    """Service to prepare normalized stock count data from stock.quant."""

    def __init__(self, env):
        self.env = env

    def get_lines(self, wizard):
        """Return normalized lines for the given wizard configuration.

        Notes:
        - We aggregate stock.quant rows to avoid duplicate lines caused by
          package/owner/reservation splits.
        - Aggregation key:
            (location_id, product_id, lot_id) when lot exists,
            else (location_id, product_id, False)
        """
        quant_model = self.env["stock.quant"]
        domain = self._build_quant_domain(wizard)
        quants = quant_model.search(domain)

        totals = OrderedDict()
        meta = {}

        for quant in quants:
            product = quant.product_id
            location = quant.location_id
            lot = quant.lot_id
            key = (location.id, product.id, lot.id if lot else False)

            totals[key] = totals.get(key, 0.0) + (quant.quantity or 0.0)
            if key not in meta:
                meta[key] = {
                    "location_id": location.id,
                    "location_name": location.display_name,
                    "product_id": product.id,
                    "product_code": product.default_code or "",
                    "product_name": product.display_name,
                    "lot_id": lot.id if lot else False,
                    "lot_name": lot.name if lot else "",
                    "uom_name": product.uom_id.name if wizard.show_uom else "",
                    "rounding": product.uom_id.rounding or 0.01,
                    # ✅ Price: ใช้ต้นทุน (ถ้าต้องการราคาขาย เปลี่ยนเป็น product.list_price)
                    "price": product.standard_price or 0.0,
                }

        is_prefill = (wizard.mode == "prefill")
        lines = []
        for key, qty in totals.items():
            info = meta[key]
            qty_rounded = float_round(qty, precision_rounding=info["rounding"] or 0.01)

            lines.append({
                "location_id": info["location_id"],
                "location_name": info["location_name"],
                "product_id": info["product_id"],
                "product_code": info["product_code"],
                "product_name": info["product_name"],
                "lot_id": info["lot_id"],
                "lot_name": info["lot_name"],
                "uom_name": info["uom_name"],

                # ✅ Prefill: เอาค่า qty ระบบมาใส่ Counted Qty
                "counted_qty": qty_rounded if is_prefill else "",

                # ✅ Price (ต้นทุน) - ถ้าจะใช้ราคาขายเปลี่ยนเป็น product.list_price
                "price": (info.get("price") or 0.0) if is_prefill else "",

                "note": "",
            })

        return self._sort_lines(lines, wizard.sort_by)

    def group_by_location(self, lines):
        grouped = OrderedDict()
        for line in lines:
            loc_key = line.get("location_id") or 0
            if loc_key not in grouped:
                grouped[loc_key] = {
                    "location_id": line.get("location_id"),
                    "location_name": line.get("location_name") or "",
                    "lines": [],
                }
            grouped[loc_key]["lines"].append(line)

        return list(grouped.values())

    def _build_quant_domain(self, wizard):
        location_field = "child_of" if wizard.include_child_locations else "in"
        domain = [
            ("location_id", location_field, wizard.location_ids.ids),
            ("location_id.usage", "=", "internal"),
        ]
        if wizard.only_on_hand:
            domain.append(("quantity", ">", 0))
        return domain

    def _sort_lines(self, lines, sort_by):
        def key_location(line):
            return (
                line["location_name"] or "",
                line["product_name"] or "",
                line.get("lot_name") or "",
            )

        def key_product(line):
            return (
                line["product_name"] or "",
                line["location_name"] or "",
                line.get("lot_name") or "",
            )

        def key_lot(line):
            return (
                line.get("lot_name") or "",
                line["product_name"] or "",
                line["location_name"] or "",
            )

        key_by_sort = {
            "location": key_location,
            "product": key_product,
            "lot": key_lot,
        }
        key_fn = key_by_sort.get(sort_by or "location", key_location)
        return sorted(lines, key=key_fn)
