##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockBook(models.Model):
    _inherit = "stock.book"

    autoprinted = fields.Boolean(
        help="If voucher is not an autoprinted, it will assign as many vouchers as pages the report has. "
        "Otherwise, it will assign only one voucher",
    )
    sequence_to = fields.Char(
        help="Número límite superior hasta el cual se puede usar este libro de stock. "
        "Deje el campo vacío para indicar sin límite. Si ingresa un valor, se completará automáticamente con ceros a la izquierda hasta 8 dígitos.",
        required=False,
    )

    @api.onchange("sequence_to")
    def _add_padding_to_sequence_to(self):
        if self.sequence_to:
            self.sequence_to = self.sequence_to.zfill(8)
