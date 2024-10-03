##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models
from . import wizard
from odoo import api, SUPERUSER_ID


def uninstall_hook(env):
    menu = env.ref('stock.menu_reordering_rules_replenish', raise_if_not_found=False)
    if menu:
        menu.action = env.ref('stock.action_replenishment')
