{
    'name': 'PSN: Thai Number to Text',
    'version': '18.0.0.0.1',
    'depends': ['base','psn_discount','salesperson_signature','psn_sale_order_line_number'
                ,'psn_sale_order_line_number','psn_purchase_order_line_number'
                ,'psn_account_invoice_line_number','amount_to_billing','psn_stock_picking_line_number'],
    'post_init_hook': 'create_convert_num_functions',
    'installable': True,
}
