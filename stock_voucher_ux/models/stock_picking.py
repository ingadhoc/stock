<<<<<<< HEAD
||||||| MERGE BASE
=======
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
            rec.with_vouchers = bool(rec.voucher_ids)

    def do_print_voucher(self):
        # El autoimpreso se numera antes del render: el reporte imprime
        # ``o.vouchers or o.name``. El preimpreso, por páginas reales al imprimir.
        if self.autoprinted and not self.voucher_ids:
            self.assign_numbers(1, self.book_id)
        self.printed = True
        if self.book_id:
            self.book_id = self.book_id.id
        return super(StockPicking, self).do_print_voucher()

    def assign_numbers(self, estimated_number_of_pages, book):
        # Único punto por el que pasan todos los caminos de numeración.
        self._check_voucher_cai_range(book, estimated_number_of_pages)
        return super().assign_numbers(estimated_number_of_pages, book)

    def _check_voucher_cai_range(self, book, estimated_number_of_pages):
        """No numerar por encima del tope del CAI (``sequence_to``)."""
        sequence_to = (book.sequence_to or "").strip()
        if not book.autoprinted or not sequence_to.isdigit():
            return
        # ``number_next_actual`` no declara depends y la secuencia se consume con
        # SQL crudo: sin invalidar, el segundo remito de la transacción lee viejo.
        book.sequence_id.invalidate_recordset(["number_next_actual"])
        last_number = book.sequence_id.number_next_actual + estimated_number_of_pages - 1
        if last_number > int(sequence_to):
            raise UserError(
                _(
                    "The voucher number %s exceeds the range specified in the CAI. Please update the range or use a different CAI with a different range.",
                    last_number,
                )
            )

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
            if self.voucher_ids:
                # El botón sigue clickeable después de imprimir: no renumerar.
                return self.do_print_voucher()
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
        # Autoimpreso: un remito de N hojas, un solo número, acá. Preimpreso: al
        # imprimir, tantos como hojas reales tenga el PDF.
        res = super(StockPicking, self.with_context(do_not_assign_numbers=True))._action_done()
        if self._context.get("do_not_assign_numbers"):
            return res
        for picking in self.filtered(lambda p: p.book_required and p.book_id and p.book_id.autoprinted):
            picking.assign_numbers(1, picking.book_id)
        return res

    def clean_voucher_data(self):
        return super(StockPicking, self).clean_voucher_data()

>>>>>>> FORWARD PORTED
