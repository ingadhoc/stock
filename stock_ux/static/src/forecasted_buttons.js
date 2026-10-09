/** @odoo-module **/
import { ForecastedButtons } from "@stock/stock_forecasted/forecasted_buttons";
import { patch } from '@web/core/utils/patch';


patch(ForecastedButtons.prototype, {
    async _onClickTrace(){
        return this.actionService.doAction("stock.stock_move_action", {
            additionalContext: {
                search_default_future: 1,
                search_default_groupby_picking_type_id: 1,
                search_default_product_id: this.productId,
            },
        });
    }
});
