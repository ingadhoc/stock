/** @odoo-module **/
import { ForecastedButtons } from "@stock/stock_forecasted/forecasted_buttons";
import { patch } from '@web/core/utils/patch';

const { onWillStart } = owl;

patch(ForecastedButtons.prototype, 'stock_ux.ForecastedButtons',{
    setup() {
        this._super.apply();
        onWillStart(async () =>{
            this.context = this.props.action.context;
            this.productId = this.context.active_id;
            this.resModel = this.props.resModel || 'product.template';
        });
    },

    async _onClickTrace(){
        return this.actionService.doAction("stock.stock_move_action", {
            additionalContext: {
                search_default_future: 1,
                search_default_picking_type: 1,
                search_default_product_id: this.productId,
            },
        });
    }
});
