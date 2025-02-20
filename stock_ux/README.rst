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
#. Add reason return field in the picking return wizard and then bring that field to internal notes in the created picking.
#. Add an optional setting to print in Delivery Slip reports the origin description instead of the product name
#. We create a new group "Allow picking cancellation", only users with that right can cancel pickings or validate without back orders
#. Only allow to delete pickings on draft/cancel state and "Block Picking Deletion?" is not checked in Pick operation type.
#. If filtered location is found on source location: use negative quantity.
#. Add new field ""Net Quantity"" in stock moves lines. When you filter by locations, the field will be computed this way:
#. If filtered location is found on destiny location: use positive quantity.
#. If filtered location is found on source and destiny location: use "0".
#. Add in products (template and variants) a button to access to stock moves related.
#. When accessing stock moves through the products form group by picking type and filter according to do.
#. Add Rotation and Location Rotation to Reordering Rules (orderpoint): delivered quantities to customers on last 120 days divided per 4 (to make it monthly)
#. Add optional constraints configurable by Picking Type: Block additional quantity, Block force availability, Block picking deletion
#. Add partner field on procurement group form view.
#. Show location and warehouse filters on all products and product templates views (not only the one on inventory)
#. When archive a replenishment rule set min, max and multiple quantities in 0.
#. Show inactive replenishment rules if the product is active (with warning decorator).
#. Send template established in operation type when confirm picking.
#. Add an optional setting to print remaining quantities not yet delivered on Delivery Slips: "Show remaining quantities not yet delivered on Delivery Slips."print remaining quantities not yet delivered
#. Adds a review toggle per line that allows the user to indicate when the replenishment order is ready to be confirmed.
#. Add a "All transfers" view form in Menu: Operations

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
