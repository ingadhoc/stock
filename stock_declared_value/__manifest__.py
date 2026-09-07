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
<<<<<<< e7187e20818a805c2f7052b82ccfe61d203f06e3:stock_declared_value/__manifest__.py
    "name": "Stock Declared Value",
    "version": "19.0.1.1.0",
||||||| 3765afa30ec444eb3db54c42165ba14ccc810c42:stock_voucher/__manifest__.py
    "name": "Stock Voucher",
    "version": "18.0.1.7.1",
=======
    "name": "Stock Voucher",
    "version": "18.0.1.8.0",
>>>>>>> 0ded6f93dc25e3f09a4c20c00bd4feda4838ecdc:stock_voucher/__manifest__.py
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
