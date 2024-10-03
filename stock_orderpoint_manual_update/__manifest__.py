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
    'name': 'Stock Orderpoint Manual Update',
    'version': "17.0.1.2.0",
    'category': 'Warehouse Management',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'purchase_stock',
        'stock_ux',
    ],
    'data': [
        'wizard/stock_warehouse_orderpoint_wizard_views.xml',
        'security/ir.model.access.csv',
        'views/stock_warehouse_orderpoint_views.xml',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'stock_orderpoint_manual_update/static/src/views/**/*',
        ],
    },
    'uninstall_hook': "uninstall_hook",
    'installable': True,
    'auto_install': False,
    'application': False,
}
