{
    "name": "M2O Force Dropdown",
    "version": "18.0.1.0.5",
    "summary": "Many2one that always shows dropdown (even on mobile)",
    "description": "Forces many2one autocomplete to use the inline dropdown everywhere (desktop, tablet, mobile) by patching env.isSmall and Many2XAutocomplete so the mobile dialog never opens.",
    "category": "Web",
    "license": "LGPL-3",
    "author": "Phyo Thet Paing/paingphyothet561@gmail.com",
    "website": "https://www.365infotech.co.th/",
    "depends": [
                "web", 
                "sale_management", 
                "partner_autocomplete"
                ],
    "data": [
        # "views/sale_order_view.xml",
    ],
    
    "assets": {
        "web.assets_backend": [
            "many2one_force_dropdown/static/src/xml/m2o_force_inline_all.xml",
            "many2one_force_dropdown/static/src/js/m2o_force_inline_all.js",
        ],
    },
    "installable": True
}
