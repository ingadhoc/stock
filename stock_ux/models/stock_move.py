##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    used_lots = fields.Char(
        compute='_compute_used_lots',
    )
    picking_create_user_id = fields.Many2one(
        'res.users',
        related='picking_id.create_uid',
        string="Picking Creator",
    )
    picking_dest_id = fields.Many2one(
        related='move_dest_ids.picking_id',
        string='Destination Transfer',
    )
    lots_visible = fields.Boolean(
        related='move_line_ids.lots_visible',
    )

    picking_partner_id = fields.Many2one(
        'res.partner',
        'Transfer Destination Address',
        related='picking_id.partner_id',
    )

    origin_description = fields.Char(compute="_compute_origin_description")

    @api.depends(
        'move_line_ids.qty_done',
        'move_line_ids.lot_id',
    )
    def _compute_used_lots(self):
        for rec in self:
            rec.used_lots = ", ".join(
                rec.move_line_ids.filtered('lot_id').mapped(
                    lambda x: "%s (%s)" % (x.lot_id.name, x.qty_done)))

    def _compute_origin_description(self):
        for rec in self:
            if rec.sale_line_id:
                rec.origin_description = rec.sale_line_id.name
            else:
                rec.origin_description = False

    def set_all_done(self):
        self.mapped('move_line_ids').set_all_done()
        for rec in self.filtered(lambda x: not x.move_line_ids):
            rec.quantity_done = rec.product_uom_qty

    @api.constrains('quantity_done')
    def _check_quantity(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        if any(self.filtered(
            lambda x: x.picking_id.picking_type_id.
            block_additional_quantity and float_compare(
                x.product_uom_qty, x.quantity_done,
                precision_digits=precision) == -1)):
            raise ValidationError(_(
                'You can not transfer more than the initial demand!'))

    def action_view_linked_record(self):
        """This function returns an action that display existing sales order
        of given picking.
        """
        self.ensure_one()
        action_ref = self._context.get('action')
        form_view_ref = self._context.get('form_view')
        action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        form_view = self.env.ref(form_view_ref)
        res_id = self._context.get('res_id')
        action['views'] = [(form_view.id, 'form')]
        action['res_id'] = res_id
        return action

    @api.model
    def default_get(self, fields_list):
        # We override the default_get to make stock moves created when the picking
        # was confirmed , this way restrict to add more quantity that initial demand
        defaults = super().default_get(fields_list)
        if self.env.context.get('default_picking_id'):
            picking_id = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
            if picking_id.state == 'confirmed':
                defaults['state'] = 'confirmed'
                defaults['product_uom_qty'] = 0.0
                defaults['additional'] = True
        return defaults

    @api.constrains('state')
    def check_cancel(self):
        if self._context.get('cancel_from_order'):
            return
        if self.filtered(
            lambda x: x.picking_id and x.state == 'cancel' and not self.user_has_groups('stock_ux.allow_picking_cancellation')):
            raise ValidationError("Only User with 'Picking cancelation allow' rights can cancel pickings")
