# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
from dateutil import parser
from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)   

class TchopReport(models.AbstractModel):
    _name = 'report.tchop_etyamo_compta.report_tchop_yamo'
    _description = 'Auxiliar to get the report'

    def _get_folio_data(self, date_start):
        """
        This function return a data dictionnary of product 
        and display it in a Pdf report!!
        """
        total_purchase_cost = 0
        total_production_cost = 0
        total_revenue_cost = 0
        data_folio = []
        yamo_obj = self.env['product.template']
        act_domain = [('checkin_yamo_date', '>=', date_start)]
        tids = yamo_obj.search(act_domain)
        for data in tids:
            checkin_yamo_date = data.checkin_yamo_date.\
                strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            data_folio.append({
                'name': data.name,
                'unique_purchase_cost': data.unique_purchase_cost,
                'purchase_cost': data.purchase_cost,
                'sale_qty': data.sale_qty,
                'unique_production_cost': data.unique_production_cost,
                'production_cost': data.production_cost,
                'qty': data.qty,
                'unique_revenue_cost': data.unique_revenue_cost,
                'revenue_cost': data.revenue_cost,
                'analytic_result': data.analytic_result,
                'analytic_revenue_rate': data.analytic_revenue_rate,
                'margin_rate': data.margin_rate,
                'checkin_yamo_date': parser.parse(checkin_yamo_date),
                # 'checkin': parser.parse(checkin),
                # 'checkout': parser.parse(checkout),
            })
            total_purchase_cost += data.total_purchase_cost
            total_production_cost += data.total_production_cost
            total_revenue_cost += data.total_revenue_cost
        data_folio.append({'total_purchase_cost': total_purchase_cost})
        data_folio.append({'total_production_cost': total_production_cost})
        data_folio.append({'total_revenue_cost': total_revenue_cost})
        return data_folio
        

    @api.model
    def _get_report_values(self, docids, data):
        self.model = self.env.context.get('active_model')
        if data is None:
            data = {}
        if not docids:
            docids = data['form'].get('docids')
        folio_profile = self.env['product.template'].browse(docids)
        date_start = data['form'].get('date_start', fields.Date.today())
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': folio_profile,
            'time': time,
            'tchoptetyamo_data': self._get_folio_data(date_start)
        }
