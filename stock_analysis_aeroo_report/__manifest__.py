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
    'name': 'Stock Analysis Report',
    'version': '12.0.1.0.0',
    'category': 'Aeroo Reporting',
    'sequence': 14,
    'author': 'ADHOC SA, Iván Todorovich <ivan.todorovich@gmail.com>',
    'website': 'www.adhoc.com.ar',
    'license': 'AGPL-3',
    'images': [
    ],
    'depends': [
        'stock',
        'account',
        'report_aeroo',
    ],
    'data': [
        'reports/stock_analysis_report.xml',
        'wizard/stock_analysis_report_wizard.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
