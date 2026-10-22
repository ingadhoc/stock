##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import _, api, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.constrains("state", "location_id", "location_dest_id")
    def check_user_location_rights(self):
        # (b) Cancelar un movimiento no procesa mercadería: solo validamos los
        # movimientos que pasan a "done". Los movimientos encadenados que quedan
        # en "cancel" al modificar/confirmar una OC con ruta MTO no deben
        # disparar la constraint. Ver ticket 109676.
        moves = self.filtered(lambda x: x.state == "done")
        if not moves or not self.env.user.restrict_locations:
            return True
        # (a) La verificación de ubicaciones permitidas pertenece a la validación
        # explícita del picking (botón "Validar"). Fuera de ese flujo la
        # constraint se dispara por efectos colaterales (ej. recreación de
        # movimientos encadenados MTO) generando falsos positivos de
        # "Invalid Location". Ver ticket 109676.
        picking_ids = self.env.context.get("button_validate_picking_ids")
        if not picking_ids:
            return True
        # Solo los movimientos de los pickings que se están validando.
        moves = moves.filtered(lambda x: x.picking_id.id in picking_ids)
        user_locations = self.env.user._get_allowed_stock_locations()
        for picking, picking_moves in moves.grouped("picking_id").items():
            denied = (picking_moves.location_id | picking_moves.location_dest_id) - user_locations
            if denied:
                raise ValidationError(
                    _(
                        'Invalid Location. You cannot process the transfer "%(picking)s" since you do not control '
                        "these locations: %(locations)s.",
                        picking=picking.name,
                        locations=", ".join(denied.mapped("display_name")),
                    )
                )
