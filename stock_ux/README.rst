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

Several improvements to stock:

#. Add new field "Net Quantity" on stock moves only visible when you filter by locations. This fields is computed this way:

    #. If filtered location is found on source location: use negative quantity
    #. If filtered location is found on destiny location: use positive quantity
    #. If filtered location is found on source and destiny location: use 0
#. When accesing stock moves throw products group by picking type and todo
#. Add to orderpoint Rotation and Location Rotation: delivered quantities to customers on last 90 days divided per 3 (to make it monthly)
#. On draft pickings, if you change source or target locations, related moves will be update accordingly (by default they where not updated).
#. Add button "Set all Done" on Moves lines
#. Add tracking field and Messaging in "Stock Warehouse Orderpoint".
#. Add partner field on procurement group form view. Also allow to search procurements by group
#. Add button on moves to destination pickings
#. We create a new group "Allow picking cancellation", only users with that right can cancel pickings or validate without back orders
#. Add in the picking return wizard a field with the reason for the return and then bring that field to internal notes in the created picking.
#. Only allow to delete pickings on draft/cancel state.
#. Add a wizard accion in Operation to change locations.
#. Remove the technical features group in the "Forecasted" button from the product template view, to see the breakdown of incoming and outgoing stock.
#. Remove the group Tecnical Features to the seccion "Locations" in "stock move" form view from the picking view.


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
