.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================
Stock Request UX
================

Several improvements to Stock Request:

#. All the lines of a request order leave in a single picking: the procurements of an order share a grouping reference, and the picking origin is the name of the order.
#. Add a button in pickings (if the group "Stock Request Order" is enabled) and in stock moves to access the related stock request order.
#. Add a "Cancel remaining" button in the lines of an order in progress. It keeps on the line only what was delivered, cancels what is pending and closes the line. If other lines of the same product wait for the same stock move, that move only loses the quantity of the cancelled line.
#. Show the stock moves and the allocations of a stock request to the technical group.
#. Check that the location, warehouse and route of a stock request belong to its company.
#. Enable the "Stock Request Order" setting when the module is installed.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. No Configuration needed.

Usage
=====

To use this module, you need to:

#. Go to Stock Requests > Operations > Stock Request Orders and open an order in progress.
#. In a line that was delivered in part, click the "Cancel remaining" button (block icon) and confirm.
#. The line is left with the delivered quantity and done, and the order chatter records the change.

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
