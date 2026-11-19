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

<<<<<<< 39f3d3941ec9262c736601e62267d02d5dc3b5f4
    @api.constrains("picking_type_id", "batch_id")
    def _check_picking_type_batch(self):
        for rec in self.filtered("batch_id"):
            if rec.batch_id.picking_type_id and rec.picking_type_id != rec.batch_id.picking_type_id:
                raise ValidationError(
                    _("You cannot change the operation type of a picking if it is already assigned to a batch.")
                )
||||||| ded1fa114c1cdc2dbc5924bba06083638942b957
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

            # A move only completes on _action_done when picked; force_transfer forces the
            # quantities, so mark its moves picked too (otherwise nothing is done in 18.0).
            pick.move_ids.filtered(lambda m: m.state not in ("done", "cancel")).picked = True
            pick._action_done()
            # force_transfer validates a picking directly, skipping button_validate, which is
            # where core drops a done picking from a wave whose other pickings are still open.
            # Without this the done picking stays in the wave and its sanity check rejects it.
            if pick.batch_id and any(sibling.state != "done" for sibling in pick.batch_id.picking_ids):
                pick.batch_id = False

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
>>>>>>> 268e7af029baae5233a7ed1d5e1290eaf1a750e1
