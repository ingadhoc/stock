##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models, _
from odoo.exceptions import ValidationError


class StockRequestAbstract(models.AbstractModel):
    _inherit = 'stock.request.abstract'

    @api.constrains('company_id', 'product_id', 'warehouse_id',
                    'location_id', 'route_id')
    def _check_company_constrains(self):
        """ Check if the related models have the same company """
        for rec in self:
            # No queremos bloquear por cia de producto ya que puede ser
            # que los productos se compartan entre cias o que sea de cia hija.
            # Se bloquea automaticamente por las reglas de registro y listo
            # if rec.product_id.company_id and \
            #         rec.product_id.company_id != rec.company_id:
            #     raise ValidationError(
            #         _('You have entered a product that is assigned '
            #           'to another company.'))
            if rec.location_id.company_id and \
                    rec.location_id.company_id != rec.company_id:
                raise ValidationError(
                    _('You have entered a location that is '
                      'assigned to another company.'))
            if rec.warehouse_id.company_id != rec.company_id:
                raise ValidationError(
                    _('You have entered a warehouse that is '
                      'assigned to another company.'))
            if rec.route_id and rec.route_id.company_id and \
                    rec.route_id.company_id != rec.company_id:
                raise ValidationError(
                    _('You have entered a route that is '
                      'assigned to another company.'))
