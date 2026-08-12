.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==================================
Stock Currency Valuation Recompute
==================================

Repair tool for databases where the cost in the secondary currency drifted away
from the valuation layers.

When a revaluation does not write ``standard_price_in_currency`` on the product,
every later layer is valued from that stale cost: outgoing moves take
``standard_price_in_currency * quantity`` and incoming moves re-average on top of
it. Setting the cost on the product afterwards does not repair that history.

This module adds a tool that replays the whole valuation history of a product in
chronological order, computes what each layer should have been, shows the old and
the new values side by side, and only on confirmation writes the corrected values
back to the layers, their journal entries and the product cost.

**Manual adjustments are respected.** Only the layers created after the last manual
valuation of the product are adjusted; that adjustment and everything before it are
left exactly as they are. Without this cut, an adjustment that was compensating for a
badly valued layer ends up counted twice: once in the recomputed layer and again in
the adjustment that is still there.

The layers before the cut still take part in the replay, but with their recorded
values, not the recomputed ones. They are not going to be written, so the average
cost has to advance with what will actually remain in the database — otherwise the
product ends up with a cost derived from a history that does not exist, and it does
not add up against the valuation report.

It is meant to be installed on an affected database, run once per product, and
uninstalled afterwards. It does not change any standard behaviour while installed.

Installation
============

To install this module, you need to:

#. Only need to install the module

Configuration
=============

To configure this module, you need to:

#. Nothing to configure

Usage
=====

To use this module, you need to:

#. Go to Inventory / Reporting / Layer recompute
#. Create a record, choose the product and press "Compute lines"
#. Review the proposed values, they are not written yet
#. Press "Revaluate" to apply them

Known issues / Roadmap
======================

* Products with valuation per lot (``lot_valuated``) are not supported, the tool
  works at product level and raises instead of writing wrong costs.
* Layers coming from a landed cost are not adjusted.
* ``remaining_qty`` and ``remaining_value`` are not rewritten.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/ingadhoc/stock/issues>`_.
In case of trouble, please check there if your issue has already been reported.

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
