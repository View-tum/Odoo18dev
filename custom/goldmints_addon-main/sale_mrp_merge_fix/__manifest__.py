{
    'name': 'Sale MRP Merge Fix',
    'version': '18.0.1.0.0',
    'category': 'Sales/Manufacturing',
    'summary': 'Fix MO Smart Button on SO when MO is merged',
    'description': """
        This module overrides the MO count and view action on Sale Orders to search MOs by origin string.
        This allows the smart button to show correctly even when MOs are merged from multiple SOs
        and the procurement group link is set to 'none'.
    """,
    'author': 'Wolapart',
    'depends': ['sale_mrp'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
