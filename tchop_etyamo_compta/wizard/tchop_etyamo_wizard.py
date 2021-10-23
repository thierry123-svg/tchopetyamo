# -*- coding: utf-8 -*-
##############################################################################
#   TCHOPETYAMOERP un fork du projet open source Odoo V12.
#   Copyright (C) 2019 Tchopetyamoerp, (<info@ona-itconsulting.com>).
###############################################################################
###############################################################################

from odoo import api, fields, models

class TchopYamoWizard(models.TransientModel):
    _name = 'tchop.yamo.wizard'
    _rec_name = 'date_start'
    _description = 'Allow print folio report by date'

    date_start = fields.Datetime('Start Date')
    date_end = fields.Datetime('End Date')

    
    def print_report(self):
        data = {
            'ids': self.ids,
            'model': 'product.template',
            'form': self.read(['date_start'])[0]
        }
        return self.env.ref('tchop_etyamo_compta.report_yamo_management').\
           report_action(self, data=data)
