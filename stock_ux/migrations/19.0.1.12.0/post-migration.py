import logging

from openupgradelib import openupgrade

logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """The "Inventory Adjustments" capability was carved out of the plain
    Inventory User group. To avoid a regression on existing installations,
    grant the new group to every user that is currently an Inventory User so
    they keep being able to adjust. Admins can then untick it for the users
    that should become "basic" (everything but adjustments)."""
    adjustment_group = env.ref("stock_ux.group_stock_inventory_adjustment", raise_if_not_found=False)
    stock_user_group = env.ref("stock.group_stock_user", raise_if_not_found=False)
    if not adjustment_group or not stock_user_group:
        return
    users = stock_user_group.all_user_ids
    logger.info("Granting 'Inventory Adjustments' to %s existing Inventory Users", len(users))
    adjustment_group.write({"user_ids": [(4, user.id) for user in users]})
