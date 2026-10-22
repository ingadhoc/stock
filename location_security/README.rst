.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=================
Location Security
=================

Restrict the stock locations a user can validate transfers from and to. When a restricted user validates a transfer, its source and destination locations must be among the user's allowed locations or their sublocations; otherwise the validation is blocked with an error that lists the locations the user does not control.

The restriction applies only when validating a transfer, including through the backorder wizard. It does not hide locations or transfers, and it does not apply to stock moves done outside the transfer validation, such as scraps, or to cancelled moves.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Go to Settings>Users & Companies>Users.
#. Select the user you want to configure.
#. Under the Preferences tab, in the Locations section, enable the Restrict Locations option.
#. In Allowed Locations, set the locations the user is allowed to work with. Their sublocations are allowed too. Include the partner locations the transfers use, such as Vendors or Customers.

Usage
=====

To use this module, you need to:

#. Validate transfers as usual. If the user has restricted locations and a transfer uses a location that is not allowed, the validation is blocked.
#. On a location form, Restricted Users shows the restricted users that have that location among their allowed locations.

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
