# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    picking_create_user_id = fields.Many2one(
        'res.users',
        related='picking_id.create_uid',
        string="Picking Creator",
        readonly=True,
    )
    picking_partner_id = fields.Many2one(
        related='picking_id.partner_id',
        store=True,
        readonly=True,
    )
    picking_type_code = fields.Selection(
        related='picking_type_id.code',
        readonly=True,
    )
    product_uom_qty_location = fields.Float(
        compute='compute_product_uom_qty_location',
        string='Net Quantity',
    )
    picking_dest_id = fields.Many2one(
        related='move_dest_id.picking_id',
        readonly=True,
    )

    @api.multi
    def compute_product_uom_qty_location(self):
        location = self._context.get('location')
        if not location:
            return False
        # because now we use location_id to select location, we have compelte
        # location name. If y need we can use some code of
        # _get_domain_locations on stock/product.py
        locations = self.env['stock.location'].search(
            # [('name', 'ilike', location)])
            [('complete_name', 'ilike', location)])
        # from_locations = self.env['stock.location'].search([
        #     '|', ('name', 'ilike', location),
        #     ('location_dest_id', 'ilike', location)
        #     ])
        for rec in self:
            product_uom_qty_location = rec.product_uom_qty
            if rec.location_id in locations:
                # if location is source and destiny, then 0
                if rec.location_dest_id in locations:
                    product_uom_qty_location = 0.0
                else:
                    product_uom_qty_location = -product_uom_qty_location
            rec.product_uom_qty_location = product_uom_qty_location

    @api.multi
    def action_view_linked_record(self):
        """This function returns an action that display existing sales order
        of given picking.
        """
        self.ensure_one()
        action_ref = self._context.get('action_ref')
        form_view_ref = self._context.get('form_view_ref')
        action = self.env.ref(action_ref).read()[0]
        form_view = self.env.ref(form_view_ref)
        res_id = self._context.get('res_id')
        action['views'] = [(form_view.id, 'form')]
        action['res_id'] = res_id
        return action

    @api.multi
    def action_cancel(self):
        """
        Si se cancela un move y hay operations vinculadas, las borramos
        """
        res = super(StockMove, self).action_cancel()
        self.mapped('linked_move_operation_ids.operation_id').with_context(
            force_op_unlink=True).unlink()
        return res
