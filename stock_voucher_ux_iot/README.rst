======================
Stock Voucher UX - IoT
======================

Assign preprinted voucher (remito) numbers when the report is printed through an
IoT printer.

Características
===============

- Cuando el remito preimpreso se imprime a través de una impresora IoT, asigna
  automáticamente los números de remito al picking, igual que ocurre al
  descargar el PDF desde el navegador.
- La asignación se basa en la cantidad real de páginas con productos del reporte
  renderizado (dividida por la cantidad de copias del reporte), no en una
  estimación.
- Solo aplica a talonarios preimpresos (``autoprinted = False``); los talonarios
  autoimpresos siguen numerándose en la validación.
- Es idempotente: si el picking ya tiene números asignados, un reintento de
  impresión no consume números de secuencia adicionales.

Detalles Técnicos
=================

- Modelos nuevos: ninguno.
- Modelos heredados:

  - ``ir.actions.report``: sobrescribe ``render_and_send`` (método provisto por
    el módulo ``iot``) para asignar los números de remito antes de delegar en
    ``super()``, de modo que el documento que se renderiza y se envía a la
    impresora ya los incluye. Métodos auxiliares:
    ``_is_preprinted_voucher_report`` (detecta el reporte aeroo de remito sobre
    ``stock.picking``), ``_assign_preprinted_voucher_numbers``,
    ``_count_voucher_pages`` y ``_count_pages_with_products``.

- Vistas incluidas: ninguna.
- Datos / seguridad: ninguno.

Uso
===

1. Configurar en el reporte aeroo del remito preimpreso uno o más dispositivos
   IoT de tipo impresora (campo ``IoT Devices`` de ``ir.actions.report``).
2. Asegurarse de que el picking tenga asignado un talonario preimpreso
   (``stock.book`` con ``autoprinted = False``).
3. Imprimir el remito. Al enviarse a la impresora IoT, los números de remito se
   asignan automáticamente al picking y aparecen en el documento impreso.

Arquitectura
============

Módulo puente entre ``stock_voucher_ux`` e ``iot``.

En el flujo de descarga por navegador, ``stock_voucher_ux`` asigna los números
de remito en su override del controller ``/report/download``. El camino de
impresión por IoT nunca pasa por ese controller: el handler del cliente
(``iot/static/src/iot_report_action.js``) llama a
``ir.actions.report.render_and_send``, que renderiza el documento del lado del
servidor y lo envía directo a la impresora, cortocircuitando la acción. Este
módulo cubre ese hueco enganchándose en ``render_and_send``, de forma que la
asignación de números ocurre independientemente del canal de impresión.

Dependencias
============

- ``stock_voucher_ux``
- ``iot``

Autor
=====

ADHOC SA

Licencia
========

AGPL-3
