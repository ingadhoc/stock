.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========================
Stock Report Substitute
===========================


This module serves as a bridge between the stock and the OCA's ``report_substitute`` module.
It solves the error that occurs when digitally signing delivery slips when there's a substitution report configured.

This module modifies the ``_attach_sign`` method in the ``stock.picking`` model to:

#. Check if there's a substitute report for the delivery report
#. If there is a substitute: render that report directly
#. If there isn't: use Odoo's standard flow

This ensures that digital signing works correctly for both native and substitute reports.

Installation
============

To install this module, you need to:

#. Install this module

Configuration
=============

To configure this module, you need to:

#. No additional configuration is required. The module works automatically once installed.

Usage
=====

To use this module, you need to:

#. Configure report substitution rules in the ``report_substitute`` module
#. When digitally signing delivery slips, the module will automatically handle report substitution

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
