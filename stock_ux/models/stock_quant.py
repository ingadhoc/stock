##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class StockQuant(models.Model):
    """ TODO Remove this in v13, all are included in that odoo version
    """
    _inherit = 'stock.quant'

    value = fields.Float('Value', compute='_compute_value', readonly=True)

    @api.depends('product_id.cost_method', 'quantity',
                 'product_id.standard_price')
    def _compute_value(self):
        """ Compute the current accounting valuation of the quants
        by multiplying the quantity bythe standard price. This works well for
        standard and AVCO valuation, while not so much in FIFO because it'll
        estimate the products at their last delivery price and not their real
        value.
        """
        for quant in self:
            quant.value = quant.quantity * quant.product_id.standard_price

    @api.model
    def read_group(
            self, domain, fields, groupby, offset=0, limit=None, orderby=False,
            lazy=True):
        """ This override is done in order for the grouped list view to display
        the total value of the quants inside a location. This doesn't work out
        of the box because `value` is a computed
        field.
        """
        if 'value' not in fields:
            return super().read_group(
                domain, fields, groupby, offset=offset, limit=limit,
                orderby=orderby, lazy=lazy)
        res = super().read_group(
            domain, fields, groupby, offset=offset, limit=limit,
            orderby=orderby, lazy=lazy)
        for group in res:
            if group.get('__domain'):
                quants = self.search(group['__domain'])
                group['value'] = sum(quant.value for quant in quants)
        return res
