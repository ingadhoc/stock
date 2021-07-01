from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'stock_batch_picking_ux', 'migrations/13.0.1.2.0/mig_data.xml')
