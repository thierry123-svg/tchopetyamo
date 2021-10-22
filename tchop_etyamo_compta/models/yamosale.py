from datetime import datetime, timedelta
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from odoo.addons import decimal_precision as dp


import logging

_logger = logging.getLogger(__name__)

class YamoOrder(models.Model):
    """Yamo Order"""

    _name = 'yamo.sale.order'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Yamo Order"
    
    

    def _default_validity_date(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.user.company_id.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return False


    name = fields.Char(string='Numero de la vente', required=True, copy=False, readonly=True, states={'brouillon': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    origin = fields.Char(string='Source Document', help="Reference of the document that generated this sales order request.")
    client_order_ref = fields.Char(string='Customer Reference', copy=False)
    reference = fields.Char(string='Payment Ref.', copy=False,
        help='The payment communication of this sale order.')
    state = fields.Selection([
        ('brouillon', 'Devis'),
        ('sent', 'Devis Envoye'),
        ('sale', 'Commande de Vente'),
        ('done', 'Termine'),
        ('cancel', 'Annule'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', track_sequence=3)
    date_order = fields.Datetime(string='Date de La commande', required=True, readonly=True, index=True, states={'brouillon': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    is_expired = fields.Boolean(compute='_compute_is_expired', string="Is expired")
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True, help="Date on which sales order is created.")
    confirmation_date = fields.Datetime(string='Confirmation Date', readonly=True, index=True, help="Date on which the sales order is confirmed.", oldname="date_confirm", copy=False)
    user_id = fields.Many2one('res.users', string='Vendeur', index=True, track_visibility='onchange', track_sequence=2, default=lambda self: self.env.user)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True, states={'brouillon': [('readonly', False)], 'sent': [('readonly', False)]}, help="The analytic account related to a sales order.", copy=False, oldname='project_id')
    order_line = fields.One2many('yamo.sale.order.line', 'order_ids', string='Lignes de Commande')
    amount_untaxed = fields.Monetary(string='Montant Non Taxe', store=True, readonly=True, compute='_amount_all', track_visibility='onchange', track_sequence=5)
    amount_by_group = fields.Binary(string="Montant Taxe Par Groupe", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always', track_sequence=6)
    currency_rate = fields.Float("Ratio de La monnaie", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate 1 applicable at the date of the order')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term')
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    partner_id = fields.Many2one('res.partner', string='Client')
    validity_date = fields.Date(string='Validite', readonly=True, copy=False, states={'brouillon': [('readonly', False)], 'sent': [('readonly', False)]},
        help="Validity date of the quotation, after this date, the customer won't be able to validate the quotation online.", default=_default_validity_date)
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]}, help="Delivery address for current sales order.")
    note = fields.Text('Termes Et Condition')


    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })
  

    @api.multi
    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
            'confirmation_date': fields.Datetime.now()
        })

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env['ir.config_parameter'].sudo().get_param('sale.auto_done_setting'):
            self.action_done()
        return True

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('sale.order.yamo') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.order.yamo') or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        result = super(YamoOrder, self).create(vals)
        return result
    
class YamoSaleOrderLine(models.Model):
    _name = 'yamo.sale.order.line'
    _description = 'Sales Order Line'


    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_ids.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_ids.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    order_ids = fields.Many2one('yamo.sale.order', string="reference d'ordre", change_default=True, required=True)
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_id = fields.Many2one('product.product', string='Article', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict')
    product_updatable = fields.Boolean(compute='_compute_product_updatable', string='Can Edit Product', readonly=True, default=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    # product_custom_attribute_value_ids = fields.One2many('product.attribute.custom.value', 'sale_order_line_id', string='User entered custom product attribute values', copy=True)
    name = fields.Text(string='Description', required=True)
    product_no_variant_attribute_value_ids = fields.Many2many('product.template.attribute.value', string='Product attribute values that do not create variants')
    discount = fields.Float(string='Remise (%)', digits=dp.get_precision('Remise'), default=0.0)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

    # Non-stored related field to allow portal user to see the image of the product he has ordered
    product_image = fields.Binary('Product Image', related="product_id.image", store=False, readonly=False)
    product_uom_qty = fields.Float(string='Quantite Commandee', required=True, default=1.0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total', readonly=True, store=True)

    price_unit = fields.Float('Prix Unitaire', required=True, default=0.0)
    # untaxed_amount_invoiced = fields.Monetary("Untaxed Invoiced Amount", compute='_compute_untaxed_amount_invoiced', compute_sudo=True, store=True)
    # untaxed_amount_to_invoice = fields.Monetary("Untaxed Amount To Invoice", compute='_compute_untaxed_amount_to_invoice', compute_sudo=True, store=True)

    currency_id = fields.Many2one(related='order_ids.currency_id', depends=['order_ids.currency_id'], store=True, string='Currency', readonly=True)
    # company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True)
    # order_partner_id = fields.Many2one(related='order_id.partner_id', store=True, string='Customer', readonly=False)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    # analytic_line_ids = fields.One2many('account.analytic.line', 'so_line', string="Analytic lines")
    is_expense = fields.Boolean('Is expense', help="Is true if the sales order line comes from an expense or a vendor bills")
    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when creating invoices from a sales order."
        " They are not copied when duplicating a sales order.")

class YamoSaleMorning(models.Model):
    _name ='yamo.sale.morning'
    _description = 'Recettes Journaliers'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Yamo Order Morning"    


    name = fields.Char(string='Numero de la vente')
    origin = fields.Char(string='Source Document', help="Reference of the document that generated this sales order request.")
    client_order_ref = fields.Char(string='Customer Reference', copy=False)
    reference = fields.Char(string='Payment Ref.', copy=False,
        help='The payment communication of this sale order.')
    state = fields.Selection([
        ('brouillon', 'Devis'),
        ('sent', 'Devis Envoye'),
        ('sale', 'Commande de Vente'),
        ('done', 'Termine'),
        ('cancel', 'Annule'),
        ], string='Etat')
    date_order = fields.Datetime(string='Date de La commande', default=fields.Datetime.now)
    is_expired = fields.Boolean(compute='_compute_is_expired', string="Is expired")
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True, help="Date on which sales order is created.")
    confirmation_date = fields.Datetime(string='Confirmation Date', readonly=True, index=True, help="Date on which the sales order is confirmed.", oldname="date_confirm", copy=False)
    user_id = fields.Many2one('res.users', string='Vendeur', index=True, track_visibility='onchange', track_sequence=2, default=lambda self: self.env.user)
    pricelist_id = fields.Many2one('product.pricelist', string='Liste des Prix')
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True, states={'brouillon': [('readonly', False)], 'sent': [('readonly', False)]}, help="The analytic account related to a sales order.", copy=False, oldname='project_id')
    order_line = fields.One2many('yamo.morning.line', 'order_ids', string='Lignes de Commande')
    amount_untaxed = fields.Monetary(string='Montant Non Taxe', store=True, readonly=True, compute='_amount_all', track_visibility='onchange', track_sequence=5)
    amount_by_group = fields.Binary(string="Montant Taxe Par Groupe", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always', track_sequence=6)
    currency_rate = fields.Float("Ratio de La monnaie", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate 1 applicable at the date of the order')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term')
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    partner_id = fields.Many2one('res.partner', string='Client')
    momo_line = fields.One2many('yamo.momo.line', 'momo_id', string='Mobile Money')
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]}, help="Delivery address for current sales order.")
    note = fields.Text('Termes Et conditions')
    amount_total_momo = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all_momo', track_visibility='always', track_sequence=6)
    amount_momo_product = fields.Monetary(string='Total des Ventes', store=True, readonly=True, compute='_amount_momo_product', track_visibility='always', track_sequence=6)
    

    @api.depends('amount_total_momo','amount_total')
    def _amount_momo_product(self):
        for record in self:
            record.amount_momo_product = record.amount_total_momo + record.amount_total


    @api.multi
    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
                raise UserError(_(
                    'It is not allowed to confirm an order in the following states: %s'
                ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
            'confirmation_date': fields.Datetime.now()
        })

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env['ir.config_parameter'].sudo().get_param('sale.auto_done_setting'):
            self.action_done()
        return True

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })


    @api.depends('momo_line.price_subtotal')
    def _amount_all_momo(self):
        """
        Compute the total amounts of the SO of momo.
        """
        for order in self:
            amount_untaxed = 0.0
            for line in order.momo_line:
                amount_untaxed += line.price_subtotal
            order.update({
                'amount_total_momo': amount_untaxed,
            })

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('receipts.morning.yamo') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('receipts.morning.yamo') or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        result = super(YamoSaleMorning, self).create(vals)
        return result

class YamoSaleOrderMorningLine(models.Model):
    _name ='yamo.morning.line'
    _description = 'Lignes des Recettes Journaliers'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Yamo Order Line"  
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_ids.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_ids.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })


    order_ids = fields.Many2one('yamo.sale.morning', string="reference d'ordre", change_default=True, required=True)
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_id = fields.Many2one('product.product', string='Article', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict')
    product_updatable = fields.Boolean(compute='_compute_product_updatable', string='Can Edit Product', readonly=True, default=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    # product_custom_attribute_value_ids = fields.One2many('product.attribute.custom.value', 'sale_order_line_id', string='User entered custom product attribute values', copy=True)
    discount = fields.Float(string='Remise (%)', digits=dp.get_precision('Remise'), default=0.0)

    product_no_variant_attribute_value_ids = fields.Many2many('product.template.attribute.value', string='Product attribute values that do not create variants')
    # name = fields.Text(string='Description', required=True)
    # Non-stored related field to allow portal user to see the image of the product he has ordered
    product_image = fields.Binary('Product Image', related="product_id.image", store=False, readonly=False)
    product_uom_qty = fields.Float(string='Quantite Commandee', required=True, default=1.0)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_unit = fields.Float('Prix Unitaire', required=True, related='product_id.list_price')
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total', readonly=True, store=True)
    # untaxed_amount_invoiced = fields.Monetary("Untaxed Invoiced Amount", compute='_compute_untaxed_amount_invoiced', compute_sudo=True, store=True)
    # untaxed_amount_to_invoice = fields.Monetary("Untaxed Amount To Invoice", compute='_compute_untaxed_amount_to_invoice', compute_sudo=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

    currency_id = fields.Many2one(related='order_ids.currency_id', depends=['order_ids.currency_id'], store=True, string='Currency', readonly=True)
    # company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True)
    # order_partner_id = fields.Many2one(related='order_id.partner_id', store=True, string='Customer', readonly=False)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    # analytic_line_ids = fields.One2many('account.analytic.line', 'so_line', string="Analytic lines")
    is_expense = fields.Boolean('Is expense', help="Is true if the sales order line comes from an expense or a vendor bills")
    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when creating invoices from a sales order."
        " They are not copied when duplicating a sales order.")

class YamoMomoLine(models.Model):
    _name ='yamo.momo.line'
    _description = 'Paiement Par Mobile Money'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Yamo Order Line"  

    

    designation = fields.Selection([
        ('cash', 'Recette Cash'),
        ('om', 'Recette Orange Money'),
        ('momo', 'Recettes MTN Money'),
        ('online', 'Recette En Ligne'),
        ('yup', 'Recette YUP'),
        ('dep', 'Depenses Caisses'),
        ], string='Designation', default='cash')
    number_command = fields.Integer(string="Nombre de Commande")
    price_unit = fields.Float('Ticket Moyen', required=True, default=0.0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total', readonly=True, store=True)
    momo_id = fields.Many2one('yamo.sale.morning', string='Momo ID', oldname='payment_term')
    momo_id_e = fields.Many2one('yamo.sale.evening', string='Momo ID', oldname='payment_term')
    # price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    currency_id = fields.Many2one(related='momo_id.currency_id', depends=['momo_id.currency_id'], store=True, string='Currency', readonly=True)

    @api.depends('number_command','price_unit')
    def  _compute_amount(self):
        for record in self:
            record.price_subtotal = record.number_command * record.price_unit

class YamoSaleEvening(models.Model):
    """Yamo Order"""
    _name = 'yamo.sale.evening'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Yamo Order"
    
    name = fields.Char(string='Numero de la vente')
    origin = fields.Char(string='Source Document', help="Reference of the document that generated this sales order request.")
    client_order_ref = fields.Char(string='Customer Reference', copy=False)
    reference = fields.Char(string='Payment Ref.', copy=False,
        help='The payment communication of this sale order.')
    state = fields.Selection([
        ('brouillon', 'Devis'),
        ('sent', 'Devis Envoye'),
        ('sale', 'Commande de Vente'),
        ('done', 'Termine'),
        ('cancel', 'Annule'),
        ], string='Etat')
    date_order = fields.Datetime(string='Date de La commande', default=fields.Datetime.now)
    is_expired = fields.Boolean(compute='_compute_is_expired', string="Is expired")
    create_date = fields.Datetime(string='Creation Date', readonly=True, index=True, help="Date on which sales order is created.")
    confirmation_date = fields.Datetime(string='Confirmation Date', readonly=True, index=True, help="Date on which the sales order is confirmed.", oldname="date_confirm", copy=False)
    user_id = fields.Many2one('res.users', string='Vendeur', index=True, track_visibility='onchange', track_sequence=2, default=lambda self: self.env.user)
    pricelist_id = fields.Many2one('product.pricelist', string='Liste des Prix')
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True, states={'brouillon': [('readonly', False)], 'sent': [('readonly', False)]}, help="The analytic account related to a sales order.", copy=False, oldname='project_id')
    order_line = fields.One2many('yamo.evening.line', 'order_ids', string='Lignes de Commande')
    amount_untaxed = fields.Monetary(string='Montant Non Taxe', store=True, readonly=True, compute='_amount_all', track_visibility='onchange', track_sequence=5)
    amount_by_group = fields.Binary(string="Montant Taxe Par Groupe", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always', track_sequence=6)
    currency_rate = fields.Float("Ratio de La monnaie", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate 1 applicable at the date of the order')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term')
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    partner_id = fields.Many2one('res.partner', string='Client')
    # momo_line = fields.One2many('yamo.momo.line', 'momo_id', string='Mobile Money')
    momo_line = fields.One2many('yamo.momo.line', 'momo_id_e', string='Mobile Money')
    # partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]}, help="Delivery address for current sales order.")
    note = fields.Text('Termes Et conditions')
    amount_total_momo = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all_momo', track_visibility='always', track_sequence=6)
    amount_momo_product = fields.Monetary(string='Total des Ventes', store=True, readonly=True, compute='_amount_momo_product', track_visibility='always', track_sequence=6)
    
    @api.depends('amount_total_momo','amount_total')
    def _amount_momo_product(self):
        for record in self:
            record.amount_momo_product = record.amount_total_momo + record.amount_total

    @api.multi
    def action_confirm(self):
        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
            'confirmation_date': fields.Datetime.now()
        })

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env['ir.config_parameter'].sudo().get_param('sale.auto_done_setting'):
            self.action_done()
        return True

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })


    @api.depends('momo_line.price_subtotal')
    def _amount_all_momo(self):
        """
        Compute the total amounts of the SO of momo.
        """
        for order in self:
            amount_untaxed = 0.0
            for line in order.momo_line:
                amount_untaxed += line.price_subtotal
            order.update({
                'amount_total_momo': amount_untaxed,
            })

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('receipts.evening.yamo') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('receipts.evening.yamo') or _('New')

        # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        result = super(YamoSaleEvening, self).create(vals)
        return result

class YamoSaleOrderEveningLine(models.Model):
    """Yamo Order Evening Line"""
    _name = 'yamo.evening.line'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Yamo Order Evening Line"



    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_ids.currency_id, line.product_uom_qty, product=line.product_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })


    order_ids = fields.Many2one('yamo.sale.evening', string="reference d'ordre", change_default=True, required=True)
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    product_id = fields.Many2one('product.product', string='Article', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict')
    product_updatable = fields.Boolean(compute='_compute_product_updatable', string='Can Edit Product', readonly=True, default=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    # product_custom_attribute_value_ids = fields.One2many('product.attribute.custom.value', 'sale_order_line_id', string='User entered custom product attribute values', copy=True)
    discount = fields.Float(string='Remise (%)', digits=dp.get_precision('Remise'), default=0.0)

    product_no_variant_attribute_value_ids = fields.Many2many('product.template.attribute.value', string='Product attribute values that do not create variants')
    # name = fields.Text(string='Description', required=True)
    # Non-stored related field to allow portal user to see the image of the product he has ordered
    product_image = fields.Binary('Product Image', related="product_id.image", store=False, readonly=False)
    product_uom_qty = fields.Float(string='Quantite Commandee', required=True, default=1.0)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_unit = fields.Float('Prix Unitaire', required=True, related='product_id.list_price')
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Sous-total', readonly=True, store=True)
    # untaxed_amount_invoiced = fields.Monetary("Untaxed Invoiced Amount", compute='_compute_untaxed_amount_invoiced', compute_sudo=True, store=True)
    # untaxed_amount_to_invoice = fields.Monetary("Untaxed Amount To Invoice", compute='_compute_untaxed_amount_to_invoice', compute_sudo=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

    currency_id = fields.Many2one(related='order_ids.currency_id', depends=['order_ids.currency_id'], store=True, string='Currency', readonly=True)
    # company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True)
    # order_partner_id = fields.Many2one(related='order_id.partner_id', store=True, string='Customer', readonly=False)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    # analytic_line_ids = fields.One2many('account.analytic.line', 'so_line', string="Analytic lines")
    is_expense = fields.Boolean('Is expense', help="Is true if the sales order line comes from an expense or a vendor bills")
    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when creating invoices from a sales order."
        " They are not copied when duplicating a sales order.")