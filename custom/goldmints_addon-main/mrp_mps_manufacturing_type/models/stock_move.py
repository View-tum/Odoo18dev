from odoo import models, fields, api
from collections import defaultdict


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_mto_transfer_merge_group(self):
        self.ensure_one()
        if self.picking_type_id and self.picking_type_id.code != 'internal':
            return self.env['procurement.group']
        if not self.group_id:
            return self.env['procurement.group']

        mos = self.env['mrp.production'].search([
            ('procurement_group_id', '=', self.group_id.id),
        ])
        source_sos = self.env['sale.order']
        for mo in mos:
            source_so = mo.source_sale_order_id or mo.procurement_group_id.sale_id
            if not source_so and hasattr(mo, '_find_source_so'):
                source_so = mo._find_source_so()
            source_sos |= source_so
        source_sos = source_sos.filtered(lambda sale: sale.procurement_group_id)
        if len(source_sos) == 1:
            return source_sos.procurement_group_id
        return self.env['procurement.group']

    def _get_mo_manufacturing_type(self):
        self.ensure_one()
        if self.raw_material_production_id and self.raw_material_production_id.manufacturing_type:
            return self.raw_material_production_id.manufacturing_type
        if self.group_id:
            mos = self.env['mrp.production'].search([('procurement_group_id', '=', self.group_id.id)])
            types = set(mo.manufacturing_type for mo in mos if mo.manufacturing_type)
            if len(types) == 1:
                return types.pop()
        return False

    def _key_assign_picking(self):
        keys = super()._key_assign_picking()
        merge_group = self._get_mto_transfer_merge_group()
        if merge_group:
            keys = (merge_group,) + keys[1:]
        m_type = self._get_mo_manufacturing_type()
        if m_type:
            return keys + (m_type,)
        return keys

    def _search_picking_for_assignation_domain(self):
        domain = super()._search_picking_for_assignation_domain()
        merge_group = self._get_mto_transfer_merge_group()
        if merge_group:
            domain = [
                ('group_id', '=', merge_group.id)
                if isinstance(condition, tuple) and condition[0] == 'group_id'
                else condition
                for condition in domain
            ]
        m_type = self._get_mo_manufacturing_type()
        if m_type:
            domain.append(('manufacturing_type', '=', m_type))
        return domain

    def _assign_picking(self):
        for move in self:
            merge_group = move._get_mto_transfer_merge_group()
            if merge_group and move.group_id != merge_group:
                move.group_id = merge_group
        return super()._assign_picking()

    def _merge_moves_fields(self):
        vals = super()._merge_moves_fields()
        if isinstance(vals, dict):
            return vals
        if 'move_dest_ids' in vals:
            vals.remove('move_dest_ids')
        return vals

    def _assign_picking_values(self, picking):
        vals = super()._assign_picking_values(picking)
        m_type = self[:1]._get_mo_manufacturing_type()
        if m_type:
            if not picking.manufacturing_type:
                vals['manufacturing_type'] = m_type
            if not picking.user_id:
                if m_type == "plastic":
                    group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_plastic"
                elif m_type == "pharma":
                    group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_pharma"
                else:
                    group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_packaging"
                manager_group = self.env.ref(group_xml_id, raise_if_not_found=False)
                if manager_group and manager_group.users:
                    primary_buyer = manager_group.users.filtered(lambda u: u.active)
                    if primary_buyer:
                        vals['user_id'] = primary_buyer[0].id
        return vals

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        m_types = set()
        for move in self:
            m_type = move._get_mo_manufacturing_type()
            if m_type:
                m_types.add(m_type)
        if len(m_types) == 1:
            dominant_type = m_types.pop()
            vals['manufacturing_type'] = dominant_type
            if dominant_type == "plastic":
                group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_plastic"
            elif dominant_type == "pharma":
                group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_pharma"
            else:
                group_xml_id = "mrp_mps_manufacturing_type.group_mrp_manager_packaging"
            manager_group = self.env.ref(group_xml_id, raise_if_not_found=False)
            if manager_group and manager_group.users:
                primary_buyer = manager_group.users.filtered(lambda u: u.active)
                if primary_buyer:
                    vals['user_id'] = primary_buyer[0].id
        return vals
