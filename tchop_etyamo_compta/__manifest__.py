# -*- coding: utf-8 -*-
{
    'name': "tchop_etyamo_compta",

    'summary': """
        Module pour detailler le rapport analytique de Tchop et Yamo""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Thierry Zock",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['product','web','board','purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/stock_views.xml',
        'data/ir_sequence.xml',
        'views/purchase_views.xml',
        'views/sale_views.xml',
        'wizard/tchop_etyamo_wizard.xml',
        'report/tchop_etyamo_report.xml',
        # 'report/yamo_stock_materials.xml',
        'report/yamo_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}