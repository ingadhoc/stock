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

    def _get_voucher_report(self):
        """Reporte que efectivamente se imprime como remito para este picking: el
        recibo de entrega nativo, o el remito que lo sustituye cuando
        ``report_substitute`` tiene una regla para su talonario."""
        self.ensure_one()
        report = self.env.ref("stock.action_report_delivery")
        # ``report_substitute`` es opcional: sin él el reporte es el nativo.
        if hasattr(report, "get_substitution_report"):
            report = report.get_substitution_report(self.ids)
        return report

    def _assign_preprinted_numbers(self):
        """Numera los remitos preimpresos server-side, según las páginas reales.

        El camino de impresión numera en el controller ``/report/download`` o en
        ``render_and_send`` (IoT), y los dos dependen de que un cliente web ejecute
        la acción de reporte. Cuando valida una automatización server-side —la de
        entregas del tipo de pedido de venta— esa acción se descarta y el remito
        queda validado sin número. Numerando acá los otros dos caminos quedan
        no-op, porque ambos chequean que no haya números todavía.
        """
        for picking in self.filtered(lambda p: p.book_id and not p.book_id.autoprinted and not p.voucher_ids):
            number_of_pages = picking._get_voucher_report()._count_voucher_pages(picking)
            # Sin páginas reales no inventamos una cantidad: que numere el camino
            # de impresión, como antes.
            if number_of_pages:
                picking.assign_numbers(number_of_pages, picking.book_id)

    def do_print_and_assign(self):
        if not self.book_id and self.picking_type_code != "incoming":
            raise UserError("Primero debe seleccionar un talonario")
        if self.autoprinted == False:
            # Talonario preimpreso: la cantidad de remitos debe coincidir con las
            # páginas REALES del reporte. No pre-asignamos por la estimación
            # ``lines_per_voucher`` (subnumera: p. ej. asigna 3 cuando el remito
            # tiene 5 páginas). Numeramos server-side contando las páginas del
            # render, así el número no depende de que alguien ejecute la acción que
            # devolvemos, e imprimimos con ``assign=True`` para que el controller
            # numere igual si acá no se pudo renderizar.
            self.printed = True
            self._assign_preprinted_numbers()
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
