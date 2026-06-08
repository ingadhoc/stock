import logging

from openupgradelib import openupgrade

logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    logger.info("Forzamos la actualización de la vista stock_warehouse_views en stock")
    openupgrade.load_data(env, "stock", "views/stock_warehouse_views.xml")
