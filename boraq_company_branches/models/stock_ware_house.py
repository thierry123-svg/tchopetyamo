from odoo import api, fields, models, tools, _

class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    branch_id = fields.Many2one('company.branches', string='Branch', domain="[('company_id','=',company_id)]")
