# Guia paso a paso: modelo de Inventario (s, S) en AnyLogic

Esta guia reproduce en **AnyLogic** el mismo modelo de inventario de revision
periodica **(s, S)** que simula `programa.py` (parametros de Law, cap. 1.5),
para obtener la **tercera fuente de datos** del TP (valor teorico / Python /
AnyLogic) y contrastar las tres.

> **Como usar esta guia con ayuda de IA.** Cada paso es una instruccion concreta.
> A diferencia del modelo M/M/1 (que se arma con bloques de la *Process Modeling
> Library*), el inventario (s,S) **NO** es un sistema de colas: es un sistema de
> **dinamica de eventos sobre una variable de estado** (el nivel de inventario).
> Por eso lo mas comodo es modelarlo con **System Dynamics / variables + eventos**
> o directamente con codigo Java en `Main`, no arrastrando Source/Queue/Sink.
> Si la IA propone Source/Queue, corregila: aca no aplica.

## 0. Que estamos modelando (resumen)

- Hay un **nivel de inventario** `I` (entero, puede ser negativo = backlog).
- Llegan **demandas** de clientes en tiempos aleatorios; cada una resta unidades.
- **Cada mes** se revisa `I`: si `I < s` se ordena hasta `S` (se pide `S - I`).
- La orden tarda en llegar un **lag** aleatorio.
- Se acumulan tres costos: **ordenar**, **mantenimiento (holding)** y
  **faltante (shortage)**.

| Parametro | Valor (Law) | Significado |
|---|---|---|
| `I0` | 60 | inventario inicial |
| `nMonths` | 120 | horizonte (meses) |
| demanda | {1,2,3,4} con prob {1/6,1/3,1/3,1/6} | tamano de cada pedido |
| `meanInterdemand` | 0.1 mes | media del tiempo entre demandas (exponencial) |
| `K` (setup) | 32 | costo fijo por orden |
| `incCost` | 3 | costo por unidad ordenada |
| `holdingCost` | 1 | costo por unidad-mes en stock (I>0) |
| `shortageCost` | 5 | costo por unidad-mes faltante (I<0) |
| lag entrega | Uniforme(0.5, 1.0) mes | demora de la orden |

---

## 1. Crear el modelo

1. **File > New > Model**. Nombre: `Inventario`. Model time units: **months**.
2. Queda abierto el agente `Main`. Todo se arma sobre `Main`.

---

## 2. Parametros (editables para la clase)

Arrastrar desde la paleta **Agent** estos *Parameter* a `Main` (asi se cambian
sin tocar codigo, cumpliendo "facilitar el ingreso de parametros"):

| Nombre | Tipo | Default |
|---|---|---|
| `s` | int | `20` |
| `S` | int | `40` |
| `nMonths` | int | `120` |
| `meanInterdemand` | double | `0.1` |
| `setupCost` | double | `32` |
| `incCost` | double | `3` |
| `holdingCost` | double | `1` |
| `shortageCost` | double | `5` |

> Para comparar politicas, en clase se cambian solo `s` y `S`:
> (20,40), (20,60), (40,60), (40,80).

---

## 3. Variables de estado

Arrastrar a `Main` (paleta **Agent > Variables**):

| Variable | Tipo | Inicial | Para que |
|---|---|---|---|
| `inv` | int | `60` | nivel de inventario actual `I` |
| `lastEventTime` | double | `0` | momento del ultimo evento (para integrar) |
| `orderingCost` | double | `0` | acumulador costo de ordenar |
| `holdingArea` | double | `0` | integral de `max(inv,0)` en el tiempo |
| `shortageArea` | double | `0` | integral de `max(-inv,0)` en el tiempo |
| `amountOnOrder` | int | `0` | unidades pedidas aun no entregadas |

> `holdingCost_total = holdingCost * holdingArea` y
> `shortageCost_total = shortageCost * shortageArea` al final.

### 3.1 Funcion de actualizacion de areas (clave)
Crear una **Function** `updateAreas()` (tipo: void, sin retorno) con este
codigo. Se llama **al principio de cada evento**, antes de cambiar `inv`:

```java
double dt = time() - lastEventTime;
if (inv > 0) holdingArea  += inv * dt;
if (inv < 0) shortageArea += (-inv) * dt;
lastEventTime = time();
```

Esto integra el area bajo `I(t)` separando la parte positiva (holding) de la
negativa (shortage) — exactamente lo que hace el motor de Python.

---

## 4. Eventos del modelo

### 4.1 Demanda de clientes (Event ciclico, disparo por tiempo exponencial)
Arrastrar un **Event** (paleta **Agent**). Nombre: `demandEvent`.
- *Mode*: **Cyclic**
- *Recurrence time*: `exponential(1 / meanInterdemand)`
  (exponencial de **media** `meanInterdemand`; recordar que en AnyLogic
  `exponential(rate)` tiene media `1/rate`, por eso el `1/...`).
- *Action*:
```java
updateAreas();
// tamano de la demanda: empirica {1,2,3,4} con prob {1/6,1/3,1/3,1/6}
double u = uniform();
int d;
if      (u < 1.0/6) d = 1;
else if (u < 1.0/6 + 1.0/3) d = 2;
else if (u < 1.0/6 + 2.0/3) d = 3;
else d = 4;
inv -= d;
```

### 4.2 Revision mensual (Event ciclico cada 1 mes)
Arrastrar otro **Event**. Nombre: `reviewEvent`.
- *Mode*: **Cyclic**
- *First occurrence time*: `0`
- *Recurrence time*: `1` (un mes)
- *Action*:
```java
updateAreas();
if (inv < s) {
    int z = S - inv;                  // cantidad a ordenar
    orderingCost += setupCost + incCost * z;
    amountOnOrder += z;
    // programar la entrega tras un lag Uniforme(0.5, 1.0)
    double lag = uniform(0.5, 1.0);
    create_deliveryEvent(z, lag);     // ver 4.3
}
```

### 4.3 Entrega de la orden (Dynamic Event)
La entrega ocurre **una sola vez** por orden, tras el lag. Para eso usar un
**Dynamic Event** (paleta **Agent > Dynamic Event**). Nombre: `deliveryEvent`.
- Agregar un **parametro** al Dynamic Event: `int qty`.
- *Action*:
```java
updateAreas();
inv += qty;
amountOnOrder -= qty;
```
- Se dispara desde `reviewEvent` con `create_deliveryEvent(z, lag);`
  (AnyLogic genera ese metodo automaticamente: primer arg = parametros del
  evento, ultimo arg = tiempo hasta que ocurre).

> Si tu version de AnyLogic nombra distinto el metodo de creacion, la IA lo
> resuelve: el patron es "Dynamic Event con un parametro `qty`, agendado a
> `lag` meses".

---

## 5. Parar la simulacion al final del horizonte

En las propiedades del experimento *Simulation*:
- *Stop*: **Stop at specified time**, *Stop time* = `nMonths` (120).

O bien un **Event** `stopEvent` (Timeout, en `time() == nMonths`) que llame a
`updateAreas()` una ultima vez y luego calcule los costos finales (ver paso 6).

---

## 6. Calcular los costos finales (medidas del TP)

Crear una **Function** `finalCosts()` que se llama al terminar (o leer estas
expresiones directo en textos en pantalla):

```java
updateAreas();  // cierra la ultima franja temporal
double ordering = orderingCost / nMonths;
double holding  = holdingCost  * holdingArea  / nMonths;
double shortage = shortageCost * shortageArea / nMonths;
double total    = ordering + holding + shortage;
```

Estas cuatro son **exactamente** las medidas que pide el TP:
**costo de orden, costo de mantenimiento, costo de faltante y costo total**
(todas promedio por mes).

---

## 7. Mostrar en pantalla + grafico de I(t)

- Agregar **Text** dinamicos en `Main` mostrando `ordering`, `holding`,
  `shortage`, `total` y `inv` actual.
- Agregar un **Time Plot** que grafique `inv` vs `time()` -> reproduce la
  grafica escalonada de nivel de inventario `I(t)` (la misma que
  `inventario_nivel.png` de Python). Marcar una linea horizontal en `0` para
  ver cuando entra en backlog.
- Opcional: un **Time Stack Chart** con los costos acumulados (ordering /
  holding / shortage) para reproducir `inventario_costos_acumulados.png`.

---

## 8. Correr 10+ replicas (lo que exige el TP)

El TP pide **minimo 10 corridas por experimento**.

1. Click derecho en el modelo -> **New > Experiment > Monte Carlo**
   (o *Parameter Variation* con *Replications*).
2. *Number of replications*: `10` (o mas).
3. *Randomness*: **Random seed (unique simulation runs)** — cada replica con
   semilla distinta.
4. Recolectar en *DataSet/Histogram* los valores finales de `ordering`,
   `holding`, `shortage`, `total`. AnyLogic da **media y desvio** entre
   replicas -> de ahi el intervalo de confianza para comparar con Python.

---

## 9. Comparar las 4 politicas (s, S)

El TP pide justificar la eleccion de parametros comparando alternativas.

- **Manual:** correr el Monte Carlo (10 replicas) 4 veces, una por cada par:
  (20,40), (20,60), (40,60), (40,80). Anotar el costo total medio.
- **Automatica (mejor):** un experimento **Parameter Variation** que recorra
  esos 4 pares de `(s, S)` con 10 *replications per iteration*, y grafique el
  costo total medio por politica -> reproduce `inventario_comparacion_total.png`.

> Resultado esperado (coincide con Python): la mejor suele ser **(20, 60)**,
> con costo total ~121-122 por mes. Las otras quedan en ~127. Confirmar que
> AnyLogic da el mismo ranking valida las tres fuentes.

---

## 10. Exportar para el informe

Para la tabla comparativa de las **tres fuentes** del informe LaTeX:

- Anotar, por cada politica (s,S): ordering / holding / shortage / total de
  AnyLogic (media +/- desvio de las 10 replicas).
- Si AnyLogic exporta a Excel/CSV, guardarlo en `inventario/output/anylogic/`.

Esos numeros van despues en las columnas `% TODO AnyLogic` del
`informe/informe.tex`.

---

## Checklist final

- [ ] Modelo `Inventario.alp` con variables `inv`, areas, costos.
- [ ] `updateAreas()` integrando holding y shortage por separado.
- [ ] `demandEvent` (exponencial) restando demanda empirica {1,2,3,4}.
- [ ] `reviewEvent` mensual con politica (s,S) y costo de ordenar.
- [ ] `deliveryEvent` (Dynamic Event) con lag Uniforme(0.5,1).
- [ ] Stop a los `nMonths` meses y calculo de las 4 medidas.
- [ ] Time Plot de `inv` vs tiempo (con linea en 0).
- [ ] Monte Carlo con 10+ replicas, semilla unica.
- [ ] Barrido de las 4 politicas (s,S) con su ranking.
- [ ] Resultados anotados/exportados para la tabla de 3 fuentes.

## Equivalencias rapidas Python <-> AnyLogic

| Concepto | Python (`programa.py`) | AnyLogic |
|---|---|---|
| Tiempo entre demandas | `-mean*ln(U)` (LCG) | `exponential(1/meanInterdemand)` |
| Tamano de demanda | inversa sobre {1,2,3,4} | bloque `if/else` con `uniform()` |
| Revision mensual (s,S) | evento fin de mes | `reviewEvent` ciclico cada 1 |
| Lag de entrega | `uniform(0.5,1)` | Dynamic Event a `uniform(0.5,1)` |
| Area holding/shortage | integra `I(t)` por tramos | `updateAreas()` con `dt` |
| 10 corridas | `-r 10` (semillas) | Monte Carlo, 10 replicas, seed unico |
| Comparar politicas | `--politicas "20,40;..."` | Parameter Variation sobre (s,S) |
