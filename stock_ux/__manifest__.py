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
<<<<<<< 5c4c4f22e4695c1a7871d31b873b66b0e893cf18
    "name": "Stock UX",
    "version": "18.0.1.11.0",
    "category": "Warehouse Management",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "images": [],
    "depends": [
        "sale_stock",
||||||| 0b86a64b7e1a4ff860ae521461ed182c091c0d60
    'name': 'Stock UX',
    'version': "17.0.1.12.0",
    'category': 'Warehouse Management',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'images': [
=======
    'name': 'Stock UX',
    'version': "17.0.1.13.0",
    'category': 'Warehouse Management',
    'sequence': 14,
    'summary': '',
    'author': 'ADHOC SA',
    'website': 'www.adhoc.com.ar',
    'images': [
>>>>>>> a4c1ff62ff5d01080e27d80ead9fc268afd8a548
    ],
    "data": [
        "security/stock_ux_security.xml",
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/product_product_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_move_views.xml",
        "views/stock_move_line_views.xml",
        "views/stock_warehouse_orderpoint_views.xml",
        "views/procurement_group_views.xml",
        "views/stock_backorder_confirmation_views.xml",
        "views/stock_return_picking_views.xml",
        "views/stock_picking_type_views.xml",
        "views/report_deliveryslip.xml",
        "views/res_config_settings_views.xml",
        "wizards/stock_operation_wizard_views.xml",
        "wizards/stock_product_zpl_views.xml",
        "report/ir.action.reports.xml",
        "report/picking_templates.xml",
        "views/res_company_views.xml",
        "views/stock_quant_views.xml",
        "report/stock_picking_operations.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "assets": {
        "web.assets_backend": [
            "stock_ux/static/src/**/*.xml",
            "stock_ux/static/src/**/*.js",
        ],
    },
    "license": "AGPL-3",
}
