# -*- coding: utf-8 -*-
{
    'name': "Company Branches",

    'summary': """
        This module will help to add branches in company
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Boraq-Group",
    'website': "",
    'category': 'base',
    'version': '13.0',
    'depends': ['base','sale','account','purchase','stock','point_of_sale'],
    "images" : ['static/description/banner.png'],
    'data': [
        'report/report_layout_custom_view.xml',
        'data/report_layout.xml',
        'views/company_branches_view.xml',
        'security/ir.model.access.csv',
        'views/res_company_view.xml',
        'views/sale_order_view.xml',
        'views/res_users_views.xml',
        'views/pos_config_view.xml',
        'views/stock_warehouse_view.xml',
        'report/sale_report_templates.xml',
        'views/account_invoice_view.xml',
        'report/report_invoice.xml',
        'views/purchase_order_view.xml',
        'report/purchase_order_template.xml',
        'report/purchase_quotation_template.xml',
        ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
