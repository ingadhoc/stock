/** @odoo-module */

import { StockOrderpointListController } from '@stock/views/stock_orderpoint_list_controller';
import { patch } from "@web/core/utils/patch";

patch(StockOrderpointListController.prototype, "order patch", {
    async onClickOrder() {
        const resIds = await this.getSelectedResIds();
        const action = await this.model.orm.call(this.props.resModel, 'action_replenish', [resIds], {
            context: this.props.context,
        });
        await this.model.orm.call(
            'stock.warehouse.orderpoint',
            'update_qty_to_order_orderpoint',
            [resIds]
        );
        if (action) {
            return await this.actionService.doAction(action);
        }
        return this.actionService.doAction('stock.action_orderpoint_replenish', {
            stackPosition: 'replaceCurrentAction',
        });
    }
});
