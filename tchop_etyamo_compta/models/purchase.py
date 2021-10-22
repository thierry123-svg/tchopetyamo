from datetime import datetime
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError

import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    """Purchase Order"""

    _inherit = 'purchase.order'
    _rec_name = 'yamo_order'

    raw_materials_ids = fields.One2many('stock.yamo.materials', 'materials_id')
    
    @api.depends('raw_materials_ids.total_price_unit')
    def _amount_all(self):
        for order in self:
            amount_untaxed_ = 0.0
            for line in order.raw_materials_ids:
                amount_untaxed_ += line.total_price_unit
            order.update({
                'amount_untaxed_': order.currency_id.round(amount_untaxed_),
                'amount_total_': amount_untaxed_,
            })



    amount_untaxed_ = fields.Integer(string='Montant Non taxe', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total_ = fields.Integer(string='Total', store=True, readonly=True, compute='_amount_all')
    yamo_order = fields.Char('Reference Ordre', required=True, index=True, copy=False, default='New')
    
    
    @api.model
    def create(self, vals):
        if vals.get('yamo_order', _('New')) == _('New'):
             vals['yamo_order'] = self.env['ir.sequence'].next_by_code('purchase.order.yamo') or _('New')
        return super(PurchaseOrder, self).create(vals)


class PurchaseElectricity(models.Model):
    _name = 'purchase.electricity'


    name = fields.Char(string="Libelle", required=True, copy=False, readonly=True,default=lambda self: _('New'))
    qty = fields.Integer(string="Quantite", default=1)
    intitule = fields.Char(string="Intitule", default="Facture D'electricite")
    amount = fields.Integer(string="Montant")
    sub_total = fields.Integer(string="Montant Total", compute='_amount_total')
    date_order = fields.Datetime(string='Date', required=True, readonly=True, index=True, default=fields.Datetime.now)



    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
             vals['name'] = self.env['ir.sequence'].next_by_code('purchase.electricity.yamo') or _('New')
        return super(PurchaseElectricity, self).create(vals)

    
    @api.depends('qty','amount')
    def _amount_total(self):
        for record in self:
            record.sub_total = record.qty * record.amount


class PurchaseWater(models.Model):
    _name = 'purchase.water'


    name = fields.Char(string="Libelle", required=True, copy=False, readonly=True,default=lambda self: _('New'))
    qty = fields.Integer(string="Quantite", default=1)
    intitule = fields.Char(string="Intitule", default="Facture D'eau")
    amount = fields.Integer(string="Montant")
    sub_total = fields.Integer(string="Montant Total", compute='_amount_total')
    date_order = fields.Datetime(string='Date', required=True, readonly=True, index=True, default=fields.Datetime.now)



    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
             vals['name'] = self.env['ir.sequence'].next_by_code('purchase.water.yamo') or _('New')
        return super(PurchaseWater, self).create(vals)

    
    @api.depends('qty','amount')
    def _amount_total(self):
        for record in self:
            record.sub_total = record.qty * record.amount


class OtherExpenses(models.Model):
    _name = 'other.expenses'


    name = fields.Char(string="Libelle", required=True, copy=False, readonly=True,default=lambda self: _('New'))
    qty = fields.Integer(string="Quantite", default=1)
    intitule = fields.Char(string="Intitule", default="Autres depenses")
    amount = fields.Integer(string="Montant")
    sub_total = fields.Integer(string="Montant Total", compute='_amount_total')
    date_order = fields.Datetime(string='Date', required=True, readonly=True, index=True, default=fields.Datetime.now)



    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
             vals['name'] = self.env['ir.sequence'].next_by_code('other.expenses.yamo') or _('New')
        return super(OtherExpenses, self).create(vals)

    
    @api.depends('qty','amount')
    def _amount_total(self):
        for record in self:
            record.sub_total = record.qty * record.amount