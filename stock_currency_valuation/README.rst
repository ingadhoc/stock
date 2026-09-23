.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

========================
Stock Currency Valuation
========================

Permite llevar la valuación del inventario en una moneda secundaria, definida por categoría de producto, en paralelo a la moneda de la compañía. La valuación contable no cambia: los asientos de inventario se siguen registrando en la moneda de la compañía.

* **Moneda de valuación por categoría.** Todos los productos de la categoría calculan su costo y su valor de inventario también en esa moneda. Funciona con costo estándar, promedio y FIFO.
* **Cotización manual en las recepciones de compra.** En el ingreso se puede cargar la cotización con la que se valúa la mercadería en moneda secundaria. Si no se carga, se usa la cotización de la fecha.
* **Valor en moneda secundaria** en movimientos de stock, cantidades en stock (quants), historial de costos y reporte de costo promedio.
* **Costos en destino** con su propia cotización y el costo final también en moneda secundaria.
* **Reposición:** agrega el tipo de costo de reposición "promedio en moneda".

**A tener en cuenta:**

* El reporte de valuación de inventario todavía muestra solo la moneda de compañía.
* La moneda de valuación de una categoría se define una sola vez. Cambiarla después no está soportado.
