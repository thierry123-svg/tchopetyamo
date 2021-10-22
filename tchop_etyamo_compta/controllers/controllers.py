# -*- coding: utf-8 -*-
from odoo import http

# class TchopEtyamoCompta(http.Controller):
#     @http.route('/tchop_etyamo_compta/tchop_etyamo_compta/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tchop_etyamo_compta/tchop_etyamo_compta/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('tchop_etyamo_compta.listing', {
#             'root': '/tchop_etyamo_compta/tchop_etyamo_compta',
#             'objects': http.request.env['tchop_etyamo_compta.tchop_etyamo_compta'].search([]),
#         })

#     @http.route('/tchop_etyamo_compta/tchop_etyamo_compta/objects/<model("tchop_etyamo_compta.tchop_etyamo_compta"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tchop_etyamo_compta.object', {
#             'object': obj
#         })