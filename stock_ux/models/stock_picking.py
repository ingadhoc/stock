# flake8: noqa
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    block_manual_lines = fields.Boolean(
        related='picking_type_id.block_manual_lines',
    )
    observations = fields.Html(
    )

    def unlink(self):
        """
        To avoid errors we block deletion of pickings in other state than
        draft or cancel
        """
        not_del_pickings = self.filtered(
            lambda x: x.picking_type_id.block_picking_deletion or x.state
            not in ('draft', 'cancel'))
        if not_del_pickings:
            raise ValidationError(
                _(
                    'You can not delete this pickings because "Block picking '
                    'deletion" is enable on the picking type/s "%s" '
                    'or the state of the picking is not draft or cancel.\n'
                    'Picking Ids: %s') %
                (','.join(not_del_pickings.mapped('picking_type_id.name')),
                 not_del_pickings.ids))
        return super().unlink()

    def copy(self, default=None):
        self.ensure_one()
        # si no viene default entonces es por interfaz y
        # si tiene bloqueado agregar cantidades entonces
        # tiene bloqueado duplicar
        if not default and self.picking_type_id.block_additional_quantity:
            raise UserError(_(
                'You can not duplicate a Picking because "Block'
                ' Additional Quantity"'
                ' is enable on the picking type "%s"') % (
                self.picking_type_id.name))
        return super().copy(default=default)

    def add_picking_operation(self):
        self.ensure_one()
        view_id = self.env.ref('stock_ux.view_move_line_tree').id
        search_view_id = self.env.ref('stock_ux.stock_move_line_view_search').id
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

    def action_done(self):
        for picking in self:
            # con esto arreglamos que odoo dejaria entregar varias veces el
            # mismo picking si por alguna razon el boton esta presente
            # en nuestro caso pasaba cuando la impresion da algun error
            # lo que provoca que el picking se entregue pero la pantalla no
            # se actualice
            # antes lo haciamo en do_new_transfer, pero como algunas
            # veces se llama este metodo sin pasar por do_new_transfer
            if picking.state in ['done', 'cancel']:
                raise UserError(_(
                    'No se puede validar un picking que no esté en estado '
                    'Parcialmente Disponible o Reservado, probablemente el '
                    'picking ya fue validado, pruebe refrezcar la ventana!'))
        res = super().action_done()
        for rec in self.with_context(mail_notify_force_send=False).filtered('picking_type_id.mail_template_id'):
            try:
                rec.message_post_with_template(rec.picking_type_id.mail_template_id.id)
            except Exception as error:
                title = _(
                    "ERROR: Picking was not sent via email"
                )
                rec.message_post(body="<br/><br/>".join([
                    "<b>" + title + "</b>",
                    _("Please check the email template associated with"
                      " the picking type."),
                    "<code>" + str(error) + "</code>"
                ]),
                )
        return res

    def new_force_availability(self):
        self.action_assign()
        for rec in self.mapped('move_lines').filtered(lambda m: m.state not in ['cancel', 'done']):
            # this two could go together but we keep similar to odoo sm._quantity_done_set
            if not rec.move_line_ids:
                rec.quantity_done = rec.product_uom_qty
            elif len(rec.move_line_ids) == 1:
                rec.quantity_done = rec.product_uom_qty
            else:
                for line in rec.move_line_ids:
                    line.qty_done = line.product_uom_qty

    def _put_in_pack(self, move_line_ids):
        # we send to skip a process of check qty when is sending through the copy method.
        return super()._put_in_pack(move_line_ids.with_context(put_in_pack=True))
