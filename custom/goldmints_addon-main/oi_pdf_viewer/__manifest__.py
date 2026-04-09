# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    'name': 'PDF Viewer',
    "summary": "PDF, PDF Viewer, PDF Preview, PDF Report",
    "category": "Extra Tools",
    
    "website": "https://www.open-inside.com",
    "author": "Openinside",
    "version": "18.0.1.1.5",
    "license": "OPL-1",
    "price" : 29.99,    
    "currency": 'USD',
    'depends': [
        'web',
    ],    
    'data': [
        
    ],
    'images': [
            'static/description/cover.png'
        ],
    'assets': {
        'web.assets_backend': [            
            'oi_pdf_viewer/static/src/pdf_viewer/pdf_viewer.js',
            'oi_pdf_viewer/static/src/pdf_viewer/pdf_viewer.xml'
        ],

    },      
    'installable': True,
    'odoo-apps' : True,
    'auto_install': True,
}
