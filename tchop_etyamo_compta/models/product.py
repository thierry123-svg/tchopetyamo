from datetime import datetime
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError

import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    """Product Template Inherit"""

    _inherit = 'product.template'

   
    def _compute_cout_achat(self):
        for record in self:
            record.unique_purchase_cost = sum(line.amount_price for line in self.cost_ids)
    
    qty = fields.Integer(string="Quantité Achat", store=True)
    purchase_cost = fields.Integer(string="Cout d'achat", compute="_compute_purchase", size=15, digits=(15,0))
    production_cost = fields.Integer(string="Cout de Production Unitaire", compute="_get_unique_production")
    revenue_cost = fields.Integer(string="Cout de Revient", compute="_compute_revenue_cost")
    analytic_revenue_rate = fields.Char(string="Taux Analytique", compute="_compute_revenue")
    analytic_result = fields.Integer(string="Revenu Analytique", compute="_compute_analytic_result")
    unique_production_cost = fields.Float(string="Cout de production", compute="_compute_production_cost")
    unique_purchase_cost = fields.Float(string="Cout d'achat Unitaire", compute="_compute_cout_achat")
    unique_revenue_cost = fields.Float(string="Cout de Revient Unitaire")
    # margin_rate = fields.Char(string="Taux de marge", compute="_compute_margin_rate")
    sale_qty = fields.Integer(string="Quantité Production", compute="_compute_quantity_production", default=1)
    checkin_yamo_date = fields.Datetime(string="Date Creation", default=datetime.now())
    total_purchase_cost = fields.Integer(string="Cout d'achat Total", compute="_compute_total_cost", store=True)
    total_production_cost = fields.Integer(string="Cout de Production Total", compute="_compute_total_cost_production", store=True)
    total_revenue_cost = fields.Integer(string="Cout de Revenue Total", compute="_compute_total_cost_revenue", store=True)
    cost_ids = fields.One2many('product.template.cost', 'product_template_id', string="Cout D'achat")
    production_ids = fields.One2many('product.template.production', 'production_template_id',string="Cout de Production")
    weigth_id = fields.Float(string="Poids de L'article")
    # poids_id = fields.Char(compute='_get_poids_id')
   
   

    @api.depends('standard_price')
    def _compute_purchase(self):
        """ Fonction qui calcule le cout d'achat """
        for rec in self:
            rec.purchase_cost = rec.qty * rec.unique_purchase_cost


    def _get_unique_production(self):
        for record in self:
            record.production_cost = record.unique_production_cost/2
    
    
    # def _get_poids_id(self):
    #     for record in self:
    #         record.poids_id = "%s" % (record.name)


    def _compute_revenue(self):
        """Fonction qui calcule le taux de revenu """
        for rec in self:
            if rec.purchase_cost != 0:
                rec.analytic_revenue_rate = str(round((rec.revenue_cost/rec.purchase_cost)*100, 2)) + '%'
    

    def _compute_analytic_result(self):
        """ Fonction qui calcule le Resultat Analytique """
        for rec in self:
            rec.analytic_result = rec.purchase_cost - rec.revenue_cost
            if  rec.analytic_result < 0:
                rec.description = "Attention votre Resultat Analytique %s est negatif" %(rec.analytic_result)


    def _compute_revenue_cost(self):
        """Fonction qui calcule le cout de revient"""
        for rec in self:
            rec.revenue_cost = rec.qty * rec.unique_revenue_cost


    def _compute_production_cost(self):
        """ Fonction qui calcule le cout de production """
        for record in self:
            record.unique_production_cost = record.unique_purchase_cost + sum(line.amount_price_production for line in record.production_ids)
    

    def _compute_quantity_production(self):
        """ Fonction qui calcule la quantite de production"""
        for record in self:
             record.sale_qty = sum(line.qty for line in record.cost_ids) + sum(line.qty for line in record.production_ids)
    # @api.constrains('qty')
    # def check_quantity(self):
    #     if self.qty ==  0:
    #         raise ValidationError(_('Vous ne pouvez pas saisir une quantite nulle! Approvisionez votre stock.'))
    #     elif self.qty > 1000:
    #         raise ValidationError(_('Vous n etes pas autoriser a remplir plus 1000 articles!.'))
    #     elif self.qty < 0:
    #          raise ValidationError(_('Une quantite ne peut pas etre negative!.'))
    

    
    # def _compute_margin_rate(self):
    #     """ Fonction qui calcule le taux de marge"""
    #     for rec in self:
    #         rec.margin_rate =  str((100 - round((rec.revenue_cost/rec.purchase_cost)*100, 2))) + '%'

    @api.onchange('sale_qty')
    def onchange_sale_qty(self):
        for rec in self:
            if rec.sale_qty < rec.qty:
                rec.qty = rec.qty - rec.sale_qty
            elif rec.sale_qty > rec.qty:
                raise ValidationError(_('La quantite vendu %s ne peut pas etre superieur a la quantite totale!' %(rec.sale_qty)))
        

    def warning_null_qty(self):
        if self.qty == 0:
            err_msg = _('Vous devez Vous reaprovisionnez en stock!!')
            raise RedirectWarning(err_msg)

   
    # def _compute_total_cost(self):
    #     record.total_purchase_cost
    #     for record in self:
    #        record.total_purchase_cost += sum(record.purchase_cost)
    #        _logger.info("in checking sum purchase_cost {}".format(record.total_purchase_cost))

     
   
    @api.depends('purchase_cost')
    def _compute_total_cost(self):
        _logger.info("RESERVATION : GET TOTAL PURCHASE COST")
        #UPDATE PRICE AMOUNT TOTAL
        self.total_purchase_cost = sum(line.purchase_cost for line in self)
        _logger.info("Checking : Total Purchase Cost {}".format(self.total_purchase_cost))

   
    @api.depends('production_cost')
    def _compute_total_cost_production(self):
        _logger.info("RESERVATION : GET TOTAL PRODUCTION COST")
        #UPDATE PRICE AMOUNT TOTAL
        self.total_production_cost = sum(line.production_cost for line in self)
        _logger.info("Checking : Total Production Cost {}".format(self.total_production_cost))
    
   
    @api.depends('revenue_cost')
    def _compute_total_cost_revenue(self):
        _logger.info("RESERVATION : GET TOTAL REVENUE COST")
        #UPDATE TOTAL REVENUE COST
        self.total_revenue_cost = sum(line.revenue_cost for line in self)
        _logger.info("Checking : Total Revenue Cost {}".format(self.total_revenue_cost))




    class ProductTemplateCost(models.Model):
        _name='product.template.cost'
        
       
        @api.depends('qty','unit_price')
        def _compute_amount(self):
            """Fonction qui calcule le montant total"""
            for rec in self:
               if rec.qty:
                   rec.amount_price = rec.qty * rec.unit_price

        
        
        @api.depends('amount_price')
        def _compute_amount_total(self):
            """Fonction qui calcule le montant total"""
            if self.amount_price:
                self.amount_total_price = sum(line.amount_price for line in self)
                _logger.info("Checking : new info cost {}".format(self.amount_total_price))
        
        
        element_name = fields.Selection([
            ('Sachet Jaune','F1'),
            ('sucre','F2'),
            ('citron','F3'),
            ('Lait','F4'),
            ('Levure','F5'),
            ('Farine','F6'),
            ('Sel','F7'),
            ('Boite Blanche','F8'),
            ('Huile','F9'),
            ('GAZ','F10'),
            ('Frais sur Achat','F11'),
        ], string="Elements")
        # element_name = fields.Char(string="Elements")
        qty = fields.Float(string="Quantite en Kg")
        unit_price = fields.Float(string="Prix Unitaire")
        amount_price = fields.Float(string="Montants", compute="_compute_amount", store=True)
        amount_total_price = fields.Float(string="Montants Total", compute="_compute_amount_total", store=True)
        product_template_id = fields.Many2one('product.template', string="Product ID")

    
    class ProductTemplateProduction(models.Model):
        _name='product.template.production'


       
        @api.depends('qty','unit_price')
        def _compute_amount(self):
            """Fonction qui calcule le montant total"""
            for rec in self:
               if rec.qty:
                   rec.amount_price_production = rec.qty * rec.unit_price
        

        def _get_defaut_cost(self):
            return  self.env['product.template'].search([('unique_purchase_cost', '=', 10)], limit=1)


        element_name = fields.Char(string="Elements")
        qty = fields.Float(string="Quantite en Kg")
        unit_price = fields.Float(string="Prix Unitaire")
        amount_price_production = fields.Float(string="Montants", compute="_compute_amount",store=True)
        production_template_id = fields.Many2one('product.template', string="Product ID")
        default_amount = fields.Float(string="Montants", related="production_template_id.unique_purchase_cost",compute="_compute_amount",store=True, limit=1)
        
        