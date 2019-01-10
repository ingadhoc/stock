# -*- coding: utf-8 -*-
from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    """
    The objective of this hook is to speed up the update of the module
    """
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE stock_move_line ADD COLUMN picking_type_id integer;
        COMMENT ON COLUMN stock_move_line.picking_type_id IS
        'Operation Type';
        """)
    openupgrade.logged_query(
        env.cr,
        """\
        UPDATE stock_move_line AS sml
        SET picking_type_id = sp.picking_type_id
        FROM stock_picking AS sp
        WHERE sml.picking_id = sp.id
        """)
