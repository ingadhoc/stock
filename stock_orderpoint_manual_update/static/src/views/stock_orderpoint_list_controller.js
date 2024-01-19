/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { StockOrderpointListController } from '@stock/views/stock_orderpoint_list_controller';

patch(StockOrderpointListController.prototype, "order patch", {
    async onClickOrder() {
        const resIds = await this.getSelectedResIds();
        const action = await this.model.orm.call(this.props.resModel, 'action_replenish', [resIds], {
            context: this.props.context,
        });
        if (action) {
            await this.actionService.doAction(action);
        }
    }
});

