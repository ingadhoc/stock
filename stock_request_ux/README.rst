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

#. Al cancelar un request cancelamos tambien los moves encadenados.
#. Gracias a lo anterior, si cancelamos un request order se cancelan todos los pickings vinculados
#. Agregamos ruta en request order que se lleva por defecto a los request, al cambiar la ruta tambien te las cambia en los request.
#. Al crear los procurements order creamos el procurement group, propagamos que al crearse los requests tambien se lleve ese mismo group.
#. Upon duplication of request order, duplicate lines
#. Order requests from last to first created
#. Automatically reserve the picking from stock when a request is confirmed
#. Add to stock request field "order_id" ondelete=cascade to delete stock request when stock request order related are deleted.
#. Add new button in pickings to access to the stock request order if has the group "Stock Request Order"
#. Add new button in Stock moves to access to the stock request order related.
#. Hide the "Replanishment" button in products(template/variants) when stock request was installed.

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
