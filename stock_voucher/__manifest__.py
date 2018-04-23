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
    'name': 'Stock Voucher',
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
        'delivery',
        'base_validator',
        # 'web_widget_one2many_tags'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/stock_print_remit_view.xml',
        'views/report_stockpicking.xml',
        'views/stock_book_view.xml',
        'views/stock_picking_voucher_view.xml',
        'views/stock_remit_data.xml',
        'views/stock_menu.xml',
        # 'wizard/stock_transfer_details_view.xml',
        'views/res_company_view.xml',
        'views/stock_picking_type_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_move_view.xml',
        'data/stock_book_data.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': False,
    'auto_install': False,
    'application': False,
}
