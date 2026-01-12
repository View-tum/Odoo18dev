# -*- coding: utf-8 -*-
# Copyright 2018 Openinside co. W.L.L.
{
    "name": "Client Action File Download",
    "summary": "Client Action File Download",
    "version": "18.0.1.1.1",
    'category': 'Extra Tools',
    "website": "https://www.open-inside.com",
	"description": """
		Client Action File Download 
		 
    """,
	'images':[
        'static/description/cover.png'
	],
    "author": "Openinside",
    "license": "OPL-1",
    "price" : 9,
    "currency": 'USD',
    "installable": True,
    "depends": [
        'web'
    ],
    "data": [
        
    ],
    'installable': True,
    'auto_install': True,    
    'odoo-apps' : True,
    'assets': {
        'web.assets_backend': [
            'oi_action_file/static/src/js/action_file_download.js',
        ],

    },    
    
}

