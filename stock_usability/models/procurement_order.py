##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ProcurementOrder(models.Model):

    _inherit = "procurement.order"

    @api.multi
    def button_cancel_remaining(self):
        """
        Esta funcion es similar a la "cancel" de los procurements salvo que
        cancel solo sirve si no hay ningún move en done, con esta funcion
        cancelamos todo lo no done y chequeando que no haya cosas con
        "reservation" para no romper nada o que queden pedidos incompletos (
        sobre todo para dos pasos).

        se llama recursivamente con related procurements ya que no podemos
        simplemente pasar en contexto "cancel_procurement" porque eso
        llamaria a "cancel" y si ya hubo entregas parciales no se van a
        cancelar los procuremets relacionados
        """
        # no permitimos que se cancelen abastecimientos generados
        # automaticamente por moves porque queremos que se cancele el
        # abastecimiento padre mandamos esta clave en contexto para indicar si
        # se llama desde el padre
        from_move_dest = self._context.get('from_move_dest', False)
        for rec in self.filtered(lambda x: x.state != 'done'):
            if rec.move_dest_id and not from_move_dest:
                raise ValidationError(_(
                    'Solo puede cancelar abastecimientos primarios no los '
                    'encadenados'))
            if rec.rule_id.action != 'move':
                raise ValidationError(_(
                    'Cancel remaining in procurements is only implmented for '
                    'rules with action of type "move"'))

            not_done_moves = rec.move_ids.filtered(
                lambda x: x.state != 'done')

            # al final cancelamos por mas que este asignado siempre y cuando
            # no haya procurements relacionados que esten realizados
            # chequeamos contra reserver para que permita cancelar si se forzo
            # disponibilidad o para compras por ejemplo
            # if not_done_moves.filtered(lambda x: x.state == 'assigned'):
            #     raise UserError(_(
            #         'You can not cancel a procurement if it has assigned '
            #         'moves!'))
            # if not_done_moves.filtered(lambda x: x.reserved_quant_ids):
            #     raise ValidationError(_(
            #         'You can not cancel a procurement if it has moves with '
            #         ' reserved quants!\n'
            #         'You should unreserve or confirm related pickings first')

            # verificamos en los moves y no en los procurements porque el proc
            # podria no estar totalmente satisfecho e igual queremos restringir
            # si al menos un move ya fue confirmado
            not_done_moves_related_moves = not_done_moves.search([
                ('move_dest_id', 'in', not_done_moves.ids),
                ('state', '=', 'done'),
            ])
            if not_done_moves_related_moves:
                raise ValidationError(_(
                    'You can not cancel moves that are destination moves '
                    'of already done moves.\n'
                    '* Moves to cancel: %s\n'
                    '* Done moves: %s') % (
                        not_done_moves.ids,
                        not_done_moves_related_moves.ids))

            # similar a como hace sale_stock, vemos la cantidad que representan
            # estos moves que se cancelan y los descontamos del procurement
            # para que si luego, por ejemplo, una venta intenta agregar
            # cantidades, entonces funcione bien
            # qty = 0.0
            # for move in not_done_moves:
            not_done_qty = sum([rec.env['product.uom']._compute_qty_obj(
                x.product_uom, x.product_uom_qty, rec.product_uom) for x in
                not_done_moves])
            not_done_moves.action_cancel()
            rec.product_qty -= not_done_qty

            # ya no seria necesario porque modificamos el action_cancel
            # de los moves ya que no siempre este metodo borraba las operations
            # y quedaban en algunos casos moves cancelados con operations
            # because cancel dont update operations, we re asign
            # not_done_moves.mapped('picking_id').filtered(
            #     lambda x: x.state not in ['draft', 'cancel']).action_assign()

            # al fina buscamos en todos los moves relacionados
            # porque los procurements generados (y parcialmente satsifechos)
            # podrian estar ligados a un move realizado
            related_procurements = rec.search(
                # [('move_dest_id', 'in', not_done_moves.ids)])
                [('move_dest_id', 'in', rec.move_ids.ids)])
            related_procurements.with_context(
                from_move_dest=True).button_cancel_remaining()
            rec.check()
            # TODO tal vez querramos agregar un check de que si el procurement
            # no queda en realizado o cancelado hay que revisar algo
