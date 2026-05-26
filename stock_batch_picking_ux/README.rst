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
#. Partner on the batch transfer:
-  The ``partner_id`` on the batch is **computed** from the partners of its pickings: it is set when all pickings share the same partner and cleared when there is a mix. It remains **editable manually** (e.g. to pre-set a partner on an empty batch and constrain which pickings can be attached via the domain).
-  Locked once the batch is ``done`` or ``cancel``.
-  Shown in the list view of batches.
#. While processing the batch picking:
-  In the transfer lines it adds information of the vouchers, from & to and source document, among others.
-  A smart button is added to go to the list view of associated transfers.
-  When you click on a transfer (from the transfer tab) you see all the possible actions that would be seen by entering it directly, such as the possibility of printing the voucher.
#. Batch Delivery Slip report:
-  A **Delivery Slip** report for batch transfers is included, analogous to the one available for individual pickings.
-  The **Print** button in the batch form view follows the same logic as native pickings: when the batch is ``in_progress`` it prints the *Batch Transfer* report; once the batch is ``done`` it prints the *Delivery Slip* instead.
-  In the ``done`` state the slip is **dual-mode**: a batch *with* partner prints the consolidated *Batch Delivery Slip* (one document for the whole batch); a batch *without* partner falls back to printing the individual delivery slip of each picking (mixed-partner batches manage delivery documents at picking level).
#. Compatibility: exposes an ``l10n_pe_edi_status`` stub on ``stock.picking.batch`` so the Peruvian EDI delivery slip block (which inherits the same primary template) does not raise at render time when the record is a batch.

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
