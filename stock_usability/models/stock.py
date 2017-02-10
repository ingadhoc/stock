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


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def add_picking_operation(self):
        self.ensure_one()
        view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'stock_usability.view_stock_pack_operation_tree')
        search_view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'stock_usability.view_pack_operation_search')
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.pack.operation",
            "search_view_id": search_view_id,
            "views": [[view_id, "tree"], [False, "form"]],
            "domain": [["id", "in", [
                x.id for x in self.pack_operation_product_ids]]],
            "context": {"create": False},
        }
