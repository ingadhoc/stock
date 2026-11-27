.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================================
Stock currency valuation - Purchase
===================================

Puente entre ``stock_currency_valuation`` y ``purchase_stock``.

Cuando una compra está en la moneda de valuación de la categoría y la recepción tiene una cotización manual, el valor en esa moneda es el precio de la compra y el valor en la moneda de la compañía es ese precio a la cotización manual. Vale para el precio de la orden de compra y para el de la factura. Sin cotización manual, se usa la cotización de la fecha, como en el estándar.

Installation
============

Se instala solo cuando están ``stock_currency_valuation`` y ``purchase_stock``.

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
