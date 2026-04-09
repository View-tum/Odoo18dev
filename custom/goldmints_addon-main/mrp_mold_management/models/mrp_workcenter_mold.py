# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    is_mold = fields.Boolean(
        string="Is Mold?",
        default=False,
        help="If enabled, this workcenter represents a mold (tooling).",
    )
    mold_cost_hour = fields.Float(
        string="Mold Cost / Hour",
        default=0.0,
        help="Cost of using this mold per hour of operation.",
    )
    mold_life_limit = fields.Integer(
        string="Mold Life Limit (Shots)",
        default=0,
        help="Maximum number of shots before maintenance is required.",
    )
    mold_life_current = fields.Integer(
        string="Current Shots",
        default=0,
        readonly=True,
        help="Total number of shots taken so far.",
    )
    mold_cavities = fields.Integer(
        string="Cavities",
        default=1,
        help="Number of parts produced per shot.",
    )
    mold_state = fields.Selection(
        [("normal", "Normal"), ("warning", "Warning"), ("full", "Full")],
        string="Mold Status",
        compute="_compute_mold_state",
        store=True,
        default="normal",
    )

    def action_reset_mold_life(self):
        """Reset the current shots to 0 and log the action."""
        self.ensure_one()
        if not self.is_mold:
            return

        old_shots = self.mold_life_current
        self.mold_life_current = 0
        self.message_post(
            body=f"Mold Life Reset: {old_shots} shots -> 0 shots (Maintenance completed).",
            message_type="notification"
        )

    # Matrix Compatibility
    allowed_mold_ids = fields.Many2many(
        "mrp.workcenter",
        "mrp_workcenter_mold_rel",
        "workcenter_id",
        "mold_id",
        string="Compatible Molds",
        domain=[("is_mold", "=", True)],
        help="List of molds that can be used on this machine.",
    )

    # [ENHANCED] Performance Matrix: Mold -> Product with Cycle Time
    mold_product_line_ids = fields.One2many(
        "mrp.mold.product.line",
        "mold_id",
        string="Produced Products Efficiency",
        help="List of products this mold can produce and their respective speeds.",
    )

    # Maintain backward compatibility for existing code using produced_product_ids
    produced_product_ids = fields.Many2many(
        "product.product",
        string="Produced Products",
        compute="_compute_produced_product_ids",
        inverse="_inverse_produced_product_ids",
        help="Helper field to maintain backward compatibility with matrix matching logic.",
    )

    # [UX] Show machines compatible with this mold
    compatible_machine_ids = fields.Many2many(
        "mrp.workcenter",
        string="Compatible Machines",
        compute="_compute_compatible_machine_ids",
        help="Machines that have this mold in their 'Compatible Molds' list.",
    )

    @api.depends("allowed_mold_ids")
    def _compute_compatible_machine_ids(self):
        for wc in self:
            if wc.is_mold:
                # Find machines that allow this mold
                machines = self.env["mrp.workcenter"].search([
                    ("is_mold", "=", False),
                    ("allowed_mold_ids", "in", [wc.id])
                ])
                wc.compatible_machine_ids = machines
            else:
                wc.compatible_machine_ids = False

    @api.depends("mold_product_line_ids.product_id")
    def _compute_produced_product_ids(self):
        for wc in self:
            wc.produced_product_ids = wc.mold_product_line_ids.mapped("product_id")

    def _inverse_produced_product_ids(self):
        for wc in self:
            existing_products = wc.mold_product_line_ids.mapped("product_id")
            new_products = wc.produced_product_ids - existing_products
            removed_products = existing_products - wc.produced_product_ids

            # Add new lines
            for product in new_products:
                self.env["mrp.mold.product.line"].create({
                    "mold_id": wc.id,
                    "product_id": product.id,
                })

            # Remove old lines
            if removed_products:
                wc.mold_product_line_ids.filtered(lambda line: line.product_id in removed_products).unlink()

    @api.depends("mold_life_limit", "mold_life_current")
    def _compute_mold_state(self):
        for wc in self:
            if not wc.is_mold or not wc.mold_life_limit:
                wc.mold_state = "normal"
                continue
            ratio = wc.mold_life_current / wc.mold_life_limit
            if ratio >= 1.0:
                wc.mold_state = "full"
            elif ratio >= 0.9:
                wc.mold_state = "warning"
            else:
                wc.mold_state = "normal"

    def action_open_mold_report(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_mold_management.action_mrp_mold_matrix_report")
        action['domain'] = [('mold_id', '=', self.id)]
        action['context'] = {'search_default_mold_id': self.id}
        return action

    @api.model
    def is_mold_management_enabled(self):
        """Kill switch to disable mold logic if needed."""
        return self.env['ir.config_parameter'].sudo().get_param('mrp_mold_management.enabled', default='True') == 'True'


class MrpMoldProductLine(models.Model):
    _name = "mrp.mold.product.line"
    _description = "Mold Product Efficiency Line"

    mold_id = fields.Many2one(
        "mrp.workcenter",
        string="Mold",
        required=True,
        ondelete="cascade",
        domain=[("is_mold", "=", True)],
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
    )
    cycle_time = fields.Float(
        string="Cycle Time (s)",
        default=0.0,
        help="Time in seconds for one shot (one cycle).",
    )
    units_per_hour = fields.Float(
        string="Units / Hour",
        compute="_compute_units_per_hour",
        store=True,
        help="Calculated production rate (Units/Hour) based on cycle time and cavities.",
    )

    @api.depends("cycle_time", "mold_id.mold_cavities")
    def _compute_units_per_hour(self):
        for line in self:
            if line.cycle_time > 0:
                # (3600s / cycle_time) * cavities
                line.units_per_hour = (3600.0 / line.cycle_time) * line.mold_id.mold_cavities
            else:
                line.units_per_hour = 0.0
