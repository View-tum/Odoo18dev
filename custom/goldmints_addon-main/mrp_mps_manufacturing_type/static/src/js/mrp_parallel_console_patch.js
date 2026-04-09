/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ParallelShopfloorHome } from "@mrp_parallel_console/js/mrp_parallel_console";

patch(ParallelShopfloorHome.prototype, {
    /**
     * @override
     */
    async loadMos(domain) {
        // Use provided domain or fallback to searchDomain from props
        const baseDomain = domain || this.props.searchDomain || [];
        // Ensure it's a new array to avoid mutating props directly
        const finalDomain = [...baseDomain];
        
        const context = (this.props.action && this.props.action.context) || this.props.searchContext || {};
        const m_type = context.default_manufacturing_type || context.manufacturing_type;
        if (m_type) {
            // Check if domain already has manufacturing_type to avoid double adding
            const hasType = finalDomain.some(d => Array.isArray(d) && d[0] === 'manufacturing_type');
            if (!hasType) {
                finalDomain.push(['manufacturing_type', '=', m_type]);
            }
            
            // Update title if possible
            if (this.props.action) {
                if (m_type === 'plastic' && !this.props.action.display_name.includes("Plastic")) {
                    this.props.action.display_name = "Plastic Shop Floor";
                } else if (m_type === 'pharma' && !this.props.action.display_name.includes("Pharma")) {
                    this.props.action.display_name = "Pharma Shop Floor";
                }
            }
        }
        
        return super.loadMos(finalDomain);
    }
});

