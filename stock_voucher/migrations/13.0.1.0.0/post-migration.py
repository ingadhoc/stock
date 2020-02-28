from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr, 'stock_voucher', 'migrations/13.0.1.0.0/mig_data.xml')
