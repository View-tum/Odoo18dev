# -*- coding: utf-8 -*-
# from odoo import http


# class Addons/saleOrder365ShippingPolicy(http.Controller):
#     @http.route('/addons/sale_order_365_shipping_policy/addons/sale_order_365_shipping_policy', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/addons/sale_order_365_shipping_policy/addons/sale_order_365_shipping_policy/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('addons/sale_order_365_shipping_policy.listing', {
#             'root': '/addons/sale_order_365_shipping_policy/addons/sale_order_365_shipping_policy',
#             'objects': http.request.env['addons/sale_order_365_shipping_policy.addons/sale_order_365_shipping_policy'].search([]),
#         })

#     @http.route('/addons/sale_order_365_shipping_policy/addons/sale_order_365_shipping_policy/objects/<model("addons/sale_order_365_shipping_policy.addons/sale_order_365_shipping_policy"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('addons/sale_order_365_shipping_policy.object', {
#             'object': obj
#         })

