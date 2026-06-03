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
<<<<<<< 8b1493de9906b9f991195e66de149c8aa7f66608:stock_declared_value/__manifest__.py
    "name": "Stock Declared Value",
    "version": "19.0.1.1.0",
||||||| 5510a864c7fa81e197b0c52486c3933f87d7908c:stock_voucher_ux/__manifest__.py
    "name": "Stock Voucher UX",
    "version": "18.0.1.3.0",
=======
    "name": "Stock Voucher UX",
    "version": "18.0.1.4.0",
>>>>>>> c46207d64e28343c267dd8e7280fbc486a6ef26f:stock_voucher_ux/__manifest__.py
    "category": "Warehouse Management",
    "sequence": 14,
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "sale_stock",
        "stock_ux",
    ],
    "data": [
        "views/stock_picking_type_views.xml",
        "views/stock_picking_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
