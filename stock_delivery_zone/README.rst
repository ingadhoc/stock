.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
Stock Delivery Zone
===================

#. Add delivery zones, a simple list of zones that can be archived.
#. Add a "Zone" field on contacts, below the address, also on the Delivery, Invoice and Other addresses of the "Contacts & Addresses" tab.
#. Show the zone of the transfer contact on delivery orders, read only.
#. Print the zone below the delivery address on the Delivery Slip and on the Picking Operations report.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Go to Contacts / Configuration / Zones and create the zones. Only users with Settings access can create, edit or delete zones.
#. Set the "Zone" on each contact.

Usage
=====

To use this module, you need to:

#. Create a delivery order for a contact with a zone: the zone is shown next to the contact.
#. Print the Delivery Slip or the Picking Operations report: the zone is printed below the delivery address.

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
