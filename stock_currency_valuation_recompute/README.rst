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
#. To work on several at a time, tick them in the list and use the "Compute lines" and
   "Revaluate" buttons of the header

Computing lines does not touch the layers or their journal entries — all it writes are the
recompute's own proposed lines — so the header button does it in the request and you see
the result straight away. It still replays the whole valuation history of every product in
the selection, so a selection of many products with long histories can run past the request
timeout; if that happens nothing is saved, so work in smaller groups.

Revaluating does write on the layers and on their journal entries, so the header button
applies nothing however many records you select: it moves them to *Revaluating*, and a
scheduled action applies them one by one in the background. Nothing to wait for on screen,
and no selection large enough to time out the request. Cancelling a record before the
scheduled action reaches it takes it out of the queue.

A record that fails is left in *Error* with the reason on it, and the rest of the batch
carries on. It is not retried on its own: the usual reason is a correction that starts
before the fiscal lock date, which retrying does not fix. Filter the list by *Error* to see
them; once the cause is sorted out, compute their lines again — which clears the reason —
and revaluate. Only a record with computed lines can be revaluated, so a failure of the
compute step can never be applied.

Correcting a manual revaluation
-------------------------------

Only the layers created after the last manual valuation are adjusted, so the tool never
rewrites a manual revaluation on its own. To correct one whose value in the secondary
currency was loaded wrong, drive it in two passes:

#. Compute the lines. The manual revaluation appears as a line of type *before adjustment*,
   unticked
#. Tick it, and set the value in the secondary currency to what it should be. A revaluation
   has no quantity, so the unit cost does not matter, and the company-currency side is
   already filled in with the recorded value — leave it as it is to keep the amount in
   company currency unchanged
#. Optionally, untick the remaining lines. They were computed from the wrong revaluation,
   so leaving them ticked writes them — and reposts their journal entries — with figures the
   second pass corrects anyway. The end state is the same either way; unticking only avoids
   the round trip
#. Press "Revaluate". The layer and its journal entry are corrected, and the entry is
   posted again with the same amount in company currency
#. Create a **new** recompute for the product and compute its lines. The corrected
   revaluation is now respected as the cut, and every layer after it — and the product cost
   — is recalculated from it
#. Review and press "Revaluate"

The second pass is not optional: the product cost written by the first one still comes from
the figures computed before the correction. Only after the second pass does the cost match
the sum of the layers again.

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
