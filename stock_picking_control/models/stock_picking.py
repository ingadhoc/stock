##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    block_additional_quantiy = fields.Boolean(
        related='picking_type_id.block_additional_quantiy',
        readonly=True,
    )

    @api.multi
    def unlink(self):
        """
        To avoid errors we block deletion of pickings in other state than
        draft or cancel
        """
        not_del_pickings = self.filtered(
            lambda x: x.picking_type_id.block_picking_deletion)
        if not_del_pickings:
            raise ValidationError(_(
                'You can not delete this pickings because "Block picking '
                'deletion" is enable on the picking type "%s".\n'
                'Picking Ids: %s') % (
                    not_del_pickings.ids, self.picking_type_id.name))
        return super(StockPicking, self).unlink()
