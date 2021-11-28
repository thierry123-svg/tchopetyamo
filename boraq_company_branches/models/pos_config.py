from odoo import api, fields, models, tools, _

class PosConfig(models.Model):
    _inherit = "pos.config"

    branch_id = fields.Many2one('company.branches', string='Branch', domain="[('company_id','=',company_id)]")
