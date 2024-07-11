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

#. If we cancel a request order, it will cancel the chained moves and all linked pickings will  be cancelled as well.
#. When creating the procurements order we create the procurement group, we propagate that so when the requests are created it also takes that same group.
#. Upon duplication of request order, duplicate lines
#. When a Stock Request Order in 'draft' state is deleted, it also deletes the Stock Request related.
#. Add new button in pickings to access to the stock request order if has the group "Stock Request Order"
#. Add new button in Stock moves to access to the stock request order related.
#. Hide the "Replenishment" button in products(template/variants) when stock request was installed.

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
