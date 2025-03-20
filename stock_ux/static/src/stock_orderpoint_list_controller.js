/** @odoo-module **/
import { StockOrderpointListController } from '@stock/views/stock_orderpoint_list_controller';
import { patch } from "@web/core/utils/patch";

patch(StockOrderpointListController.prototype, "stock_orderpoint_patch", {
    async onClickOrder() {
        const resIds = await this.getSelectedResIds();
        const action = await this.model.orm.call(this.props.resModel, 'action_replenish', [resIds], {
            context: this.props.context,
        });
        if (action) {
            await this.actionService.doAction(action);
        }
        await this.model.orm.call(
            'stock.warehouse.orderpoint',
            'update_qty_to_order',
            [resIds]
        );
        return await this.actionService.doAction('stock.action_orderpoint_replenish', {
            stackPosition: 'replaceCurrentAction',
        });
    }
});
