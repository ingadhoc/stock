##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class StockRequestOrder(models.Model):
    _inherit = 'stock.request.order'
    _order = 'id desc'

    stock_request_ids = fields.One2many(
        copy=True,
    )
    # este pickings es analogo al pickings de venta pero implementado mas facil
    # odoo en ventas agrega un campo en el procurement group y related en
    # picking pero a la larga esta trayendo todos los pickings que tengan
    # el procurment group de la venta. Nosotros hacemos similar buscando los
    # pickings que tengan mismo procurement group que el request order
    # como al final tmb se puede cancelar una linea (stock request), lo
    # implementamos en las lineas directamente el cancelar
    picking_ids = fields.One2many(
        compute='_compute_picking_ids',
    )
    picking_count = fields.Integer(
        compute='_compute_picking_ids',
    )
    procurement_group_id = fields.Many2one(
        copy=False,
    )
    warehouse_id = fields.Many2one(
        change_default=True,
    )

    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        sro_with_procurement = self.filtered('procurement_group_id')
        (self - sro_with_procurement).update({
            'picking_ids': self.env['stock.picking'],
            'picking_count': 0
            })
        for rec in sro_with_procurement:
            all_moves = self.env['stock.move'].search(
                [('group_id', '=', rec.procurement_group_id.id)]
            )
            rec.picking_ids = all_moves.mapped('picking_id')
            rec.picking_count = len(rec.picking_ids)

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            if not rec.procurement_group_id:
                # setamos al group el partner del warehouse para que se propague
                # a los pickings
                group = self.env['procurement.group'].create({})
                rec.procurement_group_id = group.id
                for stock_rq in rec.stock_request_ids:
                    stock_rq.write(
                        {'procurement_group_id': rec.procurement_group_id.id})
        return recs

    @api.onchange('route_id')
    def onchange_procurement_group_id(self):
        for line in self.stock_request_ids:
            if self.route_id.id in line.route_ids.ids:
                line.route_id = self.route_id.id
