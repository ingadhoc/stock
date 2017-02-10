# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from openerp import models, fields, api
from datetime import timedelta, datetime
import openerp.addons.decimal_precision as dp
# from openerp.tools import float_compare, float_is_zero
# from openerp.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    rotation = fields.Float(
        help='Cantidades entregadas a clientes en los '
        'últimos 90 días dividido por 3 para mensualizar '
        '(restadas devoluciones).',
        compute='_compute_rotation',
        digits=dp.get_precision('Product Unit of Measure'),
    )
    location_rotation = fields.Float(
        help='Cantidades entregadas desde esta ubicación a clientes en los '
        'últimos 90 días dividido por 3 para mensualizar'
        '(restadas devoluciones).',
        compute='_compute_rotation',
        digits=dp.get_precision('Product Unit of Measure'),
    )

    @api.multi
    @api.depends('product_id', 'location_id')
    def _compute_rotation(self):
        for rec in self:
            from_date = fields.Datetime.to_string(
                datetime.now() + timedelta(-90))
            base_domain = [
                ('date', '>=', from_date),
                ('state', '=', 'done'),
                ('product_id', '=', rec.product_id.id),
            ]
            base_domain_send = base_domain + [
                ('location_dest_id.usage', '=', 'customer')]
            base_domain_return = base_domain + [
                ('location_id.usage', '=', 'customer')]

            # from any location to customers
            rotation = sum(rec.env['stock.move'].search(
                base_domain_send).mapped('product_qty'))
            # from customers to any location
            rotation -= sum(rec.env['stock.move'].search(
                base_domain_return).mapped('product_qty'))

            # from location to customers
            location_rotation = sum(rec.env['stock.move'].search(
                base_domain_send + [('location_id', '=', rec.location_id.id)]
            ).mapped('product_qty'))
            # from customers to location
            location_rotation -= sum(rec.env['stock.move'].search(
                base_domain_return + [
                    ('location_dest_id', '=', rec.location_id.id)]
            ).mapped('product_qty'))

            rec.rotation = rotation / 3.0
            rec.location_rotation = location_rotation / 3.0
