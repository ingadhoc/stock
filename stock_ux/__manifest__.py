##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Stock UX',
    'version': "15.0.1.3.0",
    'category': 'Warehouse Management',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'sale_stock',
        'report_aeroo',
        'stock_voucher',
    ],
    'data': [
        'security/stock_ux_security.xml',
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
        'views/stock_move_line_views.xml',
        'views/stock_warehouse_orderpoint_views.xml',
        'views/procurement_group_views.xml',
        'views/stock_move_views.xml',
        'views/stock_backorder_confirmation_views.xml',
        'views/stock_return_picking_views.xml',
        'views/stock_picking_type_views.xml',
        'views/report_deliveryslip.xml',
        'wizards/stock_operation_wizard_views.xml',
        'wizards/res_config_settings_views.xml',
        'report/stock_ux_report.xml',
        'report/report_stock_forecasted.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
