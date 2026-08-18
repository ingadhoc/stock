##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def write(self, vals):
        """Archivar o reactivar una sucursal cambia los almacenes que quedan
        en juego, así que hay que revisar el permiso "Gestionar varios
        almacenes": el nativo solo lo revisa al tocar un almacén, y archivar
        una compañía no archiva los suyos."""
        res = super().write(vals)
        if "active" in vals:
            self.env["stock.warehouse"]._check_multiwarehouse_group()
        return res
