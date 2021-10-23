from datetime import datetime
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.tools.sql import drop_view_if_exists

import logging

_logger = logging.getLogger(__name__)

class YamoStockMaterials(models.Model):
    """Raw Material"""

    _name = 'yamo.stock.materials'
    _auto = False

    
    
    @api.depends('qty','price_unit')
    def _compute_amount(self):
        """Fonction qui calcule le montant total"""
        for rec in self:
            if rec.qty:
                rec.total_price_unit = rec.qty * rec.price_unit


    product_name = fields.Char(string="Matiere Premiere")
    qty = fields.Integer(string="Quantité")
    unite = fields.Char(string="Unité")
    price_unit = fields.Integer(string="Prix Unitaire")
    materials_id = fields.Many2one('purchase.order', string="Material ID")
    total_price_unit = fields.Integer(string="Montant", compute="_compute_amount")
    

   
    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(""" 
            create or replace view yamo_stock_materials as (
                select
                    min(t.id) as id,
                    t.product_name as product_name,
                    sum(t.qty) as qty,
                    t.price_unit as price_unit
                from
                    stock_yamo_materials as t
                group by
                    t.product_name,t.price_unit
                order by
                    t.product_name
            )     
            """)