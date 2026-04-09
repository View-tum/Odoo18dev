from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_mo_manufacturing_type(self):
        """Helper to find the manufacturing type associated with this move if it belongs to an MO."""
        self.ensure_one()
        # Direct relationship: Raw material for an MO
        if self.raw_material_production_id and self.raw_material_production_id.manufacturing_type:
            return self.raw_material_production_id.manufacturing_type
            
        # Indirect relationship: Upstream move assigned via procurement group
        if self.group_id:
            mos = self.env['mrp.production'].search([('procurement_group_id', '=', self.group_id.id)])
            types = set(mo.manufacturing_type for mo in mos if mo.manufacturing_type)
            if len(types) == 1:
                return types.pop()
        
        return False

    def _key_assign_picking(self):
        keys = super()._key_assign_picking()
        m_type = self._get_mo_manufacturing_type()
        
        if m_type:
            # Reconstruct the key: remove group_id and partner_id
            # but KEEP location_id to ensure pickings are separated by source area.
            custom_key = f"MO_MERGE_{m_type}"
            
            new_keys = (
                custom_key, 
                self.location_id, 
                self.location_dest_id, 
                self.picking_type_id
            )
            return new_keys
            
        return keys

    def _search_picking_for_assignation_domain(self):
        domain = super()._search_picking_for_assignation_domain()
        m_type = self._get_mo_manufacturing_type()
        
        if m_type:
            # We remove 'group_id' and 'partner_id' to allow cross-MO merging.
            # We KEEP 'location_id' so we don't accidentally merge RM and Semi picks.
            domain = [d for d in domain if d[0] not in ('group_id', 'partner_id')]
            
            # Add our custom manufacturing type constraint
            domain.append(('manufacturing_type', '=', m_type))
            
        return domain

    def _assign_picking_values(self, picking):
        """Ensure the manufacturing_type and user_id are set when appending to an existing picking."""
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
        
        # Determine if these moves belong to a specific manufacturing type
        m_types = set()
        for move in self:
            m_type = move._get_mo_manufacturing_type()
            if m_type:
                m_types.add(m_type)
                
        if len(m_types) == 1:
            dominant_type = m_types.pop()
            vals['manufacturing_type'] = dominant_type
            
            # Explicitly set the location_id of the picking to the location_id of the first move
            # otherwise Odoo might use the picking type's default which might be vague.
            # But actually standard Odoo uses self.mapped('location_id').id if unique.
            
            # Assign Buyer (Manager)
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
