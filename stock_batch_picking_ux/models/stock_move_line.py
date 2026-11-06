##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    origin = fields.Char(
        related="move_id.picking_id.origin",
        # we store so we can group
        store=True,
    )

    def _is_potential_existing_wave_extra(self, wave):
        # No sumar lineas a una ola que ya quedo con traslados incompatibles.
        # El armado automatico de olas (_auto_wave) corre dentro de la reserva
        # de stock, tambien la que dispara el programador de abastecimiento. Si
        # la ola candidata ya contiene un traslado que no entra en sus
        # allowed_picking_ids (estado / empresa / tipo de operacion), agregarle
        # la linea hace saltar stock.picking.batch._sanity_check con un
        # UserError que revierte toda la operacion, y con ella la corrida entera
        # del programador, que entonces nunca avanza y se reintenta sin fin.
        # Descartamos esas olas para que el proceso automatico siga de largo
        # (crea una ola nueva) en lugar de frenarse. El chequeo espeja el del
        # _sanity_check, asi evitamos elegir una ola que lo haria fallar.
        if wave.picking_ids and not (wave.picking_ids <= wave.allowed_picking_ids):
            return False
        return super()._is_potential_existing_wave_extra(wave)
