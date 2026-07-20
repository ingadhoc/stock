##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models
from odoo.addons.stock_voucher.wizards.stock_backorder_confirmation import (
    StockBackorderConfirmation as VoucherBackorderConfirmation,
)


class StockBackorderConfirmation(models.TransientModel):
    _inherit = "stock.backorder.confirmation"

    def process(self):
        # En Odoo 18 el core re-ejecuta ``button_validate`` sobre los pickings al
        # confirmar el backorder, y ese camino ya imprime el remito (respetando
        # ``auto_print_delivery_slip`` y numerando el preimpreso con assign=True).
        # Saltamos el override de ``stock_voucher``, que reimprimía con
        # ``do_print_voucher`` sin assign (dejaba el preimpreso sin numerar) y
        # devolvía una tupla que el cliente no ejecuta.
        return super(VoucherBackorderConfirmation, self).process()

    def process_cancel_backorder(self):
        return super(VoucherBackorderConfirmation, self).process_cancel_backorder()
