##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from . import models


def init_settings(env):
    # set the stock request order configuration in True
    config = env["res.config.settings"].create(
        {
            "group_stock_request_order": True,
        }
    )
    config.execute()
