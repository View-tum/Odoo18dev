import base64
from odoo import models, fields, api, tools

class Users(models.Model):
    _inherit = "res.users"

    user_signature = fields.Binary(string="Signature")
    logo_user = fields.Binary(compute="_compute_logo_user", store=True, attachment=False)

    def clear_sign(self):
        self.write({'user_signature': False})

    # @api.depends('user_signature')
    # def _compute_logo_user(self):
    #     for user in self:
    #         if user.user_signature:
    #             user.logo_user = tools.image_process(user.user_signature, size=(180, 0))
    #         else:
    #             user.logo_user = False

    @api.depends('user_signature')
    def _compute_logo_user(self):
        for user in self:
            if user.user_signature:
                decoded_image = base64.b64decode(user.user_signature)
                processed_image = tools.image_process(decoded_image, size=(250, 0))
                user.logo_user = base64.b64encode(processed_image)
            else:
                user.logo_user = False

