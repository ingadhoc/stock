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

1. Add button "Set all Done" on moves lines in the picking
2. Add observations on pickings (and deliveryslip)
3. Add a wizard accion in the stock move lines of a picking to change locations for several lines at the same time.
4. Show always visible (for an existing lots configuration in the type operation) the notebook pages in lot form view when create and edit a lot from a stock move line.
5. Add in the picking return wizard a field with the reason for the return and then bring that field to internal notes in the created picking.
6. Add a stock picking list report to stock pickings.
7. Add an optional setting to print in Develiry Slip reports the origin description insted of the product name.
8. We create a new group "Allow picking cancellation", only users with that right can cancel pickings or validate without back orders
9. Only allow to delete pickings on draft/cancel state.
10. Block Picking Edit: Restrict to add lines or to send a different quantity than the original quantity. This will only apply to users with group Restrict Edit Blocked Pickings.
11. Change the name of the menus "Product Move" and "Product Move lines".
12. Remove tecnical features to Stock Moves menu in Inventory>Reports.
13. Add the state "partially_available" in the "To Do" filter in stock moves
14. Add new field ""Net Quantity"" on stock moves lines. When you filter by locations, the field will be computed this way:
      1. If filtered location is found on source location: use negative quantity.
      2. If filtered location is found on destiny location: use positive quantity.
      3. If filtered location is found on source and destiny location: use "0".

15. Add in products (template and variants) a button to access to stock moves related.
16. When accesing stock moves through the products form group by picking type and filter according to do.
17. Add to orderpoint Rotation and Location Rotation: delivered quantities to customers on last 120 days divided per 4 (to make it monthly)
18. Add optional constraints configurable by Picking Type
19. Add partner field on procurement group form view.

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
