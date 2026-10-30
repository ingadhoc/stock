.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
Stock Picking State
===================

This module adds a configurable state detail (sub-status) to transfers. Each
state detail belongs to one transfer status (Draft, Waiting Another Operation,
Waiting, Ready, Done or Cancelled) and one operation type (Receipt, Delivery,
Internal Transfer or Dropship).

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Go to Inventory / Configuration / Picking State Detail.
#. Create the state details, setting for each one its name, status and
   operation type. Drag the lines to set their order.
#. Archive the state details you no longer use: they are not assigned to new
   transfers.

Usage
=====

To use this module, you need to:

#. When a transfer changes its status, it gets the first state detail (by
   sequence) that matches its new status and operation type. If its current
   state detail still matches, it is kept.
#. On the transfer form, choose another state detail next to the scheduled
   date. Only the state details of the current status and operation type can be
   chosen; any other one raises an error.
#. The state detail is also shown in the transfers list view, where you can
   search, filter and group by it, and its changes are tracked in the chatter.

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
