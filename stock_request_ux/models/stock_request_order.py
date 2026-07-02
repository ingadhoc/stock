##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import Command, api, fields, models


class StockRequestOrder(models.Model):
    _inherit = "stock.request.order"
    _order = "id desc"

    warehouse_id = fields.Many2one(
        change_default=True,
    )
    # Referencia generada automáticamente para agrupar los movimientos de la
    # orden en un único picking (análogo a ``sale.order.stock_reference_ids``).
    # Es independiente de ``reference_ids`` (las referencias que carga el
    # usuario a mano) y sirve como anclaje idempotente por orden.
    stock_reference_ids = fields.Many2many(
        "stock.reference",
        "stock_request_order_default_reference_rel",
        "order_id",
        "reference_id",
        string="Default Grouping Reference",
        copy=False,
    )

    @api.onchange("route_id")
    def onchange_route_id(self):
        for line in self.stock_request_ids:
            if self.route_id.id in line.route_ids.ids:
                line.route_id = self.route_id.id

    def _prepare_reference_vals(self):
        self.ensure_one()
        return {"name": self.name}

    def _get_default_stock_reference(self):
        """Referencia por defecto para agrupar los movimientos de la orden.

        En Odoo 19 el agrupamiento de movimientos en un mismo picking dejó de
        basarse en el procurement group y pasa a basarse en ``reference_ids``
        (modelo ``stock.reference``). Un movimiento sin referencia nunca se
        fusiona con un picking existente (ver
        ``stock.move._search_picking_for_assignation``), por lo que sin este
        default cada línea de la orden termina generando su propio picking.

        Generamos (una sola vez) una referencia por orden y la guardamos en
        ``stock_reference_ids`` para que todas sus líneas se agrupen en un único
        picking sin tener que cargar la referencia a mano —replicando el
        comportamiento documentado en el campo ``reference_ids``— y sin depender
        de una búsqueda por nombre (el nombre de la orden es único solo por
        compañía).
        """
        self.ensure_one()
        if not self.stock_reference_ids:
            self.stock_reference_ids = [Command.create(self._prepare_reference_vals())]
        return self.stock_reference_ids
