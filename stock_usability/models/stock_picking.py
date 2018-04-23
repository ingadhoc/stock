##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # by default picking type is readonly only in done and cancel, we make
    # editable only in draft
    picking_type_id = fields.Many2one(
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

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

    @api.onchange('location_id')
    def change_location(self):
        # we only change moves locations if picking in draft
        if self.state == 'draft':
            for move in self.move_lines:
                move.location_id = self.location_id

    @api.onchange('location_dest_id')
    def change_location_dest(self):
        # we only change moves locations if picking in draft
        if self.state == 'draft':
            for move in self.move_lines:
                move.location_dest_id = self.location_dest_id

    @api.multi
    def do_transfer(self):
        """
        If book required then we assign numbers
        """
        for picking in self:
            # con esto arreglamos que odoo dejaria entregar varias veces el
            # mismo picking si por alguna razon el boton esta presente
            # en nuestro caso pasaba cuando la impresion da algun error
            # lo que provoca que el picking se entregue pero la pantalla no
            # se actualice
            # antes lo haciamo en do_new_transfer, pero como algunas
            # veces se llama este metodo sin pasar por do_new_transfer
            if picking.state not in ['partially_available', 'assigned']:
                raise UserError(_(
                    'No se puede validar un picking que no esté en estado '
                    'Parcialmente Disponible o Reservado, probablemente el '
                    'picking ya fue validado, pruebe refrezcar la ventana!'))
            # esto es principalmente para atrapar error conmanual quants en
            # donde luego de romper reserva y asignar manuales, no hay
            # operaciones
            if not picking.pack_operation_exist:
                raise UserError(_(
                    'No se puede validar un picking que no tiene '
                    'operationes!'))
        return super(StockPicking, self).do_transfer()

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

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    reason = fields.Text('Reason for the return')

    @api.multi
    def _create_returns(self):
        # add to new picking for return the reason for the return
        new_picking, pick_type_id = super(
            StockReturnPicking, self)._create_returns()
        picking = self.env['stock.picking'].browse(new_picking)
        picking.write({'note': self.reason})
        return new_picking, pick_type_id
