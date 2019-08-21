##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo.addons.stock_request.models.stock_move import StockMove


def new_copy_data(self, default=None):
    """ Nosotros ya copiamos la allocation en el split de arriba y ademas
    #     si se copiasen en el copy data, con algunas rutas se esta duplicando
    #     el allocation en casos donde no debe hacerlo, solo queremos duplicar
    #     allocation en entregas parciales (con el split)
    #     """
    return super(StockMove, self).copy_data(default=default)


StockMove.copy_data = new_copy_data
