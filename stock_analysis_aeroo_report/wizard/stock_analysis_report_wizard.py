##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class StockAnalysisReportWizard(models.TransientModel):
    _name = 'stock.analysis.report.wizard'
    _description = 'Stock Analysis Report Wizard'

    from_date = fields.Date(
        'From',
        default=(datetime.now()-relativedelta(months=12)).strftime('%Y-%m-01'),
        help='Leave empty to analize moves from all time. (Not recommended)',
    )

    to_date = fields.Date('To')

    # If a location is set, internal moves will be analized too.
    # Otherwise, only outgoing moves.
    location_id = fields.Many2one(
        'stock.location',
        'Location',
        domain=[('usage', '=', 'internal')],
        help="Leave empty to analize moves from all locations."
    )

    company_id = fields.Many2one(
        'res.company',
        'Company',
        groups='base.group_multi_company',
        help="Leave empty to analize moves from all companies."
    )

    filter_domain = fields.Char(
        'Filter Products',
        help="Leave empty to analyze moves from all products."
    )

    show_stock_valuation = fields.Boolean(
        'Stock Valuation',
        groups='account.group_account_user')

    show_computed_monthly_demand = fields.Boolean(
        'Monthly Demand')

    show_computed_stock_remaining_months = fields.Boolean(
        'Remaining Months')

    show_stock_reordering_rules = fields.Boolean(
        'Reordering Rules')

    show_computed_reordering_suggestion = fields.Boolean(
        'Suggest New Reordering Rules')

    @api.constrains(
        'show_computed_monthly_demand',
        'show_computed_stock_remaining_months',
        'show_computed_reordering_suggestion',
    )
    def _check_computed_fields(self):
        if not self.show_computed_monthly_demand:
            if self.show_computed_stock_remaining_months:
                raise ValidationError(_(
                    'To show computed remaining months, '
                    'monthly demand needs to be calculated too.'))
            if self.show_computed_reordering_suggestion:
                raise ValidationError(_(
                    'To show computed reordering suggestion, '
                    'monthly demand needs to be calculated too.'))

    @api.constrains(
        'location_id',
        'show_stock_reordering_rules',
    )
    def _check_reordering_location(self):
        if not self.location_id and self.show_stock_reordering_rules:
            raise ValidationError(_(
                'In order to show reordering rules, '
                'you need to select a location.'))

    @api.multi
    def confirm(self):
        products = self.env['product.product'].browse(self.filter_domain)
        return self.env.ref(
            'stock_analysis_aeroo_report.action_aeroo_stock_analysis_report'
            ).with_context(self.read()[0]).report_action(products)
