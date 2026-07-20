##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    printed = fields.Boolean()

    with_vouchers = fields.Boolean(
        compute="_compute_with_vouchers",
    )

    next_voucher_number = fields.Integer(
        "Next Voucher Number",
        related="book_id.sequence_id.number_next_actual",
    )

    autoprinted = fields.Boolean(
        related="book_id.autoprinted",
    )

    @api.depends("voucher_ids")
    def _compute_with_vouchers(self):
        for rec in self:
            rec.with_vouchers = bool(self.voucher_ids)

    def do_print_voucher(self):
        self.printed = True
        if self.book_id:
            self.book_id = self.book_id.id
        return super(StockPicking, self).do_print_voucher()

    def do_print_and_assign(self):
        if not self.book_id and self.picking_type_code != "incoming":
            raise UserError("Primero debe seleccionar un talonario")
        if self.autoprinted == False:
            # Talonario preimpreso: la cantidad de remitos debe coincidir con las
            # páginas REALES del reporte. No pre-asignamos por la estimación
            # ``lines_per_voucher`` (subnumera: p. ej. asigna 3 cuando el remito
            # tiene 5 páginas). Imprimimos con ``assign=True`` para que el
            # controller cuente las páginas renderizadas, asigne los números y
            # re-renderice el PDF ya con los números puestos.
            self.printed = True
            return self.with_context(assign=True).do_print_voucher()
        else:
            if self.book_id.sequence_to and int(self.next_voucher_number) > int(self.book_id.sequence_to):
                raise UserError(
                    _(
                        "The voucher number %s exceeds the range specified in the CAI. Please update the range or use a different CAI with a different range.",
                        self.next_voucher_number,
                    )
                )
            self.assign_numbers(1, self.book_id)
            return self.do_print_voucher()

    def button_validate(self):
        # Imprime el remito al validar sólo si el tipo de operación lo pide
        # (``auto_print_delivery_slip``). Autoimpreso: ya numerado en
        # ``_action_done``, sólo imprime. Preimpreso: numera al imprimir por
        # páginas reales (mismo camino que "Imprimir Remito").
        res = super().button_validate()
        if (
            len(self) == 1
            and self.state == "done"
            and self.book_required
            and self.book_id
            and self.picking_type_id.auto_print_delivery_slip
        ):
            if self.autoprinted:
                return self.do_print_voucher()
            return self.do_print_and_assign()
        return res

    def _action_done(self):
        # Los talonarios preimpresos (``autoprinted=False``) se numeran al
        # IMPRIMIR según las páginas reales del reporte, no en la validación por
        # la estimación ``lines_per_voucher``. Los autoimpresos se numeran acá al
        # validar, pero sólo si el tipo de operación pide imprimir el remito al
        # validar (``auto_print_delivery_slip``) — el remito reemplaza al recibo
        # de entrega nativo. Sin ese flag el número se asigna al IMPRIMIR a mano.
        res = super(StockPicking, self.with_context(do_not_assign_numbers=True))._action_done()
        if self._context.get("do_not_assign_numbers"):
            return res
        for picking in self.filtered(
            lambda p: p.book_required
            and p.book_id
            and p.book_id.autoprinted
            and p.picking_type_id.auto_print_delivery_slip
        ):
            picking.assign_numbers(picking.get_estimated_number_of_pages(), picking.book_id)
        return res

    def clean_voucher_data(self):
        return super(StockPicking, self).clean_voucher_data()
