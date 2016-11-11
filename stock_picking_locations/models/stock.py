# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    new_location_id = fields.Many2one(
        'stock.location', 'Source Location',
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'waiting': [('readonly', False)],
            'confirmed': [('readonly', False)],
        },
        help="Sets a location if you produce at a fixed location.\
         This can be a partner location if you subcontract the'\
          manufacturing operations. This will be the default of \
          the asociated stock moves.")
    new_location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'waiting': [('readonly', False)],
            'confirmed': [('readonly', False)],
        },
        help="Location where the system will stock the finished products.\
         This will be the default of the asociated stock moves.")

    @api.one
    def update_locations(self):
        vals = {
            'location_id': self.new_location_id.id,
            'location_dest_id': self.new_location_dest_id.id
        }
        self.move_lines.write(vals)
