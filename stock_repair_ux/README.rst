<<<<<<< 19129597dc62ea1c3e2b601c6caf18e5402cd161
.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============
Stock Repair UX
===============

Since Odoo 19, creating a repair order from a receipt is a native feature, but
it is only reachable from the "Actions" (gear) menu of the transfer, so it goes
unnoticed.

This module surfaces that same native action as a visible **Crear Reparación**
button on the header of incoming transfers (receipts and returns), without
having to enable any setting on the operation type.

Installation
============

To install this module, you need to:

#. Just install this module.

Configuration
=============

To configure this module, you need to:

#. No configuration needed.

Usage
=====

To use this module, you need to:

#. Open an incoming transfer (a receipt or a return).
#. Click the **Crear Reparación** button on the header to create a repair order
   prefilled with the transfer's partner and product.

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
||||||| 25704343f03c727970faedca558a7b9e068cd6fd
=======
.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============
Stock Repair UX
===============

Odoo shows the **Reparar** button on a transfer only when two conditions are met:
the operation type has *Create Repair Orders from Returns* enabled, and the
transfer was created with the *Return* wizard from a delivery (the only way the
internal link to the original delivery gets set).

That second condition leaves out two everyday cases:

* returns that come from a database migrated from an older version, where the
  link to the delivery does not exist;
* returns and incoming transfers loaded by hand, without an original delivery.

This module drops that second condition: the operation type is the only switch,
so every transfer of a repairable operation type offers the button. This is how
Odoo 19 behaves natively.

Installation
============

To install this module, you need to:

#. Just install this module.

Configuration
=============

To configure this module, you need to:

#. Go to *Inventory / Configuration / Operation Types* and open the type that
   receives the returns.
#. Enable *Create Repair Orders from Returns*.

Usage
=====

To use this module, you need to:

#. Open any transfer of that operation type.
#. Click the **Reparar** button on the header to create a repair order prefilled
   with the transfer's partner and location.

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
>>>>>>> f42683dfd71ba434dbdb27549e9642e343909981
