/** @odoo-module **/
import BarcodeModel from '@stock_barcode/models/barcode_model';
import { patch } from '@web/core/utils/patch';

patch(BarcodeModel.prototype, {
    createNewLine(){
        if (this.record.picking_type_id.block_additional_quantity == true){
            this.notification.add("No se puede agregar debido a la configuracion del tipo de operación", { type: "danger" });
            return false
        }
        this._super(...arguments);
    },
    _createNewLine(){
        if (this.record.picking_type_id.block_additional_quantity == true){
            this.notification.add("No se puede agregar más unidades del mismo producto debido a la configuracion del tipo de operación", { type: "danger" });
            return false
        }
        this._super(...arguments);
    },
});
