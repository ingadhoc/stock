# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockProductionlot(models.Model):

    _inherit = 'stock.production.lot'

    qty_available_not_res = fields.Float(
        compute='_compute_qty_available_not_res',
        string='Qty Available Not Reserved',
        store=True
    )

    @api.multi
    @api.depends('quant_ids.reservation_id', 'quant_ids.qty')
    def _compute_qty_available_not_res(self):
        for rec in self:
            # consideramos available si location es internal solamente
            # no filtramos por los no resevados porque pueden estar reservados
            # para el picking actual y entonces no lo muestra
            # and not x.reservation_id
            rec.qty_available_not_res = sum(rec.quant_ids.filtered(
                lambda x: (
                    x.location_id.usage == 'internal')).mapped('qty'))

    @api.multi
    def name_get(self):
        # TODO habria que mejorar y mostrar solo el stock disponible, sacar
        # el reservado excepto para el picking actual
        result = []
        show_locations_qty = self.env.context.get('show_locations_qty')
        for rec in self:
            if show_locations_qty and rec.quant_ids:
                locations = rec.quant_ids.mapped('location_id').filtered(
                    lambda x: x.usage == 'internal')
                locations_qty = ['%s: %s' % (
                    location.name, sum(rec.quant_ids.filtered(
                        lambda x: x.location_id == location).mapped(
                        'qty'))) for location in locations]
                name = locations and '%s (%s)' % (
                    rec.name, ', '.join(locations_qty)) or rec.name
            else:
                name = rec.name
            result.append((rec.id, name))
        return result

    @api.multi
    def validate_lot_quantity(self, quantity, domain):
        for rec in self:
            quants = self.env['stock.quant'].search(
                [('id', 'in', rec.quant_ids.ids)] + domain)
            qty = sum(quants.mapped('qty'))
            if qty < quantity:
                raise UserError(_(
                    'Sending amount can not exceed the quantity in '
                    'stock for this product in the lot.\n'
                    '* Product: %s\n'
                    '* Lot: %s\n'
                    '* Stock: %s') % (
                        rec.product_id.name, rec.name, qty))
