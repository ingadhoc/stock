.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============================
Stock Usability Improvements
============================

Several improovements to stock:
#. Make partner visible also in internal transfers (required to print valid stock vouchers when moving products between warehouses)
#. Add on stock moves Picking Creator and Picking Partner (last one already exsits but we make it stored)
#. Allow to filter and group by type of picking type on moves (internal, outgoing and incoming)
#. Add new field "Net Quantity" on stock moves only visible when you filter by locations. This fields is computed this way:
    *. If filtered location is found on source location: use negative quantity
    *. If filtered location is found on destiny location: use positive quantity
    *. If filtered location is found on source and destiny location: use 0
#. When accesing stock moves throw products group by picking type and todo
#. Add to orderpoint Rotation and Location Rotation: delivered quantities to customers on last 90 days divided per 3 (to make it monthly)
#. On draft pickings, if you change source or target locations, related moves will be update accordingly (by default they where not updated).
#. Block change of picking type in other state than 'draft'
#. Add button "Set all Done" on pack operations
#. Make moves visible on pickings no matter the state
#. Add tracking field and Messaging in "Stock Warehouse Orderpoint".
#. Add new button "cancell remaining" on procurements
#. Add partner field on procurement group form view. Also allow to search procurements by group
#. Add button on moves to destination pickings
#. We create a new group "Allow picking cancellation", only users with that right can cancel pickings or validate without back orders
#. Add in the pikcing return wizard a field with the reason for the return and then bring that field to internal notes in the created picking.
#. Backport from 10 of fix on domain of "Products" filter in Products search view.
#. Only allow to delete pickings on draft/cancel state.

Installation
============

To install this module, you need to:

#. Just install this module.


Configuration
=============

To configure this module, you need to:

#. No configuration nedeed.


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.adhoc.com.ar/

.. repo_id is available in https://github.com/OCA/maintainer-tools/blob/master/tools/repos_with_ids.txt
.. branch is "8.0" for example

Known issues / Roadmap
======================

* ...

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

* ADHOC SA: `Icon <http://fotos.subefotos.com/83fed853c1e15a8023b86b2b22d6145bo.png>`_.

Contributors
------------


Maintainer
----------

.. image:: http://fotos.subefotos.com/83fed853c1e15a8023b86b2b22d6145bo.png
   :alt: Odoo Community Association
   :target: https://www.adhoc.com.ar

This module is maintained by the ADHOC SA.

To contribute to this module, please visit https://www.adhoc.com.ar.
