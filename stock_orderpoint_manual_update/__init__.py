##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import wizard


def uninstall_hook(env):
    menu = env.ref("stock.menu_reordering_rules_replenish", raise_if_not_found=False)
    if menu:
        # Back to the action and the parent menu that stock defines
        replenishment = env.ref("stock.action_replenishment")
        menu.write(
            {
                "action": f"{replenishment._name},{replenishment.id}",
                "parent_id": env.ref("stock.menu_stock_procurement").id,
            }
        )
    action = env.ref("stock.action_orderpoint_replenish", raise_if_not_found=False)
    if action:
        action.context = "{}"
