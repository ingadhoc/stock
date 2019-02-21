##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    used_lots = fields.Char(
        compute='_compute_used_lots',
    )
    picking_create_user_id = fields.Many2one(
        'res.users',
        related='picking_id.create_uid',
        string="Picking Creator",
        readonly=True,
    )
    picking_dest_id = fields.Many2one(
        related='move_dest_ids.picking_id',
        readonly=True,
    )
    lots_visible = fields.Boolean(
        related='move_line_ids.lots_visible',
        readonly=True,
    )

    @api.depends(
        'move_line_ids.qty_done',
        'move_line_ids.lot_id',
    )
    def _compute_used_lots(self):
        for rec in self:
            rec.used_lots = ", ".join(
                rec.move_line_ids.filtered('lot_id').mapped(
                    lambda x: "%s (%s)" % (x.lot_id.name, x.qty_done)))

    @api.multi
    def set_all_done(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for rec in self:
            rec.quantity_done = rec.reserved_availability\
                if not float_is_zero(
                    rec.reserved_availability,
                    precision_digits=precision) else\
                rec.product_uom_qty

    @api.constrains('quantity_done')
    def _check_quantity(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for rec in self.filtered(
            lambda
            x: x.picking_id.picking_type_id.
            block_additional_quantity and float_compare(
                x.product_uom_qty, x.quantity_done,
                precision_digits=precision) == -1):
            raise ValidationError(_(
                'You can not transfer more than the initial demand!'))

    @api.multi
    def _cancel_quantity(self, quantity=None, stream=None):
        """ Metodo que para un conjunto de moves (self), de mismo producto,
        trata de cancelar una cantidad (quantity)
        NOTA: no exigimos igual picking ya que se pudieron generar
        backorders
        """
        def propagate(move, quantity, stream=None):
            # import pdb; pdb.set_trace()
            if not stream or stream == "downstream":
                move.move_orig_ids._cancel_quantity(quantity, "downstream")
            if not stream or stream == "upstream":
                move.move_dest_ids._cancel_quantity(quantity, "upstream")

        if not self:
            return True

        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')

        product = self.mapped('product_id')
        # picking = self.mapped('picking_id')
        if len(product) != 1:
            raise ValidationError(_(
                'Error de programación. Se llamó a cancel quantity para '
                'movimientos de distintos productos y/o pickings.\n'
                '* Id de Movimientos: %s\n'
                '* Productos: %s' % (
                    self.ids,
                    ', '.join(product.mapped('display_name')),
                )))
        # if len(product) != 1 or \
        #    len(picking) != 1:
        #     raise ValidationError(_(
        #         'Error de programación. Se llamó a cancel quantity para '
        #         'movimientos de distintos productos y/o pickings.\n'
        #         '* Id de Movimientos: %s\n'
        #         '* Productos: %s\n'
        #         '* Pickings: %s' % (
        #             self.ids,
        #             ', '.join(product.mapped('display_name')),
        #             ', '.join(picking.mapped('display_name')),
        #         )))

        active_moves = self.filtered(
            lambda x: x.state not in ['done', 'cancel'])

        available_to_cancel = sum(active_moves.mapped('product_qty'))

        if not quantity:
            to_cancel = available_to_cancel
        else:
            to_cancel = quantity

        if float_compare(
           to_cancel, available_to_cancel, precision_digits=precision) > 0:
            raise ValidationError(_(
                'No hay suficiente cantidad disponible para cancelar.\n'
                'Probablemente deba finalizar primero los movimientos '
                'encandenados con disponibilidad.'
                '* Id de Movimientos: %s\n'
                '* Producto (id): %s (%s)\n'
                '* Pickings: %s\n'
                '* Cantidad a cancelar: %s\n'
                '* Cantidad disponible para cancelar: %s' % (
                    self.ids,
                    product.display_name, product.id,
                    ', '.join(active_moves.mapped('picking_id.display_name')),
                    quantity,
                    available_to_cancel,
                )))

        for move in active_moves:

            compare = float_compare(
                to_cancel, move.product_qty, precision_digits=precision)

            # import pdb; pdb.set_trace()
            if compare > 0:
                # mas a cancelar que lo disponible
                # cancelamos movimiento y dejamos remanente para proximo
                # to_cancel = min(remaining_to_cancel, move.product_qty)
                propagate(move, quantity=to_cancel, stream=stream)
                move._action_cancel()
                to_cancel -= move.product_qty
            if compare < 0:
                # cancelar parcialmente un movimiento, lo dividimos y
                # cancelamos el nuevo
                propagate(move, quantity=to_cancel, stream=stream)
                self.browse(move._split(to_cancel))._action_cancel()
                move._do_unreserve()
                move._action_assign()
                break
            else:
                # si son iguales directamente cancelamos el move
                propagate(move, quantity=to_cancel, stream=stream)
                move._action_cancel()
                break

    # @api.multi
    # def _cancel_quantity(self, quantity, stream):
    #     """ Metodo que para un conjunto de moves (self), de mismo producto,
    #     trata de cancelar una cantidad (quantity)
    #     NOTA: no exigimos igual picking ya que se pudieron generar
    #     backorders
    #     """

    #     if not self:
    #         return True

    #     precision = self.env['decimal.precision'].precision_get(
    #         'Product Unit of Measure')

    #     product = self.mapped('product_id')
    #     # picking = self.mapped('picking_id')
    #     if len(product) != 1:
    #         raise ValidationError(_(
    #             'Error de programación. Se llamó a cancel quantity para '
    #             'movimientos de distintos productos y/o pickings.\n'
    #             '* Id de Movimientos: %s\n'
    #             '* Productos: %s' % (
    #                 self.ids,
    #                 ', '.join(product.mapped('display_name')),
    #             )))
    #     # if len(product) != 1 or \
    #     #    len(picking) != 1:
    #     #     raise ValidationError(_(
    #     #         'Error de programación. Se llamó a cancel quantity para '
    #     #         'movimientos de distintos productos y/o pickings.\n'
    #     #         '* Id de Movimientos: %s\n'
    #     #         '* Productos: %s\n'
    #     #         '* Pickings: %s' % (
    #     #             self.ids,
    #     #             ', '.join(product.mapped('display_name')),
    #     #             ', '.join(picking.mapped('display_name')),
    #     #         )))

    #     active_moves = self.filtered(
    #         lambda x: x.state not in ['done', 'cancel'])

    #     available_to_cancel = sum(active_moves.mapped('product_qty'))

    #     if float_compare(
    #        quantity, available_to_cancel, precision_digits=precision) > 0:
    #         raise ValidationError(_(
    #             'No hay suficiente cantidad disponible para cancelar.\n'
    #             'Probablemente deba finalizar primero los movimientos '
    #             'encandenados con disponibilidad.'
    #             '* Id de Movimientos: %s\n'
    #             '* Producto (id): %s (%s)\n'
    #             '* Pickings: %s\n'
    #             '* Cantidad a cancelar: %s\n'
    #             '* Cantidad disponible para cancelar: %s' % (
    #                 self.ids,
    #                 product.display_name, product.id,
    #                 ', '.join(active_moves.mapped('picking_id.display_name')),
    #                 quantity,
    #                 available_to_cancel,
    #             )))

    #     to_cancel = quantity
    #     for move in active_moves:
    #         # if not to_cancel:
    #         #     break

    #         compare = float_compare(
    #             to_cancel, move.product_qty, precision_digits=precision)

    #         # import pdb; pdb.set_trace()
    #         if compare > 0:
    #             # mas a cancelar que lo disponible
    #             # cancelamos movimiento y dejamos remanente para proximo
    #             # to_cancel = min(remaining_to_cancel, move.product_qty)
    #             move.cancel_move(stream=stream)
    #             to_cancel -= move.product_qty
    #         if compare < 0:
    #             # cancelar parcialmente un movimiento, lo dividimos y
    #             # cancelamos el nuevo
    #             self.browse(move._split(to_cancel)).cancel_move(stream=stream)
    #             move._do_unreserve()
    #             move._action_assign()
    #             break
    #         else:
    #             # si son iguales directamente cancelamos el move
    #             move.cancel_move(stream=stream)
    #             break

    # def cancel_move(self, stream=None):
    #     """ Cancelación de un movimiento y sus movimientos vinculados
    #     segun especificado en stream (para arriba o para bajo o ambos)
    #     Por lo general el movimiento original se cancela sin definir stream
    #     pero luego los llamados recurrentes a partir de _cancel_quantity
    #     se hacen en un solo sentido para no terminar siendo recursivo.
    #     Se podria haber integrado esta funcionalidad en _action_cancel
    #     pero nos pareció más prolijo dejarla separada en otro método
    #     """
    #     # if self._context.get('cancel_related_moves'):
    #     # if self._context.get('cancel_dest_moves') and self._context.get('cancel_orig_moves'):
    #     #     raise ValidationError(_(
    #     #         'Error de programación. No se puede cancelar propgragando '
    #     #         'hacia movimientos origen y destino a la vez!'))
    #     for rec in self:
    #         # import pdb; pdb.set_trace()
    #         # move_origs = rec.move_orig_ids
    #         # move_dests = rec.move_dest_ids
    #         if not stream or stream == "downstream":
    #             rec.move_orig_ids._cancel_quantity(
    #                 rec.product_qty, "downstream")
    #         if not stream or stream == "upstream":
    #             rec.move_dest_ids._cancel_quantity(
    #                 rec.product_qty, "upstream")
    #         rec._action_cancel()

    # def _action_cancel(self):
    #     """ Agregamos para que si mandamos "cancel_related_moves" en contexto
    #     entonces cancelamos los movimientos de origen.
    #     """
    #     precision = self.env['decimal.precision'].precision_get(
    #         'Product Unit of Measure')
    #     # we save this recordset because odoo cleans "move_orig_ids" on super
    #     all_moves_origs = self.env['stock.move']
    #     all_moves_dests = self.env['stock.move']
    #     # if self._context.get('cancel_related_moves'):
    #     # if self._context.get('cancel_dest_moves') and self._context.get('cancel_orig_moves'):
    #     #     raise ValidationError(_(
    #     #         'Error de programación. No se puede cancelar propgragando '
    #     #         'hacia movimientos origen y destino a la vez!'))
    #     if self._context.get('cancel_dest_moves'):
    #         for rec in self.filtered('move_dest_ids'):
    #             move_dests = rec.move_dest_ids.filtered(lambda x: x.state != 'done')
    #             if float_compare(
    #                     sum(move_dests.mapped('product_qty')),
    #                     rec.product_qty, precision_digits=precision) != 0:
    #                 raise ValidationError(_(
    #                     'No puede cancelar el movimiento "%s" y los '
    #                     'movimientos vinculados al mismo porque la '
    #                     'cantidad del mismo (%s) es distinta a la cantidad '
    #                     'de los movimientos vinculados no realizados (%s).\n'
    #                     'Probablemente deba finalizar primero los movimientos '
    #                     'encandenados con disponibilidad') % (
    #                         rec.display_name,
    #                         rec.product_qty,
    #                         sum(move_dests.mapped('product_qty')),
    #                     ))
    #             all_moves_dests |= move_dests

    #     if self._context.get('cancel_orig_moves'):
    #         for rec in self.filtered('move_orig_ids'):
    #             move_origs = rec.move_orig_ids.filtered(
    #                 lambda x: x.state != 'done')
    #             if float_compare(
    #                     sum(move_origs.mapped('product_qty')),
    #                     rec.product_qty, precision_digits=precision) != 0:
    #                 raise ValidationError(_(
    #                     'No puede cancelar el movimiento "%s" y los '
    #                     'movimientos vinculados al mismo porque la '
    #                     'cantidad del mismo (%s) es distinta a la cantidad '
    #                     'de los movimientos vinculados no realizados (%s).\n'
    #                     'Probablemente deba finalizar primero los movimientos '
    #                     'encandenados con disponibilidad') % (
    #                         rec.display_name,
    #                         rec.product_qty,
    #                         sum(move_origs.mapped('product_qty')),
    #                     ))
    #             all_moves_origs |= move_origs
    #     res = super(StockMove, self)._action_cancel()

    #     # si propoagamos para abajo no queremos que esos movimientos disparen
    #     # propagar para arriba tambien (y viceversa)
    #     if all_moves_dests:
    #         all_moves_dests.with_context(
    #             cancel_orig_moves=False)._action_cancel()

    #     if all_moves_origs:
    #         all_moves_origs.with_context(
    #             cancel_dest_moves=False)._action_cancel()
    #     return res
