from odoo import api, fields, models, _
from odoo.exceptions import UserError
from lxml import etree
import json


# def _json_load(s, default):
#     try:
#         return json.loads(s) if s else default
#     except Exception:
#         return default
#
# def _or_readonly(existing):
#     """
#     Combine an existing readonly modifier (bool or domain) with is_lock=True using OR.
#     existing can be:
#       - None
#       - bool
#       - a domain in prefix-notation, e.g. ["|", ["state","=","done"], ["state","=","cancel"]]
#       - a single condition, e.g. ["state","=","done"]
#     """
#     lock_cond = ["is_lock", "=", True]
#
#     if existing is None:
#         # No existing rule → just lock_cond
#         return lock_cond
#     if isinstance(existing, bool):
#         # True stays True; False becomes lock_cond
#         return True if existing else lock_cond
#     # Domain/list case → OR them
#     return ["|", existing, lock_cond]

class ProductTemplate(models.Model):
    _inherit = "product.template"

    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
        ],
        default="draft",
        required=True,
        string="Approval State",
        tracking=True,
    )
    is_lock = fields.Boolean(string="is_lock")

    def action_approve(self):
        for record in self:
            if not self.env.user.has_group('account.group_account_manager'):
                raise UserError(_("Only Accounting Managers can approve products."))
            record.write({'approval_state': 'approved', 'is_lock': True})
            
            
    # @api.model
    # def fields_view_get(self, view_id=None, view_type="form", toolbar=False, submenu=False):
    #     res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     if view_type != "form":
    #         return res
    #
    #     # Ensure is_lock is present in fields dict so the web client knows it exists
    #     # (if your model already defines it, this is harmless)
    #     if "is_lock" not in res.get("fields", {}):
    #         # You can omit this if is_lock is a real field on the model; kept as a guard.
    #         res.setdefault("fields", {})["is_lock"] = {"type": "boolean", "string": "Locked"}
    #
    #     doc = etree.fromstring(res["arch"])
    #
    #     # Update <field> nodes
    #     for field_node in doc.xpath("//field"):
    #         # Skip non-editable virtual fields/widgets if you want (optional)
    #         # e.g., skip chatter fields:
    #         if field_node.get("widget") in {"mail_thread", "mail_followers"}:
    #             continue
    #
    #         modifiers = _json_load(field_node.get("modifiers"), {})
    #         modifiers["readonly"] = _or_readonly(modifiers.get("readonly"))
    #         field_node.set("modifiers", json.dumps(modifiers))
    #
    #     # (Optional) Also disable object/action buttons when locked
    #     # This prevents actions that might alter data even if fields are readonly.
    #     for btn in doc.xpath("//button[@type='object' or @type='action']"):
    #         modifiers = _json_load(btn.get("modifiers"), {})
    #         modifiers["readonly"] = _or_readonly(modifiers.get("readonly"))
    #         btn.set("modifiers", json.dumps(modifiers))
    #
    #     res["arch"] = etree.tostring(doc, encoding="unicode")
    #     return res
    #

