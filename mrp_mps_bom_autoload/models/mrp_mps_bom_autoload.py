from odoo import api, fields, models


class MrpMpsLine(models.Model):
    """
    Extend mrp.production.schedule:

    - เวลา user Add a Product ใน MPS แล้วเกิด schedule line ใหม่
      (from_bom_explosion = False)
        -> หา BoM ของ product (ใช้ bom_id ถ้ามี, ไม่มีก็หาเอง)
        -> ไล่ BoM ทุก level ด้วย recursion (_get_bom_components_recursive)
        -> สร้าง mrp.production.schedule ให้ทุก component ที่ยังไม่มีใน MPS

    - line ที่สร้างจากการแตก BoM จะถูก mark ด้วย from_bom_explosion = True
      เพื่อกันการแตกซ้ำ
    """
    _inherit = "mrp.production.schedule"

    from_bom_explosion = fields.Boolean(
        string="From BOM Explosion",
        default=False,
        help="Technical flag to avoid recursive BOM expansion.",
    )
    autoload_depth_mode = fields.Selection(
        [
            ("single", "Single Level"),
            ("multi", "Multi Level"),
        ],
        string="Auto-Explode Depth",
        default=lambda self: self._default_autoload_depth_mode(),
        help="Override how deep BOM explosion should go for this line.",
    )
    autoload_excluded_category_ids = fields.Many2many(
        "product.category",
        "mps_autoload_excluded_category_rel",
        "schedule_id",
        "category_id",
        string="Excluded Categories",
        default=lambda self: self._default_autoload_excluded_categories(),
        help="Products in these categories (including children) are ignored when exploding.",
    )

    bom_id = fields.Many2one(
        "mrp.bom",
        string="Bill of Materials",
        help="If set, this BOM will be used to explode components into the MPS.",
    )

    # -------------------------------------------------------------------------
    # Override create
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        if self.env.context.get("skip_bom_explosion"):
            return records

        processed = self.env[self._name]
        for rec, vals in zip(records, vals_list):
            if (
                rec.from_bom_explosion
                or not rec.product_id
                or not rec.bom_id
            ):
                continue
            depth_mode_override = vals.get("autoload_depth_mode")
            rec._create_mps_lines_from_bom(depth_mode_override=depth_mode_override)
            processed |= rec

        remaining = records - processed
        for rec in remaining:
            if (
                rec.from_bom_explosion
                or not rec.product_id
                or not rec.bom_id
            ):
                continue
            rec._create_mps_lines_from_bom()

        return records


    # -------------------------------------------------------------------------
    # BOM helpers
    # -------------------------------------------------------------------------

    def _find_bom_for_product(self, product, company_id=False):
        """
        หา BoM สำหรับ product ที่กำหนด
        ลำดับ:
          1) BoM ที่ fix product_id (variant)
          2) BoM ระดับ template (product_tmpl_id, product_id=False)
        """
        Bom = self.env["mrp.bom"]
        if not product:
            return False

        domain_company = []
        if company_id:
            domain_company = ["|", ("company_id", "=", company_id), ("company_id", "=", False)]

        # 1) หา BoM ที่ผูกกับ product variant ก่อน
        bom = Bom.search(
            [("product_id", "=", product.id)] + domain_company,
            limit=1,
        )
        if bom:
            return bom

        # 2) ถ้าไม่เจอ -> หา BoM ที่ผูกกับ template
        bom = Bom.search(
            [
                ("product_tmpl_id", "=", product.product_tmpl_id.id),
                ("product_id", "=", False),
            ] + domain_company,
            limit=1,
        )
        return bom

    def _find_bom_for_rec(self, rec):
        """
        หา BoM สำหรับ schedule line ตัวบนสุด (ตัวที่ user add)
        ถ้าใน model มี field bom_id และ user เลือกมาแล้ว -> ใช้ก่อน
        ไม่มีก็ไปใช้ _find_bom_for_product ตามปกติ
        """
        product = rec.product_id
        if not product:
            return False

        company_id = rec.company_id.id if getattr(rec, "company_id", False) else False

        # ถ้า schedule มี field bom_id และมีค่า -> ใช้อันนี้
        if "bom_id" in rec._fields and rec.bom_id:
            return rec.bom_id

        return self._find_bom_for_product(product, company_id=company_id)

    # -------------------------------------------------------------------------
    # Filters
    # -------------------------------------------------------------------------

    bom_filter_product_id = fields.Many2one(
        "product.product",
        string="Filter by BOM Structure",
        store=False,
        search="_search_bom_filter",
        help="Search for a product to see it and all its BOM components (recursively).",
    )

    def _search_bom_filter(self, operator, value):


        if not value:
            return []

        Product = self.env["product.product"]

        # Handle based on VALUE TYPE (not operator) for better autocomplete
        if isinstance(value, str):
            # User typed text -> use name_search to support default_code, barcode, etc.
            product_ids = [pid for pid, _name in Product.name_search(value, operator="ilike", limit=20)]
            products = Product.browse(product_ids)
        elif isinstance(value, int):
            # User selected from dropdown -> direct ID
            products = Product.browse([value])
        elif isinstance(value, list):
            # Multiple IDs selected
            products = Product.browse(value)
        else:
            # Unknown type - fallback
            return []

        if not products:

            return []

        all_products = products

        # Loop to avoid singleton error
        for product in products:
            components = self._get_bom_components_recursive(
                product,
                company_id=self.env.company.id,
                level=1,
                max_level=10,
                excluded_cats=self.env.company.mps_bom_excluded_category_ids,
                include_leafs=True  # ✅ Filter needs EVERYTHING (including Raw Materials)
            )
            for comp in components:
                all_products |= comp


        return [("product_id", "in", all_products.ids)]

    def _default_autoload_depth_mode(self):
        # Default to multi-level explosion unless user picks another option on the form.
        return "multi"

    def _default_autoload_excluded_categories(self):
        return self.env.company.mps_bom_excluded_category_ids.ids if self.env.company else []

    def _is_excluded_category(self, product, excluded_cats):
        """
        Skip products if their category is child of any excluded category set on the company.
        """
        if not product or not product.categ_id or not excluded_cats:
            return False

        return (
            self.env["product.category"].search_count(
                [("id", "child_of", excluded_cats.ids), ("id", "=", product.categ_id.id)]
            )
            > 0
        )

    def _get_configured_max_level(self, param_name, default_value):
        """
        Read an integer config parameter. Zero or negative values are treated as unlimited depth.
        """
        param_value = self.env["ir.config_parameter"].sudo().get_param(param_name, str(default_value))
        try:
            max_level = int(param_value)
        except (TypeError, ValueError):
            max_level = default_value

        if max_level <= 0:
            return 999
        return max_level

    def _get_bom_components_recursive(
        self,
        product,
        company_id=False,
        level=1,
        max_level=100,
        excluded_cats=None,
        include_leafs=False, # New Param
        _visited=None,  # Internal: track visited products
    ):
        if level > max_level or not product:
            return []

        # Initialize visited set on first call
        if _visited is None:
            _visited = set()

        bom = self._find_bom_for_product(product, company_id=company_id)
        if not bom:
            return []

        components = []
        for line in bom.bom_line_ids:
            comp_product = line.product_id
            if not comp_product:
                continue

            # ✅ Skip if already processed (prevents duplicates from shared components)
            if comp_product.id in _visited:
                continue

            # หา BoM ของ component ตัวนี้
            child_bom = self._find_bom_for_product(comp_product, company_id=company_id)

            # Skip if excluded
            if self._is_excluded_category(comp_product, excluded_cats):
                continue

            # Logic: Include if it has BOM (Semi) OR if we want leafs (Raw)
            # Default "old code" behavior was effectively include_leafs=False
            should_include = bool(child_bom) or include_leafs

            if should_include:
                components.append(comp_product)
                _visited.add(comp_product.id)  # Mark as visited

            # If child has BOM, recurse deeper
            if child_bom:
                components += self._get_bom_components_recursive(
                    comp_product,
                    company_id=company_id,
                    level=level + 1,
                    max_level=max_level,
                    excluded_cats=excluded_cats,
                    include_leafs=include_leafs,
                    _visited=_visited,  # Pass visited set
                )

        return components


    # -------------------------------------------------------------------------
    # Main logic: create schedule lines from BOM components
    # -------------------------------------------------------------------------

    def _create_mps_lines_from_bom(self, depth_mode_override=None):
        """
        สำหรับแต่ละ schedule line (ตัวที่ user add):

          1) หา BoM ของ product (ใช้ bom_id ถ้ามี)
          2) ใช้ _get_bom_components_recursive() เพื่อดึง component ทุกตัว
             ลึกสูงสุด 10 level
          3) สำหรับทุก component:
             - ถ้าใน MPS ยังไม่มี line ของ product + warehouse + company เดียวกัน
               -> สร้าง mrp.production.schedule ใหม่ (from_bom_explosion=True)
        """
        MpsLine = self.env[self._name]

        for rec in self:
            product = rec.product_id
            if not product:
                continue

            # Only explode when user explicitly selected a BOM (standard otherwise)
            # This is already filtered in create(), but good to keep as safeguard
            if not rec.bom_id:
                continue

            company_id = rec.company_id.id if getattr(rec, "company_id", False) else False

            # 1. Depth Logic
            depth_mode = depth_mode_override or rec.autoload_depth_mode or rec._default_autoload_depth_mode()

            if depth_mode == "single":
                max_level = rec._get_configured_max_level(
                    "mrp_mps_bom_autoload.single_max_level", default_value=1
                )
            else:
                max_level = rec._get_configured_max_level(
                    "mrp_mps_bom_autoload.max_level", default_value=2
                )

            # 2. Excluded Categories Logic (Wizard + Company Global)
            excluded_cats = (
                rec.autoload_excluded_category_ids or self.env['product.category']
            ) | self.env.company.mps_bom_excluded_category_ids

            # เรียก recursive เอา components ทุก level
            # ⚠️ Autoload (Creation) should follow OLD BEHAVIOR: ONLY SEMIS
            components = self._get_bom_components_recursive(
                product=product,
                company_id=company_id,
                level=1,
                max_level=max_level,
                excluded_cats=excluded_cats,
                include_leafs=False, # ✅ Exclude raw materials on creation
            )

            for comp_product in components:
                if not comp_product:
                    continue
                child_bom = self._find_bom_for_product(comp_product, company_id=company_id)
                # Backup check just in case recursion returned something we shouldn't add?
                # Actually, check not needed if function is correct, but safer to keep consistency
                if self._is_excluded_category(comp_product, excluded_cats):
                    continue

                # กัน duplicate: product + warehouse + company
                domain = [("product_id", "=", comp_product.id)]
                if hasattr(rec, "warehouse_id") and rec.warehouse_id:
                    domain.append(("warehouse_id", "=", rec.warehouse_id.id))
                if hasattr(rec, "company_id") and rec.company_id:
                    domain.append(("company_id", "=", rec.company_id.id))

                existing = MpsLine.search(domain, limit=1)
                if existing:
                    # Force is_indirect=False and replenish_trigger='manual' if set by standard Odoo
                    vals_update = {}
                    if existing.is_indirect:
                        vals_update['is_indirect'] = False
                    if existing.replenish_trigger == 'never':
                        vals_update['replenish_trigger'] = 'manual'

                    if vals_update:
                        existing.write(vals_update)
                    continue

                vals = {
                    "product_id": comp_product.id,
                    "from_bom_explosion": True,
                    "is_indirect": False,
                    "replenish_trigger": "manual",
                }
                if hasattr(rec, "warehouse_id") and rec.warehouse_id:
                    vals["warehouse_id"] = rec.warehouse_id.id
                if hasattr(rec, "company_id") and rec.company_id:
                    vals["company_id"] = rec.company_id.id

                # ใช้ context flag กัน not to explode อีก
                MpsLine.with_context(skip_bom_explosion=True).create(vals)
