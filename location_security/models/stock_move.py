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
        if not self.env.context.get("button_validate_picking_ids"):
            return True
        user_locations = self.env.user.stock_location_ids
        for user_location in user_locations:
            location = user_locations.search([("id", "child_of", user_location.id)])
            user_locations |= location
        message = _(
            'Invalid Location. You cannot process this picking "%s" since you do not control the location "%s".'
        )

        for rec in moves:
            if self.env.context.get("button_validate_picking_ids") and rec.picking_id.id not in self.env.context.get(
                "button_validate_picking_ids"
            ):
                return True
            elif rec.location_id not in user_locations:
                raise ValidationError(message % (rec.picking_id.name, rec.location_id.name))
            elif rec.location_dest_id not in user_locations:
                raise ValidationError(message % (rec.picking_id.name, rec.location_dest_id.name))
