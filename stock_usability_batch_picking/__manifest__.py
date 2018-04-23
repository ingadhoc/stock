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
    'name': 'Stock Usability with Batch Picking and stock vouchers',
    'version': '9.0.1.8.0',
    'category': 'Warehouse Management',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'stock_usability',
        'stock_voucher',
        'stock_batch_picking',
    ],
    'data': [
        'views/stock_batch_picking_view.xml',
        'views/stock_pack_operation_view.xml',
        'views/stock_picking_view.xml',
        'report/batch_picking_list_data.xml',
    ],
    'demo': [
    ],
    'installable': False,
    'auto_install': True,
    'application': False,
}
