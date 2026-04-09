# -*- coding: utf-8 -*-
# Email: sales@creyox.com

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class ResUser(models.Model):
    _inherit = 'res.users'

    read_only = fields.Boolean(string="Make Read Only")
    read_only_type = fields.Selection([('none', 'None'), ('all', 'Whole Project'), ('specific', 'Specific Models')])
    models_id = fields.Many2many('ir.model')

    @api.depends('read_only_type', 'models_id')
    def compute_models_id(self):
        models_list = []
        for rec in self.env.user.models_id:
            models_list.append(rec.model)
        return models_list
    
    def write(self, vals):
        res = super(ResUser, self).write(vals)
        readonly_type = vals.get('read_only_type')
        if readonly_type == "none":
            self.set_read_only_user()
        return res


    @api.onchange('read_only')
    def set_read_only_user(self):
        if self.read_only_type == 'none':
            read_only_grp_id = \
            self.env['ir.model.data'].check_object_reference('read_only_user_rights', 'group_read_only_user')[1]
            self.read_only = False
            group_list2 = []
            for group in self.groups_id:
                if group.id != read_only_grp_id:
                    group_list2.append(group.id)
            result = self.write({'groups_id': ([(6, 0, group_list2)])}) 

        if self.read_only_type != 'none':
            read_only_grp_id = \
            self.env['ir.model.data'].check_object_reference('read_only_user_rights', 'group_read_only_user')[1]
            if not self.read_only:
                self.read_only = True
                group_list = []
                for group in self.groups_id:
                    group_list.append(group.id)
                group_list.append(read_only_grp_id)
                result = self.write({'groups_id': ([(6, 0, group_list)])})

            elif self.read_only:
                self.read_only = False
                group_list2 = []
                for group in self.groups_id:
                    if group.id != read_only_grp_id:
                        group_list2.append(group.id)
                result = self.write({'groups_id': ([(6, 0, group_list2)])})


class IrModelAccess(models.Model):
    _inherit = 'ir.model.access'

    @api.model
    @tools.ormcache_context('self._uid', 'model', 'mode', 'raise_exception', keys=('lang',))
    def check(self, model, mode='read', raise_exception=True):
        result = super(IrModelAccess, self).check(model, mode, raise_exception=raise_exception)
        if self.env.user.has_group('read_only_user_rights.group_read_only_user'):
            user = self.env['res.users']
            if mode != 'read' and self.env.user.read_only_type == 'all':
                return False
            elif mode != 'read' and self.env.user.read_only_type == 'specific' and user.compute_models_id():
                if model in user.compute_models_id():
                    return False
        return result


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _compute_domain(self, model_name, mode="read"):
        res = super(IrRule, self)._compute_domain(model_name, mode)
        obj_list = ['res.users.log', 'mail.channel', 'mail.alias', 'bus.presence', 'res.lang']
        if model_name not in obj_list:
            if self.env.user.has_group('read_only_user_rights.group_read_only_user'):
                user = self.env['res.users']
                if mode != 'read' and mode != "write" and self.env.user.read_only_type == 'all':
                    raise ValidationError(_('Read only user can not done this operation..! (%s)') % self.env.user.name)
                elif mode != 'read' and mode != "write" and self.env.user.read_only_type == 'specific' and user.compute_models_id():
                    if model_name in user.compute_models_id():
                        raise ValidationError(_('Read only user can not done this operation..! (%s)') % self.env.user.name)
        return res
