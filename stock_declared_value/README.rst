.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

====================
Stock Declared Value
====================

This module adds Declared Value field on stock pickings and automatic computation based on:

   * Sale order lines (if linked to a sale)
   * Pricelist configured in picking type (if no sale order)
   * Support for BOM/Kit products
   * Currency conversion to company currency

Installation
============

To install this module, you need to:

#. Install the module from Apps menu

Configuration
=============

To configure this module, you need to:

#. Go to **Inventory / Configuration / Operations Types**
#. Configure the following fields:

   * **Pricelist**: Select a pricelist to use for automatic declared value calculation
   * **Automatic Declare Value**: Enable to automatically compute declared value

Usage
=====

Declared Value
--------------

#. Create a sale order and confirm it
#. The delivery order will automatically calculate the declared value based on:

   * Sale order lines prices (primary source)
   * Pricelist from picking type (if no sale order)

#. The declared value is shown in the delivery order form
#. The value is automatically converted to company currency

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
