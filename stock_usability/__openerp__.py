# -*- coding: utf-8 -*-
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
    'name': 'Stock Usability Improvements',
    'version': '9.0.1.21.0',
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
    ],
    'data': [
        'security/security.xml',
        'views/product_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_move_view.xml',
        'views/stock_pack_operation_view.xml',
        'views/stock_warehouse_orderpoint_view.xml',
        'views/procurement_order_view.xml',
        'views/procurement_group_view.xml',
        'views/stock_move_view.xml',
        'views/stock_backorder_confirmation_view.xml',
        'views/res_config_view.xml',
        'views/stock_valuation_history_view.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
