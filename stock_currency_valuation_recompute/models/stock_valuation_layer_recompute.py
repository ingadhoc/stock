<<<<<<< HEAD
||||||| MERGE BASE
=======
import logging
import time

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Segundos de trabajo por invocacion del cron. No es un tope de lo que se puede encolar:
# el cron reporta cuantos quedan y Odoo lo relanza enseguida hasta vaciar la cola.
#
# Es un presupuesto de tiempo y no una cantidad de registros porque lo que hay que no
# pasarse es el `--limit-time-real-cron` del worker (por defecto cae en
# `--limit-time-real`, 120 segundos): pasado ese tiempo mata el thread. Un numero fijo de
# registros no protege eso, porque revaluar un producto con 500 layers no cuesta lo mismo
# que uno con 5.
#
# El valor es chico porque el presupuesto es POR INVOCACION y no por thread:
# `ir.cron._run_job` reinvoca el callback hasta `MAX_BATCH_PER_CRON_JOB` (10) veces
# seguidas mientras quede trabajo, commiteando entre una y otra. Diez invocaciones tienen
# que entrar en el limite del worker, asi que el presupuesto va en el orden de un decimo.
REVALUATION_TIME_BUDGET = 10


class StockValuationLayerRecompute(models.Model):
    _name = "stock.valuation.layer.recompute"
    _description = "layer recompute"

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    product_id = fields.Many2one("product.product", string="Product", readonly=False)
    valuation_currency_id = fields.Many2one(
        "res.currency", string="Secondary Currency Valuation", compute="_compute_valuation_currency_id"
    )
    initial_amount = fields.Monetary()
    final_amount = fields.Monetary()
    initial_amount_in_currency = fields.Monetary()
    final_amount_in_currency = fields.Monetary()
    line_ids = fields.One2many(
        comodel_name="stock.valuation.layer.recompute.line",
        inverse_name="recompute_id",
    )
    last_manual_svl_id = fields.Many2one("stock.valuation.layer")
    amount_changed = fields.Boolean()
    slv_changed = fields.Boolean()
    revaluation_error = fields.Text(readonly=True, copy=False)
    final_rate = fields.Float(
        compute="_compute_final_rate",
        store=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_process", "In Process"),
            ("revaluating", "Revaluating"),
            ("done", "Done"),
            ("no_change", "Not changes Required"),
            ("error", "Error"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        string="Status",
        required=True,
        readonly=True,
        copy=False,
    )

    @api.depends("final_amount", "final_amount_in_currency")
    def _compute_final_rate(self):
        for rec in self:
            if rec.final_amount_in_currency:
                rec.final_rate = rec.final_amount / rec.final_amount_in_currency
            else:
                rec.final_rate = 0.0

    @api.onchange("product_id", "company_id")
    def _onchange_product_id(self):
        self.line_ids = False
        self.final_amount_in_currency = False

    @api.depends("product_id", "company_id")
    def _compute_valuation_currency_id(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            rec.valuation_currency_id = product_id.categ_id.valuation_currency_id

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"

    def back_to_draft(self):
        for rec in self:
            rec.state = "draft"

    def _get_manual_svl_domain(self):
        """Ajustes manuales del producto: un layer cargado a mano no tiene movimiento de
        stock, ni linea de factura, ni landed cost.

        No se filtra por `create_uid`: el ajuste lo carga quien opera, no un usuario
        tecnico, y filtrarlo hace que no se encuentre ninguno y se recalcule tambien lo
        anterior al ajuste, que es justamente lo que hay que respetar.

        `account_move_line_id` descarta las diferencias de precio de factura, que tampoco
        tienen movimiento de stock pero no son un ajuste manual: si se cuelan, el corte
        queda despues del ajuste real y deja sin recalcular layers que si correspondian.
        """
        return [
            ("company_id", "=", self.company_id.id),
            ("product_id", "=", self.product_id.id),
            ("stock_move_id", "=", False),
            ("account_move_line_id", "=", False),
            ("stock_landed_cost_id", "=", False),
        ]

    def _prepare_new_values(self, from_currency_id, to_currency_id, qty, unit_cost, layer_date, manual_currency_rate=0):
        is_company_currency = from_currency_id == self.company_id.currency_id
        if manual_currency_rate and is_company_currency:
            new_unit_cost_in_to_currency = unit_cost * manual_currency_rate
        elif manual_currency_rate and not is_company_currency:
            new_unit_cost_in_to_currency = unit_cost / manual_currency_rate
        else:
            new_unit_cost_in_to_currency = from_currency_id._convert(
                from_amount=unit_cost,
                to_currency=to_currency_id,
                company=self.company_id,
                date=layer_date,
            )

        rate_type = "manual rate" if manual_currency_rate else "slv"
        if is_company_currency:
            return [
                unit_cost,
                unit_cost * qty,
                new_unit_cost_in_to_currency,
                new_unit_cost_in_to_currency * qty,
                rate_type,
            ]
        return [
            new_unit_cost_in_to_currency,
            new_unit_cost_in_to_currency * qty,
            unit_cost,
            unit_cost * qty,
            rate_type,
        ]

    def _get_standard_price(self, new_value, standard_price, quantity_at_time, quantity):
        if not quantity_at_time:
            return standard_price
        return (new_value + standard_price * (quantity_at_time - quantity)) / quantity_at_time

    def _check_supported_product(self):
        """En 18.0 existe valuacion por lote (`lot_valuated`), que este recalculo no contempla:
        el costo se lleva a nivel producto y no por `stock.lot`. Frenamos antes de escribir."""
        if self.product_id.with_company(self.company_id).lot_valuated:
            raise UserError("El producto tiene valuación por lote (lot_valuated) y este recálculo no la contempla.")

    def action_compute_lines(self):
        self.ensure_one()
        self._check_supported_product()

        last_manual_svl_id = self.env["stock.valuation.layer"].search(
            self._get_manual_svl_domain(), order="create_date desc", limit=1
        )
        self.last_manual_svl_id = last_manual_svl_id

        lines_to_zero = self.env.context.get("lines_to_zero", {})

        leaf = [("company_id", "=", self.company_id.id), ("product_id", "=", self.product_id.id)]
        svl_ids = self.env["stock.valuation.layer"].search(leaf, order="create_date asc")
        if not svl_ids:
            # Sin este aviso el recalculo termina en "Not changes Required", que se lee
            # como "el producto esta bien" cuando en realidad se miro la compania equivocada.
            raise UserError(
                _(
                    "%(product)s has no valuation layers in %(company)s. "
                    "Check that you picked the company where the product is valued.",
                    product=self.product_id.display_name,
                    company=self.company_id.display_name,
                )
            )
        lines = [Command.clear()]
        quantity_at_time = 0
        standard_price_in_currency = 0
        standard_price = 0
        description = ""

        self.initial_amount_in_currency = self.product_id.with_company(self.company_id.id).standard_price_in_currency
        self.initial_amount = self.product_id.with_company(self.company_id.id).standard_price
        for svl_id in svl_ids:
            svl_type = ""
            vals = {
                "layer_id": svl_id.id,
                "layer_unit_cost": svl_id.unit_cost,
                "layer_value": svl_id.value,
                "layer_unit_cost_in_currency": svl_id.unit_cost_in_currency,
                "layer_value_in_currency": svl_id.value_in_currency,
            }
            quantity_at_time = quantity_at_time + svl_id.quantity
            after_last_manual = not last_manual_svl_id or svl_id.id > last_manual_svl_id.id
            if not after_last_manual:
                # El ajuste manual y todo lo anterior se respeta, asi que estos layers no
                # se van a escribir. El promedio ponderado tiene que avanzar con el valor
                # REGISTRADO, que es el que va a quedar, y no con el recalculado: si no,
                # la ficha termina con un costo que sale de una historia que no existe y
                # no cierra contra la suma de los layers.
                new_unit_cost = svl_id.unit_cost
                new_value = svl_id.value
                new_unit_cost_in_currency = svl_id.unit_cost_in_currency
                new_value_in_currency = svl_id.value_in_currency
                standard_price = self._get_standard_price(new_value, standard_price, quantity_at_time, svl_id.quantity)
                standard_price_in_currency = self._get_standard_price(
                    new_value_in_currency, standard_price_in_currency, quantity_at_time, svl_id.quantity
                )
                svl_type = "before adjustment"

            elif svl_id.id in lines_to_zero:
                new_unit_cost = 0
                new_value = 0
                new_unit_cost_in_currency = 0
                new_value_in_currency = 0
                quantity_at_time = quantity_at_time - svl_id.quantity
                svl_type = "zero"

            elif svl_id.stock_move_id and svl_id.stock_move_id.is_inventory:
                standard_price_in_currency = (
                    standard_price_in_currency if standard_price_in_currency else svl_id.unit_cost_in_currency
                )
                standard_price = standard_price if standard_price else svl_id.unit_cost

                new_unit_cost = standard_price
                new_value = standard_price * svl_id.quantity
                new_unit_cost_in_currency = standard_price_in_currency
                new_value_in_currency = standard_price_in_currency * svl_id.quantity
                svl_type = "inventory"

            # Si el movimento es de salida o de inventario, valor es el registrado en el producto
            elif svl_id.stock_move_id and svl_id.stock_move_id._is_out():
                if len(lines) == 0:
                    standard_price_in_currency = svl_id.unit_cost_in_currency
                    standard_price = svl_id.unit_cost

                new_unit_cost = standard_price
                new_value = standard_price * svl_id.quantity
                new_unit_cost_in_currency = standard_price_in_currency
                new_value_in_currency = standard_price_in_currency * svl_id.quantity
                svl_type = "out"

            # es un ajuste? si no tiene movimiento de stock
            elif not svl_id.stock_move_id:
                new_value = svl_id.value
                new_unit_cost = svl_id.unit_cost
                new_value_in_currency = svl_id.value_in_currency
                new_unit_cost_in_currency = svl_id.unit_cost_in_currency
                standard_price_in_currency = self._get_standard_price(
                    new_value_in_currency, standard_price_in_currency, quantity_at_time, svl_id.quantity
                )
                standard_price = self._get_standard_price(new_value, standard_price, quantity_at_time, svl_id.quantity)
                svl_type = "ajustement"

            # Es una devolucion
            elif svl_id.stock_move_id and svl_id.stock_move_id._is_returned(valued_type="in"):
                # Si existe el movimiento de origen el valor de avco sale del mov de origen
                if svl_id.stock_move_id.origin_returned_move_id:
                    origin_layer_ids = svl_id.stock_move_id.origin_returned_move_id.stock_valuation_layer_ids.ids
                    for temp_vals in lines:
                        if temp_vals[2] and temp_vals[2]["layer_id"] in origin_layer_ids:
                            new_unit_cost_in_currency = temp_vals[2]["new_unit_cost_in_currency"]
                            new_value_in_currency = new_unit_cost_in_currency * svl_id.quantity
                            standard_price_in_currency = self._get_standard_price(
                                new_value_in_currency, standard_price_in_currency, quantity_at_time, svl_id.quantity
                            )
                            new_unit_cost = temp_vals[2]["new_unit_cost"]
                            new_value = new_unit_cost * svl_id.quantity
                            standard_price = self._get_standard_price(
                                new_value, standard_price, quantity_at_time, svl_id.quantity
                            )
                            svl_type = "return  of  %s " % temp_vals[2]["layer_id"]
                            break
                # sino sale de producto
                else:
                    new_value_in_currency = standard_price_in_currency * svl_id.quantity
                    new_unit_cost_in_currency = standard_price_in_currency
                    new_value = standard_price * svl_id.quantity
                    new_unit_cost = standard_price
                    svl_type = "ret_without_move"

            # landed cost
            elif svl_id.stock_landed_cost_id:
                new_value, new_unit_cost, new_value_in_currency, new_unit_cost_in_currency, description = (
                    self._prepare_new_values(
                        from_currency_id=self.company_id.currency_id,
                        to_currency_id=svl_id.stock_landed_cost_id.valuation_currency_id,
                        qty=svl_id.quantity,
                        unit_cost=svl_id.value,
                        layer_date=svl_id.create_date,
                        manual_currency_rate=svl_id.manual_currency_rate,
                    )
                )
                standard_price = self._get_standard_price(new_value, standard_price, quantity_at_time, svl_id.quantity)
                standard_price_in_currency = self._get_standard_price(
                    new_value_in_currency, standard_price_in_currency, quantity_at_time, svl_id.quantity
                )
                svl_type = "landed cost %s" % description

            # purchase refund
            elif (
                svl_id.stock_move_id
                and svl_id.stock_move_id.purchase_line_id
                and svl_id.stock_move_id.origin_returned_move_id
            ):
                origin_layer_ids = svl_id.stock_move_id.origin_returned_move_id.stock_valuation_layer_ids.ids
                for temp_vals in lines:
                    if temp_vals[2] and temp_vals[2]["layer_id"] in origin_layer_ids:
                        new_unit_cost_in_currency = temp_vals[2]["new_unit_cost_in_currency"]
                        new_value_in_currency = new_unit_cost_in_currency * svl_id.quantity
                        standard_price_in_currency = self._get_standard_price(
                            new_value_in_currency, standard_price_in_currency, quantity_at_time, svl_id.quantity
                        )
                        new_unit_cost = temp_vals[2]["new_unit_cost"]
                        new_value = new_unit_cost * svl_id.quantity
                        standard_price = self._get_standard_price(
                            new_value, standard_price, quantity_at_time, svl_id.quantity
                        )
                        svl_type = "purchase refund  of  %s " % temp_vals[2]["layer_id"]
                        break

            # purchase
            elif svl_id.stock_move_id and svl_id.stock_move_id.purchase_line_id:
                purchase_currency_id = svl_id.stock_move_id.purchase_line_id.order_id.currency_id
                if purchase_currency_id == self.company_id.currency_id:
                    from_currency_id = self.company_id.currency_id
                    to_currency_id = self.valuation_currency_id
                else:
                    from_currency_id = self.valuation_currency_id
                    to_currency_id = self.company_id.currency_id
                new_unit_cost, new_value, new_unit_cost_in_currency, new_value_in_currency, description = (
                    self._prepare_new_values(
                        from_currency_id=from_currency_id,
                        to_currency_id=to_currency_id,
                        qty=svl_id.quantity,
                        unit_cost=svl_id.stock_move_id.purchase_line_id.price_unit,
                        layer_date=svl_id.create_date,
                        manual_currency_rate=svl_id.manual_currency_rate,
                    )
                )
                standard_price = self._get_standard_price(new_value, standard_price, quantity_at_time, svl_id.quantity)
                standard_price_in_currency = self._get_standard_price(
                    new_value_in_currency, standard_price_in_currency, quantity_at_time, svl_id.quantity
                )
                svl_type = "Purchase %s" % description

            else:
                new_unit_cost, new_value, new_unit_cost_in_currency, new_value_in_currency, description = (
                    self._prepare_new_values(
                        from_currency_id=self.company_id.currency_id,
                        to_currency_id=self.valuation_currency_id,
                        qty=svl_id.quantity,
                        unit_cost=svl_id.unit_cost,
                        layer_date=svl_id.create_date,
                        manual_currency_rate=svl_id.manual_currency_rate,
                    )
                )
                standard_price = self._get_standard_price(new_value, standard_price, quantity_at_time, svl_id.quantity)
                standard_price_in_currency = self._get_standard_price(
                    new_value_in_currency, standard_price_in_currency, quantity_at_time, svl_id.quantity
                )
                svl_type = "slv %s" % description

            vals["new_value"] = new_value
            vals["new_unit_cost"] = new_unit_cost
            vals["standard_price"] = standard_price

            vals["new_value_in_currency"] = new_value_in_currency
            vals["new_unit_cost_in_currency"] = new_unit_cost_in_currency
            vals["standard_price_in_currency"] = standard_price_in_currency
            vals["quantity_at_time"] = quantity_at_time
            vals["svl_type"] = svl_type

            need_change_1 = self.valuation_currency_id.compare_amounts(svl_id.value_in_currency, new_value_in_currency)
            need_change_2 = self.valuation_currency_id.compare_amounts(
                svl_id.unit_cost_in_currency, new_unit_cost_in_currency
            )
            need_change_3 = self.currency_id.compare_amounts(svl_id.value, new_value)
            need_change_4 = self.currency_id.compare_amounts(svl_id.unit_cost, new_unit_cost)

            # Solo se ajusta lo POSTERIOR al ultimo ajuste manual: el ajuste que cargo el
            # usuario se respeta tal cual, y con el todo lo anterior. Sin este corte, un
            # ajuste que compensaba un layer mal valuado se termina contando dos veces:
            # una en el layer recalculado y otra en el ajuste que sigue ahi.
            need_change_5 = after_last_manual
            need_change_6 = svl_id.id in lines_to_zero
            vals["need_changes"] = bool(
                (need_change_1 or need_change_2 or need_change_3 or need_change_4 or need_change_6) and need_change_5
            )
            lines.append(Command.create(vals))
        self.line_ids = lines
        self.final_amount_in_currency = standard_price_in_currency
        self.final_amount = standard_price
        self.state = "in_process"
        self.revaluation_error = False
        self.action_check_need_changes()

    def action_check_need_changes(self):
        if (
            not self.line_ids.filtered("need_changes")
            and self.final_amount_in_currency == self.initial_amount_in_currency
            and self.final_amount == self.initial_amount
        ):
            self.state = "no_change"

    def action_manual_slv_revaluation(self):
        self.ensure_one()
        # Sin lineas no hay nada calculado, y los importes finales estan en cero: aplicar
        # escribiria 0 en el costo del producto sin dejar rastro en ningun layer.
        if not self.line_ids:
            raise UserError(_("Compute the lines before revaluating %s.", self.display_name))
        self._check_supported_product()
        slv_changed = False
        # to_reconciled_line_ids guarda todas las conciliaciones
        to_reconciled_line_ids = []
        for line_id in self.line_ids.filtered("need_changes"):
            slv_changed = True
            if line_id.layer_id.stock_landed_cost_id:
                raise UserError("No puedo ajustar un landed cost")
            line_id.layer_id.write({"unit_cost": line_id.new_unit_cost, "value": line_id.new_value})
            # se escribe en dos pasos: el compute de value_in_currency corta si ya tiene valor
            line_id.layer_id.write(
                {
                    "unit_cost_in_currency": line_id.new_unit_cost_in_currency,
                    "value_in_currency": line_id.new_value_in_currency,
                }
            )
            lines = []
            product_move_line_ids = line_id.layer_id.account_move_id.line_ids.filtered(
                lambda x: x.product_id == self.product_id
            )
            # agrego las full reconciliaciones
            to_reconciled_line_ids.append(product_move_line_ids.full_reconcile_id.reconciled_line_ids)
            move_ids = product_move_line_ids.mapped("move_id")
            move_ids.button_draft()
            for move_line in product_move_line_ids:
                multiplier = 1 if move_line.credit == 0 else -1
                field = "debit" if move_line.credit == 0 else "credit"
                # OJO el valor de currency puede ser positivo o negativo
                # pero en el asiento siempre es positivo para debit y negativo para credit
                # por eso multiplico el valor absoluto por el signo
                lines.append(
                    Command.update(
                        move_line.id,
                        {
                            "amount_currency": abs(line_id.new_value_in_currency) * multiplier,
                            field: abs(line_id.new_value),
                        },
                    )
                )
            if lines:
                line_id.layer_id.account_move_id.line_ids = lines
            move_ids.action_post()

        product_id = self.product_id.with_company(self.company_id.id)
        if product_id.standard_price_in_currency != self.final_amount_in_currency:
            product_id.with_context(disable_auto_svl=True).sudo().write(
                {"standard_price_in_currency": self.final_amount_in_currency}
            )
            self.amount_changed = True
        if product_id.standard_price != self.final_amount:
            product_id.with_context(disable_auto_svl=True).sudo().write({"standard_price": self.final_amount})
            self.amount_changed = True

        self.slv_changed = slv_changed
        for to_reconciled_lines in to_reconciled_line_ids:
            # si no tiene reconciliaciones, lo reconcilio sino supongo
            # que ya lo reconcilie antes
            if not any(to_reconciled_lines.mapped("reconciled")):
                to_reconciled_lines.reconcile()
        self.state = "done"
        self.revaluation_error = False

    def _batch_selection(self, states):
        """Registros de la seleccion sobre los que corresponde correr la accion masiva."""
        records = self.filtered(lambda rec: rec.state in states)
        if not records:
            raise UserError(_("None of the selected records is in a state that allows this action."))
        return records

    def _apply_isolated(self, method_name):
        """Corre `method_name` sobre este registro, aislado en su propio savepoint.

        Uno que falla no se lleva a los demas de la tanda: se revierte solo y queda en
        `error` con el motivo a la vista. Se atrapa `UserError` y sus subclases, que es
        todo lo que levanta el propio flujo (incluidos los de validacion y de acceso). Un
        fallo de infraestructura —un deadlock, un conflicto de serializacion— no es
        `UserError` y se propaga a proposito: parquearlo en un estado que nadie reintenta
        solo lo haria pasar por un rechazo definitivo.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                getattr(self, method_name)()
        except UserError as error:
            self.write({"state": "error", "revaluation_error": str(error)})
            _logger.warning("%s failed on recompute %s: %s", method_name, self.id, error)

    def action_compute_lines_multi(self):
        """Boton de la vista lista: recalcula la seleccion de a un registro.

        Sin tope de registros. Recalcular no toca los layers ni sus asientos —lo unico
        que escribe son las lineas propuestas del propio recompute— asi que se hace en el
        request y el operador ve el resultado al toque.
        """
        for rec in self._batch_selection(("draft", "in_process", "no_change", "error")):
            rec._apply_isolated("action_compute_lines")
            # El cache crece con cada producto (sus layers, sus asientos): en una
            # seleccion grande hay que soltarlo o la memoria no para de subir.
            self.env.invalidate_all()

    def action_queue_revaluation(self):
        """Boton de la vista lista: encola la seleccion para que la revalue el cron.

        No revalua en el request. Aplicar un registro reescribe los asientos de cada
        layer que cambia, asi que una seleccion grande se pasa del timeout y no queda
        nada aplicado. Encolar es una escritura de estado, cueste lo que cueste la cola.
        """
        records = self._batch_selection(("in_process",))
        records.write({"state": "revaluating", "revaluation_error": False})
        self.env.ref("stock_currency_valuation_recompute.cron_revaluate_queued").sudo()._trigger()

    @api.model
    def _cron_revaluate_queued(self):
        """Revalua los encolados de a uno hasta agotar el presupuesto de tiempo."""
        started = time.monotonic()
        # Solo los ids: iterar el recordset entero traeria de una las lineas de los cientos
        # de encolados, cuando en el presupuesto entra un punado.
        queued_ids = self.search([("state", "=", "revaluating")]).ids
        for done, rec_id in enumerate(queued_ids, start=1):
            # sudo y la compania del registro: el usuario del cron no tiene por que estar
            # habilitado en la compania donde se valua el producto, y sin eso los layers y
            # los asientos de otra compania no se pueden ni leer.
            rec = self.browse(rec_id).sudo()
            if rec.state == "revaluating":
                # La cola se leyo al arrancar: entre eso y ahora lo pueden haber cancelado.
                rec.with_company(rec.company_id)._apply_isolated("action_manual_slv_revaluation")
            # Adentro del loop: si algo corta la corrida, lo hecho hasta aca cuenta como
            # progreso y el corte no se anota como falla del cron. Y mientras `remaining`
            # no llegue a cero, Odoo lo relanza enseguida en vez de esperar el intervalo.
            self.env["ir.cron"]._notify_progress(done=done, remaining=len(queued_ids) - done)
            self.env.invalidate_all()
            if time.monotonic() - started > REVALUATION_TIME_BUDGET:
                break


class StockValuationLayerRecomputeLine(models.Model):
    _name = "stock.valuation.layer.recompute.line"
    _description = "lines layer recompute"

    layer_id = fields.Many2one("stock.valuation.layer")
    quantity = fields.Float(related="layer_id.quantity")
    quantity_at_time = fields.Float()
    layer_date = fields.Datetime(related="layer_id.create_date", string="Layer Date")
    recompute_id = fields.Many2one("stock.valuation.layer.recompute")
    currency_id = fields.Many2one("res.currency", related="recompute_id.valuation_currency_id")
    company_currency_id = fields.Many2one("res.currency", related="recompute_id.currency_id")

    # company currency
    layer_unit_cost = fields.Monetary(currency_field="company_currency_id")
    layer_value = fields.Monetary(currency_field="company_currency_id")
    new_unit_cost = fields.Monetary(currency_field="company_currency_id")
    new_value = fields.Monetary(currency_field="company_currency_id")
    standard_price = fields.Monetary(currency_field="company_currency_id")

    # Secundary currency
    layer_unit_cost_in_currency = fields.Monetary()
    layer_value_in_currency = fields.Monetary()
    new_unit_cost_in_currency = fields.Monetary()
    new_value_in_currency = fields.Monetary()
    standard_price_in_currency = fields.Monetary()
    need_changes = fields.Boolean()
    svl_type = fields.Char()

>>>>>>> FORWARD PORTED
