from datetime import datetime
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.tools.sql import drop_view_if_exists

import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    """Raw Material"""

    _name = 'stock.yamo.materials'
    _rec_name = 'product_name'

    @api.multi
    @api.depends('qty','price_unit')
    def _compute_amount(self):
        """Fonction qui calcule le montant total"""
        for rec in self:
            if rec.qty:
                rec.total_price_unit = rec.qty * rec.price_unit


    product_name = fields.Char(string="Matiere Premiere")
    qty = fields.Integer(string="Quantité")
    unite = fields.Integer(string="Unité")
    price_unit = fields.Integer(string="Prix Unitaire")
    materials_id = fields.Many2one('purchase.order', string="Material ID")
    total_price_unit = fields.Integer(string="Montant", compute="_compute_amount")
    materials_ids = fields.Many2one('stock.yamo.materials',string="Matiere Premiere", change_default=True, required=True)

    
    


class ProductTemplateFood(models.Model):
    """Fresh Food"""

    _name = 'stock.fresh.food'
    _rec_name = 'product_name'

    product_name = fields.Char(string="Vivre Frais")
    qty = fields.Integer(string="Quantité")
    unite = fields.Integer(string="Unité")
    price_unit = fields.Integer(string="Prix Unitaire")


class ProductTemplateJuice(models.Model):
    """Djara"""

    _name = 'stock.fresh.juice'
    _rec_name = 'product_name'

    product_name = fields.Char(string="Djara")
    qty = fields.Integer(string="Quantité")
    unite = fields.Integer(string="Unité")
    price_unit = fields.Integer(string="Prix Unitaire")

class ProductTemplateJuice(models.Model):
    """Djara"""

    _name = 'stock.yamo.extra'
    _rec_name = 'product_name'

 

    product_name = fields.Char(string="Extra")
    qty = fields.Integer(string="Quantité")
    unite = fields.Integer(string="Unité")
    price_unit = fields.Integer(string="Prix Unitaire")
   








    