from odoo import models, fields, api


class StockProductionLot(models.Model):
    _inherit = 'stock.lot'

    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, order=None):
        args = args or []
        return_lot_ids = self._context.get('return_lot_ids', False)

        # Verificar si es una lista y tiene al menos un elemento con el formato correcto
        if isinstance(return_lot_ids, list) and return_lot_ids and isinstance(return_lot_ids[0], (tuple, list)) and len(return_lot_ids[0]) > 2:
            args.append(('id', 'in', return_lot_ids[0][2]))

        return super()._name_search(name, args, operator, limit, order)

    
    # @api.model
    # def _name_search(self, name, args=None, operator='ilike', limit=100, order=None):
    #     args = args or []
    #     return_lot_ids = self._context.get('return_lot_ids', False)
    #     if return_lot_ids and isinstance(return_lot_ids, list) and return_lot_ids[0][2]:
    #         args.append(('id', 'in', return_lot_ids[0][2]))
    #     return super()._name_search(name, args, operator, limit, order)
