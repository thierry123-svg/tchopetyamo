from odoo import api, fields, models, tools, _

class ResUsers(models.Model):
    _inherit = 'res.users'
    _description = 'Users Branches'
 
    # branch_id  = fields.Many2one('company.branches', string="Branch", domain="[('company_id','=',company_id)]")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    branch_ids = fields.Many2many('company.branches', string='Branches autorisees')
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Work Center', check_company=True)
