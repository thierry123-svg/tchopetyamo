# -*- coding: utf-8 -*-
{
    'name': "tchop_etyamo",

    'summary': """
       Module Pour la gestion des ventes Comptabilte Fabrication""",

    'description': """
        Module decrivant le flow de gestion de tchopetyamo
    """,

    'author': "My Company",
    'website': "http://www.tchopetyamo.com",

    'category': 'ACCOUNT',
    'version': '0.1',

    'depends': ['base','mrp','stock','purchase','sale'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/mrp_production_views.xml',
        'views/purchase_views.xml',
        'views/stock_views.xml',
        'views/sale_views.xml',
    ],
}