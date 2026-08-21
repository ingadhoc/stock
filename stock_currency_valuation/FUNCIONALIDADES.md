code# Stock Currency Valuation - Referencia funcional

## Alcance activo (cargado por manifest)

- Modelos activos:
  - `product.category`: moneda secundaria por categoría.
  - `product.product` y `product.template`: costo en moneda secundaria y cálculos de valuación.
  - `stock.move`: valor del movimiento en moneda secundaria.
  - `stock.picking`: cotización manual para ingresos de compra.
  - `product.value`: valor histórico en moneda secundaria.
  - `stock.quant`: valor secundario por quant.
  - `stock.landed.cost` y `stock.valuation.adjustment.lines`: costos de importación en moneda secundaria.
- Vistas activas:
  - categoría de producto
  - picking
  - quants
  - producto/template
  - movimientos de stock
  - histórico de valores (`product.value`)
  - landed costs
- Demo activa:
  - categoría hija de Furniture con valuación en moneda secundaria
  - producto demo en esa categoría

## Funcionalidades implementadas

### 1) Moneda secundaria por categoría

- Campo `valuation_currency_id` (company_dependent) en categoría.
- Permite definir la moneda de valuación secundaria para todos los productos de la categoría.

Archivos:
- `models/product_category.py`
- `views/product_category.xml`

### 2) Costo y valuación del producto en moneda secundaria

- Campo relacionado `valuation_currency_id` en producto y template.
- Campo `standard_price_in_currency` con:
  - compute/inverse/search en template
  - almacenamiento company_dependent en variante
- Cálculo de:
  - `avg_cost_in_currency`
  - `total_value_in_currency`
- Soporte por método de costo: `standard`, `average`, `fifo`.
- Reutiliza contexto de valuación (fecha, company, warehouse).

Archivos:
- `models/product_product.py`
- `models/product_template.py`
- `views/product.xml`

### 3) Integración con reglas de reposición

- Agrega `average_in_currency` a `replenishment_cost_type`.
- Calcula costo de reposición desde `standard_price_in_currency`, convertido a moneda del producto y luego aplica regla de reposición si corresponde.

Archivo:
- `models/product_template.py`

### 4) Histórico de valores (`product.value`) en moneda secundaria

- Extiende `product.value` con:
  - `valuation_currency_id`
  - `value_in_currency`
- En `create`, completa por defecto:
  - `value` desde `standard_price`
  - `value_in_currency` desde `standard_price_in_currency` (si aplica)

Archivos:
- `models/product_value.py`
- `views/product_value_views.xml`

### 5) Movimientos de stock con valor secundario

- Extiende `stock.move` con:
  - `valuation_currency_id`
  - `value_in_currency`
  - `value_manual_in_currency` (compute + inverse)
- En `_set_value` calcula `value_in_currency`:
  - OUT (con o sin picking) y ajustes IN sin picking: siempre `qty × standard_price_in_currency` (AVCO vigente)
  - IN con picking: usando `picking.currency_rate` si está definido, o conversión de moneda por fecha
- Muestra `value_in_currency` en vistas de movimientos y valuación.

Archivos:
- `models/stock_move.py`
- `views/stock_move_views.xml`

### 6) Picking de compras con cotización manual

- En ingresos de compra:
  - calcula `valuation_currency_id` desde las categorías de los moves
  - permite capturar `inverse_currency_rate`
  - persiste `currency_rate`
- El rate se usa luego para valuar movimientos en moneda secundaria.

Archivos:
- `models/stock_picking.py`
- `views/stock_picking.xml`

### 7) Valor secundario en quants

- Campo `secondary_value` en `stock.quant` para usuarios de stock manager.
- Cálculo: `quantity * standard_price_in_currency`.
- Sólo para quants valuables (respeta exclusiones de valuación y ubicaciones no valuadas).
- Visible en listas de quants (normal y editable), con suma en editable.

Archivos:
- `models/stock_quant.py`
- `views/stock_quant_views.xml`

### 8) Datos demo

- Activa EUR (si estaba inactiva).
- Crea categoría demo bajo Furniture:
  - método `average`
  - valuación `real_time`
  - moneda secundaria `EUR`
- Crea producto demo asignado a esa categoría.

Archivo:
- `demo/stock_currency_valuation_demo.xml`

### 9) Landed costs en moneda secundaria

- Extiende `stock.landed.cost` con:
  - `valuation_currency_id`
  - `currency_rate` / `inverse_currency_rate` (cotización manual del costo)
- Extiende `stock.valuation.adjustment.lines` con:
  - `valuation_currency_id`
  - `former_cost_in_currency`
  - `additional_landed_cost_in_currency`
  - `final_cost_in_currency`
- El valor en moneda secundaria del landed cost se descuenta del valor base del
  movimiento en `stock.move._set_value` para no contarlo dos veces.

Archivos:
- `models/stock_landed_cost.py`
- `views/stock_landed_cost_views.xml`

## Limitaciones y caveats

Cosas que el módulo **no** hace, o hace de una forma que conviene saber antes de
reportarlas como error.

### La valuación en moneda secundaria de la contabilidad aplica sólo hacia adelante

El balance inicial y la variación en moneda secundaria salen del `amount_currency` de
los apuntes de valuación. Los asientos posteados **antes** de esta versión no lo tienen,
y no se puede reconstruir: exigiría revaluar asientos ya contabilizados a una cotización
que nadie registró. Así que el histórico queda sin importe en moneda secundaria, y se
muestra así en vez de estimarlo.

### El reporte de valuación todavía no muestra la moneda secundaria

Los datos ya se guardan —los asientos del cierre y del wizard llevan `amount_currency`,
y `product.value` guarda el valor previo y el delta en moneda—, pero el reporte de
valuación de inventario sigue mostrando sólo la moneda de compañía. Las tres secciones en
moneda secundaria y el filtro por moneda de valuación quedan para una segunda etapa.

### La cuenta de valuación tiene que ser de una sola moneda

Un apunte contable lleva **una** moneda. Si una misma cuenta de valuación junta productos
valuados en monedas secundarias distintas, no hay forma de expresar las dos en la línea
del cierre, así que esa línea queda en moneda de compañía en lugar de elegir una. Mismo
criterio en el borrador del wizard: el total en moneda aparece sólo si todas las líneas
coinciden.

Los productos **sin** moneda secundaria descalifican la cuenta igual, y ese es el caso
frecuente: una categoría valuada en dólares y todo el resto del catálogo, sin moneda, en
la cuenta de valuación por defecto. La línea del cierre se parte en una línea por producto
y el importe en moneda se reparte entre **todas**, así que los productos que no se valúan
en esa moneda se llevan una parte que no les corresponde y el que sí queda con una
fracción de su propio valor (medido sobre una base con demo: de 100 en moneda secundaria
de un solo producto, ese producto se quedaba con 14,49 y el resto se repartía entre una
docena de productos de mobiliario).

**Implicancia práctica:** una categoría valuada en moneda secundaria necesita su **propia
cuenta de valuación**. Mientras comparta la cuenta con categorías sin moneda, el cierre y
el wizard trabajan esa cuenta en moneda de compañía — no se pierde información contable,
pero la columna en moneda secundaria queda vacía para esa cuenta.

### Las reclasificaciones de ubicación no se netean del lado en moneda

El `extra_balance` que el cierre netea por reclasificaciones de ubicación es hoy un
concepto sólo en moneda de compañía. La variación en moneda secundaria se calcula como
valor de inventario menos lo contabilizado, sin ese neteo.

### Cambiar la moneda de valuación de una categoría no es un flujo soportado

Se define una vez al implementar la categoría. Los `product.value` históricos **no** se
recalculan si cambia: cada uno queda pineado a la moneda vigente cuando se registró.
