.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================================
Stock Ux with Batch Picking and stock vouchers
==============================================

This module add the following features:
#. Add notes tab.
#. While creating a batch picking:
-  Add the partner in the batch transfer, and then filter the transfers able to be selected according to it.
-  Add the number of packages in the batch transfer
-  For receipts, it add the supplier's shipping number.
-  When pickings are selected while creating a new batch, we allow them to check availability.
#. While proccesing the batch picking:
-  Add the possibility of processing stock.move.line from a list view.
-  In the transfer lines it add information of the vouchers, from & to and source document, among others.
-  Allow to unreserve everything from the batch
-  A smart button is added to go to the list view of associated transfers.
-  When you click on a transfer (from the transfer tab) you see all the possible actions that would be seen by entering it directly, such as the possibility of printing the voucher.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Nothing to configure


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
