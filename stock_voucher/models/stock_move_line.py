##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.constrains('qty_done')
    def compute_declared_value(self):
        """ Lo malo de este metodo es que por mas que se escriban varias lineas
        a la vez en un picking odoo lo llama para cada linea. Probamos en el
        write y pasa lo mismo.
        Tambien probamos llevar esto a stock.picking con una constraint sobre
        "move_line_ids" pero solo funciona cuando se modifica desde picking
        y no se se usa el tilde o se va a la vista de procesar operaciones.
        """
        self.mapped('picking_id').compute_declared_value()
