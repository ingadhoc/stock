from openerp import fields, models, _

class stock_picking(models.Model):

    _inherit = 'stock.picking'

    driver_id = fields.Many2one(
        'res.partner',
        'Driver')

    vehicle_license_plate = fields.Char(
        'License Plate')

    # TODO: if fleet is installed, and distribution is made by
    # company, it should show license plate from fleet
