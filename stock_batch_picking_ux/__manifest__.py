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
<<<<<<< 8b1493de9906b9f991195e66de149c8aa7f66608
    "name": "Stock Usability with Batch Picking",
    "version": "19.0.1.2.0",
||||||| 6480d59457f874a6a49914b50d200bc588a70271
    "name": "Stock Usability with Batch Picking and stock vouchers",
    "version": "18.0.1.2.0",
=======
    "name": "Stock Usability with Batch Picking and stock vouchers",
    "version": "18.0.1.3.0",
>>>>>>> d3e250553190905d374d616c9b4b9edc2225a432
    "category": "Warehouse Management",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "stock_ux",
        "stock_picking_batch",
    ],
    "data": [
        "reports/ir.actions.report.xml",
        "reports/picking_templates.xml",
        "reports/report_batch_deliveryslip.xml",
        "views/stock_batch_picking_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_move_line_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": True,
    "application": False,
}
