# stock_currency_valuation — Especificación de tests

Walkthrough numérico combinado para validar el comportamiento de `standard_price_in_currency`, `value_in_currency` y `secondary_value` ante las operaciones más representativas del módulo.

## Convenciones del documento

- Compañía con moneda **ARS**, moneda secundaria de la categoría = **USD**.
- Categoría de producto: `cost_method = average`, `valuation = real_time`, `valuation_currency_id = USD`.
- Producto P en esa categoría. Estado inicial:
  - `standard_price = 0 ARS`
  - `standard_price_in_currency = 0 USD`
  - stock total = 0
- En `picking.currency_rate` y `stock.landed.cost.currency_rate` se persiste **USD por 1 ARS** (es lo que el código multiplica: `base_value × currency_rate`).
- Tasas usadas en el walkthrough:
  - Día 1: `1 USD = 1000 ARS` → `currency_rate = 0.001`
  - Día 2: `1 USD = 1200 ARS` → `currency_rate ≈ 0.000833`
  - Día 3: `1 USD = 1500 ARS` → `currency_rate ≈ 0.000667`

## Operaciones cubiertas

1. Recepción de compra con cotización manual del picking.
2. Registro de costo en destino (landed cost) sobre una recepción ya valuada.
3. Recepción de compra a otra cotización.
4. Entrega a cliente (delivery OUT).
5. Devolución del cliente (return → IN no-purchase).
6. Ajuste de inventario positivo (quant adjustment, sin `picking_id`).
7. Ajuste de inventario negativo.

## Tabla resumen del walkthrough

| Op | Día | Tipo | Qty mov. | `move.value` (ARS) | `move.value_in_currency` (USD) | Qty total | `total_value_in_currency` (USD) | `standard_price` (ARS) | **`standard_price_in_currency` (USD)** |
|----|-----|------|----------|--------------------|---------------------------------|-----------|---------------------------------|------------------------|-----------------------------------------|
| 0  | —   | Estado inicial            | —   | —      | —     | 0  | 0     | 0    | **0.00** |
| 1  | 1   | Recepción compra 1        | +10 | 10 000 | 10.00 | 10 | 10.00 | 1000 | **1.00** |
| 2  | 2   | Landed cost sobre Op 1    | —   | (+200 LC) | (+0.17)| 10 | 10.17 | 1020 | **1.02** |
| 3  | 2   | Recepción compra 2        | +10 | 24 000 | 20.00 | 20 | 30.17 | 1710 | **1.51** |
| 4  | 2   | Entrega a cliente         | -5  | -8 550 | -7.54 (qty × AVCO USD) | 15 | 22.63 | 1710 | **1.51** |
| 5  | 3   | Devolución del cliente    | +2  |  3 420 |  2.28 (conv. fecha) | 17 | 24.91 | 1710 | **1.47** |
| 6  | 3   | Ajuste de inventario +3   | +3  |  5 130 |  4.40 (qty × AVCO USD) | 20 | 29.30 | 1710 | **1.47** |
| 7  | 3   | Ajuste de inventario -2   | -2  | -3 420 | -2.93 (qty × AVCO USD) | 18 | 26.37 | 1710 | **1.47** |

## Detalle por operación

Cada bloque describe: setup específico → ejecución → asserts esperados.

### Op 1 — Recepción de compra 1 (Día 1)

**Setup**
- Crear `purchase.order` con 10 unid de P a 1000 ARS/unid.
- Confirmar y abrir el picking de incoming.
- En el picking, setear `inverse_currency_rate = 1000` (1 USD = 1000 ARS). El inverse setea `currency_rate = 0.001`.
- Validar el picking en fecha Día 1.

**Asserts sobre el move generado**
- `move.value = 10 000` (Odoo estándar)
- `move.value_in_currency = 10 000 × 0.001 = 10.00 USD`

**Asserts sobre el producto (`with_company(company)`)**
- `qty_available = 10`
- `total_value_in_currency = 10.00 USD`
- `avg_cost_in_currency = 1.00 USD`
- `standard_price = 1000 ARS` (estándar Odoo `_update_standard_price`)
- `standard_price_in_currency = 1.00 USD` (vía `_run_average_batch_in_currency(force_recompute=True)`)

**Side effects**
- Se crea `product.value` por el cambio de `standard_price_in_currency`? Depende de la rama dead-code en `write` (ver TESTING — caso 2.5 corregido). Documentar comportamiento observado.

### Op 2 — Landed cost sobre Op 1 (Día 2)

**Setup**
- Crear `stock.landed.cost` con `picking_ids = [Op 1]`, fecha Día 2.
- Una sola línea: 200 ARS, distribuido por valor.
- `inverse_currency_rate = 1200` (tasa del Día 2, fecha del LC) → `currency_rate ≈ 0.000833`.
- Validar el LC.

**Asserts sobre `stock.valuation.adjustment.lines`**
- `additional_landed_cost = 200 ARS`
- `_get_currency_rate() ≈ 0.000833` (usa `cost_id.currency_rate` del Día 2)
- `additional_landed_cost_in_currency = 200 × 0.000833 ≈ 0.17 USD`
- `former_cost_in_currency = former_cost × _get_currency_rate()` (validar fórmula: usa la tasa del LC sobre el costo previo en ARS).

**Asserts sobre el move de Op 1 después del LC**
- `move.value` ahora incluye el LC: 10 200 ARS.
- En el override `_set_value`:
  - `lc_value = 200`, `lc_value_in_currency = 200 × 0.000833 ≈ 0.17` (tasa del LC, Día 2)
  - `base_value = 10 200 - 200 = 10 000`
  - `base_value_in_currency = 10 000 × 0.001 = 10` (usa `picking.currency_rate` — tasa del Día 1, fecha de la recepción)
  - `move.value_in_currency = 10 + 0.17 = 10.17 USD`

**Asserts sobre el producto**
- `total_value_in_currency = 10.17 USD`
- `avg_cost_in_currency ≈ 1.017 USD`
- `standard_price_in_currency = 1.02 USD` (display con redondeo a 2 decimales)

**Disparidad esperada base vs. LC**: la base del move se valua con la tasa del picking (Día 1, 0.001) y el LC con la tasa del LC (Día 2, 0.000833). Es comportamiento intencional — el costo original ya fue capturado a su tasa histórica, mientras que el LC se incorpora a la tasa de su propia fecha. El test debe asertar ambas tasas explícitamente para detectar regresiones si alguien iguala las dos.

**Recompute cuando cambia la fecha sin cotización manual**: `_get_currency_rate()` cae a
`cost_id.date` cuando no hay `currency_rate` manual seteado. `_compute_amounts_in_currency`
depende de `cost_id.date` (además de `cost_id.currency_rate`) para que cambiar la fecha del LC en
borrador, antes de validar, recompute los campos `*_in_currency` guardados con la tasa de la nueva
fecha — si no dependiera de `cost_id.date`, quedarían con la tasa de la fecha vieja hasta que algo
más disparara el recompute. Cubierto por
`test_amounts_in_currency_recompute_when_date_changes` en `tests/test_landed_cost_currency.py`.

### Op 3 — Recepción de compra 2 (Día 2)

**Setup**
- `purchase.order` con 10 unid a 2400 ARS/unid.
- Picking incoming, validar Día 2.
- `inverse_currency_rate = 1200` → `currency_rate ≈ 0.000833`.

**Asserts sobre el move**
- `move.value = 24 000 ARS`
- `move.value_in_currency = 24 000 × 0.000833 ≈ 20.00 USD`

**Asserts sobre el producto (replay average)**
- Replay desde el último `product.value` o desde cero:
  - Op 1 + Op 2: in_qty=10, in_value=10.17 → qty=10, value=10.17, avg≈1.017
  - Op 3: previous_qty=10>0; in_value=20.00 → value=30.17, qty=20, avg≈1.5085
- `total_value_in_currency = 30.17`
- `standard_price_in_currency = 1.51 USD` (display redondeado)
- `standard_price` (Odoo estándar AVG) = (10 200 + 24 000) / 20 = **1710 ARS**

### Op 4 — Entrega a cliente (Día 2)

**Setup**
- `stock.picking` outgoing, 5 unid, validar Día 2.

**Comportamiento esperado**

`move.value = -5 × 1710 = -8550 ARS` (Odoo estándar).

`_set_value` ramas:
- Es OUT → cae al branch `if move._is_out() or not move.picking_id:`, independientemente de si tiene `picking_id` o de la tasa del picking.
- `value_in_currency = qty × standard_price_in_currency` (AVCO USD vigente, previo al move) = 5 × 1.508335 ≈ 7.54 USD.

**Asserts sobre el replay**
- En `_run_average_batch_in_currency`, OUT usa: `out_value = out_qty × average_cost = 5 × 1.508335 ≈ 7.54 USD` — mismo cálculo que `_set_value`, por lo que ambos coinciden por construcción.
- value = 30.17 - 7.54 = 22.63 USD; qty = 15; avg ≈ 1.5085 USD.
- `standard_price_in_currency` no se actualiza en OUT (porque `products_to_recompute` sólo se llena en IN/dropship) → **se mantiene en 1.51 USD**.

**Punto de regresión a chequear**
- Que `move.value_in_currency` del OUT sea `qty × standard_price_in_currency` (AVCO vigente), no una conversión por tasa de picking/fecha.
- Que `standard_price_in_currency` no cambie con OUTs.

**Landed cost aplicado a un OUT (caso límite, no un error de setup)**
- `stock.landed.cost.picking_ids` no restringe por dirección: la vista del core acepta pickings
  con `move_ids.is_in` **o** `move_ids.is_out` (dominio `'|'`), y `get_valuation_lines()` sólo
  filtra por `cost_method`/estado/cantidad. Un usuario puede aplicar un LC sobre una entrega ya
  validada desde la UI estándar de Landed Costs.
- El core **nunca** incorpora ese costo a `move.value` en OUT: `button_validate()` re-dispara
  `_set_value()` sobre el move, y la rama OUT del core recalcula `move.value` sólo desde
  `standard_price`/FIFO (`_get_value_from_extra` — la que sí suma landed costs — sólo se usa
  para IN). Por paridad, `_set_value` de este módulo **no suma** `lc_value_in_currency` en la
  rama OUT/sin-picking; sumarlo degradaría el invariante "OUT preserva el AVCO".
- Cubierto por `test_lc_on_out_move_does_not_pollute_value_in_currency` en
  `tests/test_landed_cost_currency.py`.

### Op 5 — Devolución del cliente (Día 3)

**Setup**
- Devolver 2 unid del picking Op 4. Genera un picking incoming nuevo, pero `purchase_id = False`.
- Validar Día 3, sin setear `inverse_currency_rate` manual.

**Asserts sobre el move**
- `move.value = 2 × 1710 = 3420 ARS` (Odoo estándar devuelve a costo actual).
- `_compute_valuation_currency_id` filtra `purchase_id and incoming` → no setea `picking.currency_rate`. Queda en 0.
- Branch `elif move.picking_id` → conversión por fecha Día 3 (0.000667).
- `move.value_in_currency = 3420 × 0.000667 ≈ 2.28 USD`.

**Asserts sobre el producto**
- Replay: previous_qty=15>0; in_value=2.28; value=22.63+2.28=24.91; qty=17; avg=24.91/17 ≈ **1.4651 USD**.
- `standard_price_in_currency ≈ 1.47 USD`.
- `standard_price` (Odoo AVG) ≈ 1710 ARS (devolución valuada a avg actual, mismo valor).

**Punto crítico**
- La tasa USADA en la devolución es la de Día 3, NO la del costo promedio histórico. Esto **degrada** el avg en USD aunque en ARS no haya cambio.
- Caso a documentar: si el negocio espera que las devoluciones de cliente sean "espejo" de la entrega, hay divergencia. Posible mejora: usar tasa del move original al que se devuelve.

### Op 6 — Ajuste de inventario +3 (Día 3)

**Setup**
- Vía `stock.quant`, ajuste de inventario +3 unidades (set quantity de X a X+3).
- En Odoo moderno, el ajuste genera un `stock.move` **sin `picking_id`**.

**Asserts sobre el move**
- `move.value = 3 × standard_price = 3 × 1710 = 5130 ARS` (Odoo estándar valua el ajuste positivo al `standard_price` vigente).
- `_set_value` override:
  ```python
  if move.is_out or not move.picking_id:
      # OUT (con o sin picking) y ajustes IN sin picking (inventario, scrap, producción):
      # qty × standard_price_in_currency (AVCO USD vigente, previo al move).
      base_value_in_currency = move._get_valued_qty() * std_price_in_currency
  elif move.picking_id.currency_rate:
      base_value_in_currency = base_value * move.picking_id.currency_rate
  else:
      # conversión por fecha (IN con picking sin tasa propia: devoluciones, etc.)
      base_value_in_currency = move.company_id.currency_id._convert(...)
  move.value_in_currency = base_value_in_currency + lc_value_in_currency
  ```
- Este ajuste es IN sin picking → cae en la primera rama. Resultado: `move.value_in_currency = 3 × 1.4651 ≈ 4.40 USD` (usa el `standard_price_in_currency` del producto justo antes del ajuste).

**Asserts sobre el producto**
- Replay (precisión interna): previous_qty=17>0; in_value=3 × 1.46514 ≈ 4.3954; value=24.9075+4.3954=29.3029; qty=20; avg=29.3029/20 ≈ **1.4651 USD** (preservado).
- `total_value_in_currency = 29.30 USD` (display redondeado a 2 decimales).
- `standard_price_in_currency = 1.47 USD` (sin cambio — el ajuste se valua al AVCO actual).

**Criterio de diseño**
- Simétrico al comportamiento de Odoo en ARS: el ajuste se valua a `standard_price`, así que en USD se valua a `standard_price_in_currency`. Esto preserva el promedio en USD (igual que el ajuste preserva el promedio en ARS).
- Todo OUT (con o sin picking, ver Op 4) cae en esta misma rama: no hay tasa de picking/fecha que tenga sentido para un egreso, así que siempre hereda el AVCO vigente. Sólo el IN con picking sin tasa propia (devoluciones, etc.) usa la conversión por fecha.

### Op 7 — Ajuste de inventario -2 (Día 3)

**Setup**
- `stock.quant` adjustment: bajar 2 unidades.

**Asserts sobre el move**
- Move sin `picking_id`, es OUT.
- `move.value = -2 × 1710 = -3420 ARS` (Odoo estándar valua el ajuste negativo al `standard_price`).
- `_set_value` rama "sin picking" (misma que Op 6): `move.value_in_currency = -2 × standard_price_in_currency = -2 × 1.4651 ≈ -2.93 USD`.

**Asserts sobre el producto**
- Replay (precisión interna): previous_qty=20>0; out_value = 2 × 1.46514 ≈ 2.9303; value = 29.3029 - 2.9303 = 26.3726; qty=18; avg ≈ 1.4651 USD.
- `total_value_in_currency = 26.37 USD` (display redondeado).
- `standard_price_in_currency` ≈ **1.47 USD** (OUT no dispara recompute; el avg queda preservado).

## Suite de tests sugerida (clases / métodos)

Organización propuesta del `tests/` (a crear):

```
tests/
    __init__.py
    common.py                              # setUpClass: ARS/USD, categ, producto, rates
    test_landed_cost_currency.py           # Op 2 + casos rate distinto
    test_delivery_and_return.py            # Op 4 + Op 5
    test_inventory_adjustment.py           # Op 6 + Op 7  (valuación por AVCO en USD)
    test_combined_walkthrough.py           # walkthrough Op 1→7 completo
    test_replenishment_cost_average_in_currency.py   # replenishment_cost_type = average_in_currency
    test_avco_report_uom.py                # cantidad del reporte AVCO en UoM de referencia
```

### `common.py` — fixture base

- Crear `res.currency` USD activa, tasas en `res.currency.rate` para días 1/2/3.
- Crear `product.category` con `valuation_currency_id = USD`, `cost_method = average`, `property_valuation = real_time`.
- Crear `product.product` P en esa categoría, con cuentas de stock/expense configuradas.
- Helpers: `_make_purchase_receipt(qty, price, rate_inverse, date)`, `_make_delivery(qty, date)`, `_make_return(picking, qty, date)`, `_make_inventory_adjustment(quantity_delta, date)`, `_make_landed_cost(picking, amount, rate_inverse, date)`.

### `test_combined_walkthrough.py`

Un solo método largo que ejecuta Op 1 a Op 7 en orden, asertando después de cada paso los 4 valores: `qty_available`, `total_value_in_currency`, `standard_price`, `standard_price_in_currency`. Esto es el test de regresión maestro.

### `test_inventory_adjustment.py`

- `test_positive_adjustment_preserves_avg` — el ajuste positivo sin picking valua el move a `+qty × standard_price_in_currency` y deja el AVCO en USD intacto (ver Op 6).
- `test_negative_adjustment_preserves_avg` — el ajuste negativo sin picking valua el move a `-qty × standard_price_in_currency` y deja el AVCO en USD intacto (ver Op 7).
- `test_positive_adjustment_with_value_manual_in_currency` — usuario setea `move.value_manual_in_currency` manualmente; valida que el replay lo respete por sobre el default heredado del AVCO.

### `test_delivery_and_return.py`

- `test_delivery_does_not_change_std_price_in_currency` — invariante.
- `test_return_uses_current_date_rate` — confirma la conversión por fecha (Op 5).
- `test_return_with_currency_rate_match` — escenario donde se setea manualmente la tasa del momento original; el avg en USD se preserva.

### `test_landed_cost_currency.py`

- `test_lc_uses_lc_currency_rate_when_set`.
- `test_lc_falls_back_to_today_rate_when_unset`.
- `test_lc_with_rate_different_from_picking` — disparidad esperada/documentada.
- `test_lc_zero_in_currency_when_company_eq_valuation` — categoría con `valuation_currency = company.currency_id`.

### `test_replenishment_cost_average_in_currency.py`

- `test_average_in_currency_converts_using_valuation_currency_rate` — con
  `replenishment_cost_type = 'average_in_currency'`, el costo de reposición
  convierte `standard_price_in_currency` a la moneda del producto a la
  cotización del día, y sigue el cambio de cotización entre Día 1 y Día 2.
- `test_average_in_currency_applies_replenishment_cost_rule_on_converted_amount` —
  la regla de reposición se aplica sobre el importe ya convertido, no sobre el
  valor en moneda secundaria.

Regresión que cubre: la conversión usaba `fields.date.today()` (minúscula), que
no existe en `odoo.fields`, así que leer `replenishment_cost` rompía con
`AttributeError`.

### `test_avco_report_uom.py`

- `test_avco_report_quantity_in_product_uom` — una recepción de 1 docena informa
  cantidad 12 en el reporte de auditoría AVCO, no 1: la vista tiene que convertir a
  la UoM de referencia del producto.
- `test_avco_report_unit_cost_uses_converted_quantity` — el costo unitario del
  reporte se calcula sobre la cantidad convertida.

Regresión que cubre: la vista SQL de este módulo es copia de la del core y había
perdido la conversión de UoM, así que el AVCO salía 12 veces más caro en productos
comprados en una unidad distinta a la de stock.

## Datos y precisión

- Las tasas de cambio se settean vía `res.currency.rate.create(...)` para los 3 días.
- Para tasas inversas redondas (1000, 1200, 1500), `currency_rate = 1/n` da decimales no exactos: tolerar `± 0.01 USD` en asserts (`self.assertAlmostEqual(..., places=2)`).
- Las cifras de `total_value_in_currency` se redondean por `currency_field` → respeta `USD.rounding` (0.01 por defecto).

## Casos no cubiertos en este walkthrough (pendientes)

- Multi-warehouse y `ratio_by_product_id`.
- Multi-compañía: mismo producto con `valuation_currency` distinta por compañía (company_dependent).
- Lot-valuated: hoy se devuelve 0; testear que no rompa.
- Cost method `fifo`: testear `_run_fifo_batch_in_currency` (usa tasa de **hoy**, no de los moves).
- Cost method `standard`: que `standard_price_in_currency` NO se autorecompute (decisión actual).
- Dropship: `is_dropship and (is_in or is_out)` — comportamiento doble.
- `valuation_currency_id == company.currency_id`: caminos atajo en `stock_landed_cost._compute_amounts_in_currency`.
