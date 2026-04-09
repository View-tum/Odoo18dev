{
    'name': 'MRP Auto Merge',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Automatically merge MOs with same BoM while preserving Origin',
    'description': """
        This module automatically merges Manufacturing Orders when:
        - Same BoM
        - Same Product
        - State: Draft or Confirmed
        - Not yet planned (is_planned = False)
        - Within configurable date range

        It preserves all Origin references for full traceability.
    """,
    'author': 'Wolapart',
    'depends': ['mrp', 'sale_mrp'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
