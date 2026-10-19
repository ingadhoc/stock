.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==================================
Stock Removal by Location priority
==================================

Add a new removal strategy, By Location Priority, that takes the stock out of the locations with the lowest removal priority first. It also adds a Removal Priority field on locations, used to order them. This strategy replaces the order of the standard ones (FIFO, LIFO, etc), it is not appended to them.

Usage
=====

To use this module, you need to:

#. Go to Inventory > Configuration > Locations, open a location and set its
   Removal Priority. The lower the value, the sooner the stock leaves that
   location. New locations get 10.
#. Set "By Location Priority" as the Force Removal Strategy of a product
   category, or as the Removal Strategy of a location.

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

* Juan Jose Scarafia <jjs@adhoc.com.ar>
* Miquel Raïch <miquel.raich@eficent.com>
* Lois Rilo <lois.rilo@eficent.com>

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
