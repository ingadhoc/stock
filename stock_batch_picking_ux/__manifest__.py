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
    "name": "Stock Usability with Batch Picking",
<<<<<<< 8883923bbd1c6ec51e71a38828f621eb08fc4eb1
    "version": "20.0.1.0.0",
||||||| ea63eb8c960ec58aaf4ee2d68a2fcec0bc5854e8
    "version": "19.0.1.5.0",
=======
    "version": "19.0.1.6.0",
>>>>>>> a93b0c07f109c1a96d7a83b13b46d103db3dbec5
    "category": "Warehouse Management",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "stock_ux",
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
