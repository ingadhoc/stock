.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

========
Stock UX
========


#. Add observations on pickings (and deliveryslip)
#. Add a wizard action in the stock move lines of a picking to change locations for several lines at the same time with the 'Manage Multiple Stock Locations' permission.
#. Show always visible (for an existing lots configuration in the type operation) the notebook pages in lot form view when create and edit a lot from a stock move line.
#. Add an optional setting to print in Delivery Slip reports the origin description instead of the product name
#. We create a new group "Allow picking cancellation", only users with that right can cancel pickings or validate without back orders
#. Only allow to delete pickings on draft/cancel state and "Block Picking Deletion?" is not checked in Pick operation type.
#. Add new field ""Net Quantity"" in stock moves lines. When you filter by locations, the field will be computed this way:
#. If filtered location is found on source location: use negative quantity.
#. If filtered location is found on destiny location: use positive quantity.
#. If filtered location is found on source and destiny location: use "0".
#. Add Rotation and Location Rotation to Reordering Rules (orderpoint): delivered quantities to customers on last 120 days divided per 4 (to make it monthly)
#. Add optional constraints configurable by Picking Type: Block additional quantity, Block force availability, Block picking deletion. With Block force availability, a line with a lot or serial number can only take it from the location that holds it.
#. Show location and warehouse filters on all products and product templates views (not only the one on inventory)
#. When archive a replenishment rule set min and max quantities in 0.
#. Show inactive replenishment rules if the product is active (with warning decorator).
#. Send template established in operation type when confirm picking.
#. Add an optional setting to print remaining quantities not yet delivered on Delivery Slips: "Show remaining quantities not yet delivered on Delivery Slips."print remaining quantities not yet delivered
#. Adds a review toggle per line that allows the user to indicate when the replenishment order is ready to be confirmed. It is set when the quantity to order is entered by hand and cleared when the replenishment is ordered.
#. Add a "All transfers" view form in Menu: Operations
#. Add a restriction to edit operation type for users with the "Restrict editing Operation Type in Pickings" check.
#. Add number of packages on pickings
#. Print product labels from a picking with a quantity per line, and add a ZPL 5 x 2,5 cm label with two labels per row. With "Print Packaging" checked the native logic applies, also on the ZPL 5 x 2,5 cm label: one label per move with the "Copies" quantity.
#. Log routes configuration changes: routes and warehouses get a chatter, changes on their rules are logged on the route chatter, and changing the warehouse reception or delivery steps logs which rules were activated, archived or created. It is off by default and is turned on with "Track Routes Configuration Changes" in the Inventory settings.
#. Add the menu "Routes Configuration Changes" (Inventory / Configuration / Warehouse Management) with every logged change, and an optional "Procurement Rule" column on stock moves lists to see which rule created a move.
#. Create the lots a counted row names and the product does not have yet, instead of stopping the whole file at the first one.
#. Import an inventory count onto the stock lines that already exist: each row is matched by product, location, lot, package and owner, so the counted quantity replaces the quantity of that line instead of adding a second one to it.
#. Accept the columns identifying a stock line on import while they repeat what the line already holds, so a file exported from Odoo can be re-imported as it is, and name the line and the column when they do not.
#. Report which row, product or column an inventory import cannot take, instead of one message for the whole file, and refuse the columns that would move stock with no move behind them.
#. Offer an import template for inventory adjustments carrying the column that identifies each stock line, only columns an adjustment can take, and the export/fill/re-import order of work.
#. Warn, without blocking, when archiving a storable product (template or variant) that still has stock in internal or transit locations, or pending stock moves.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Go to STOCK Configuration and in the section "Products" set "Show Used Lots on Picking Operations" to see the lots you used in the move lines.

Usage
=====

To use this module, you need to:

#. Go to ...

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/stock/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
