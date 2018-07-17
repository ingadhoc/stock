##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def add_picking_operation(self):
        self.ensure_one()
        view_id = self.env.ref(
            'stock_ux.view_move_line_tree').id
        search_view_id = self.env.ref(
            'stock_ux.stock_move_line_view_search').id
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "search_view_id": search_view_id,
            "views": [[view_id, "tree"], [False, "form"]],
            "domain": [["id", "in", self.move_line_ids.ids]],
            "context": {"create": False},
        }

    @api.onchange('location_id')
    def change_location(self):
        # we only change moves locations if picking in draft
        if self.state == 'draft':
            self.move_lines.update({'location_id': self.location_id.id})

    @api.onchange('location_dest_id')
    def change_location_dest(self):
        # we only change moves locations if picking in draft
        if self.state == 'draft':
            self.move_lines.update(
                {'location_dest_id': self.location_dest_id.id})

    @api.multi
    def action_done(self):
        for picking in self:
            # con esto arreglamos que odoo dejaria entregar varias veces el
            # mismo picking si por alguna razon el boton esta presente
            # en nuestro caso pasaba cuando la impresion da algun error
            # lo que provoca que el picking se entregue pero la pantalla no
            # se actualice
            # antes lo haciamo en do_new_transfer, pero como algunas
            # veces se llama este metodo sin pasar por do_new_transfer
            if picking.state not in ['confirmed', 'assigned']:
                raise UserError(_(
                    'No se puede validar un picking que no esté en estado '
                    'Parcialmente Disponible o Reservado, probablemente el '
                    'picking ya fue validado, pruebe refrezcar la ventana!'))
        return super(StockPicking, self).action_done()

    @api.multi
    def unlink(self):
        """
        To avoid errors we block deletion of pickings in other state than
        draft or cancel
        """
        not_del_pickings = self.filtered(
            lambda x: x.state not in ('draft', 'cancel'))
        if not_del_pickings:
            raise UserError(_(
                'You can only delete draft/cancel pickings. Pikcing Ids: %s') %
                not_del_pickings.ids)
        return super(StockPicking, self).unlink()
