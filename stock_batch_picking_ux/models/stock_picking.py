from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Related to drive conditional logic in inherited views/modules: a batch
    # with a partner manages delivery guides at the batch level (consolidated);
    # a batch without a partner manages them per picking (individual).
    batch_partner_id = fields.Many2one(
        related="batch_id.partner_id",
        store=True,
    )

<<<<<<< e7187e20818a805c2f7052b82ccfe61d203f06e3
    @api.constrains("picking_type_id", "batch_id")
    def _check_picking_type_batch(self):
        for rec in self.filtered("batch_id"):
            if rec.batch_id.picking_type_id and rec.picking_type_id != rec.batch_id.picking_type_id:
                raise ValidationError(
                    _("You cannot change the operation type of a picking if it is already assigned to a batch.")
                )
||||||| cbc65dc965efe4401550426b45fad1bc2cc27e97
        If *force_qty* is True, force the transfer for all product_qty
        when quantity is 0.

        Otherwise, process only pack operation with quantity.
        If a picking has no quantity filled, we released it from his batch
        """
        for pick in self:
            if pick.state != "assigned":
                pick.action_assign()
                # FIX
                # fix porque si el picking esta parcialmente disponible
                # no lo termina procesando
                # if pick.state != 'assigned':
                if pick.state not in ["assigned", "partially_available"]:
                    continue
                # END FIX

            if force_qty:
                for pack in pick.move_line_ids:
                    pack.quantity = pack.quantity
            else:
                if all(
                    float_is_zero(pack.quantity, precision_rounding=pack.product_uom_id.rounding)
                    for pack in pick.move_line_ids
                ):
                    # No qties to process, release out of the batch
                    pick.batch_id = False
                    continue
                else:
                    for pack in pick.move_line_ids:
                        if not pack.quantity:
                            pack.unlink()

            pick._action_done()

    def _action_generate_backorder_wizard(self, show_transfers=False):
        if self._context.get("picking_batches", False):
            wiz = self.env["stock.backorder.confirmation"].create({"pick_ids": [(4, p.id) for p in self]})
            wiz.process()
            self._context.get("picking_batches").write({"state": "done"})
            return True
        else:
            return super(StockPicking, self)._action_generate_backorder_wizard(show_transfers=show_transfers)
=======
        If *force_qty* is True, force the transfer for all product_qty
        when quantity is 0.

        Otherwise, process only pack operation with quantity.
        If a picking has no quantity filled, we released it from his batch
        """
        for pick in self:
            if pick.state != "assigned":
                pick.action_assign()
                # FIX
                # fix porque si el picking esta parcialmente disponible
                # no lo termina procesando
                # if pick.state != 'assigned':
                if pick.state not in ["assigned", "partially_available"]:
                    continue
                # END FIX

            if force_qty:
                for pack in pick.move_line_ids:
                    pack.quantity = pack.quantity
            else:
                if all(
                    float_is_zero(pack.quantity, precision_rounding=pack.product_uom_id.rounding)
                    for pack in pick.move_line_ids
                ):
                    # No qties to process, release out of the batch
                    pick.batch_id = False
                    continue
                else:
                    for pack in pick.move_line_ids:
                        if not pack.quantity:
                            pack.unlink()

            pick._action_done()

    def _action_generate_backorder_wizard(self, show_transfers=False):
        if self._context.get("picking_batches", False):
            wiz = self.env["stock.backorder.confirmation"].create({"pick_ids": [(4, p.id) for p in self]})
            wiz.process()
            self._context.get("picking_batches").write({"state": "done"})
            return True
        else:
            return super(StockPicking, self)._action_generate_backorder_wizard(show_transfers=show_transfers)

    def _action_done(self):
        # el número del lote de recepción se estampa al llegar a done (lote, wizard de
        # orden parcial o traslado solo) y se lee antes del super, que desasigna batch_id;
        # la condición es la misma que el guard de stock_voucher deja pasar
        numbers = {
            picking.id: picking.batch_id.voucher_number
            for picking in self
            if picking.batch_id.picking_type_code == "incoming"
        }
        res = super()._action_done()
        for picking in self.filtered(lambda p: p.state == "done" and not p.voucher_ids):
            number = numbers.get(picking.id)
            if number and any(operation.quantity for operation in picking.move_line_ids):
                self.env["stock.picking.voucher"].create({"picking_id": picking.id, "name": number})
        return res
>>>>>>> 6aa17ff3cb50293ac232a6f602b9539d50e28bba
