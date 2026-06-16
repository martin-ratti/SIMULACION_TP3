# Simulacion de inventario con politica (s, S)

Estudio de simulacion de un sistema de inventario de un solo producto con
**politica de revision periodica (s, S)**, siguiendo el ejemplo clasico de
**Law, "Simulation Modeling and Analysis", capitulo 1.5**. Trabajo Practico
de la materia Simulacion (UTN FRRO).

El estudio simula varias politicas (s, S), estima sus costos esperados por
mes con intervalos de confianza, las rankea y recomienda la de menor costo
total. Contrasta el resultado simulado con un valor de referencia analitico
aproximado.

---

## 1. Marco teorico: el modelo (s, S)

Una empresa maneja el stock de un producto. El inventario se **revisa al
inicio de cada mes** y se decide cuanto ordenar segun una politica de dos
parametros:

- **s** (punto de reorden): umbral por debajo del cual se pide reposicion.
- **S** (nivel objetivo): nivel al que se quiere llevar el inventario.

Regla de decision en cada revision, con nivel de inventario `I`:

```
si I < s   ->  ordenar Z = S - I unidades
si I >= s  ->  no ordenar (Z = 0)
```

El inventario puede volverse **negativo**: la demanda no satisfecha no se
pierde, queda como **backlog** (faltante pendiente) y se sirve cuando llega
la reposicion. Esa es la diferencia clave con un modelo de ventas perdidas.

### Procesos estocasticos del modelo

1. **Llegada de demandas**: los clientes llegan segun un proceso de Poisson;
   los tiempos entre demandas son **Exponenciales de media 0.1 mes** (10
   demandas por mes en promedio).
2. **Tamano de la demanda**: cada cliente pide `D` unidades, una variable
   discreta con distribucion empirica:

   | D (unidades) | 1   | 2   | 3   | 4   |
   |--------------|-----|-----|-----|-----|
   | probabilidad | 1/6 | 1/3 | 1/3 | 1/6 |

   Tamano medio de demanda = `1*(1/6) + 2*(1/3) + 3*(1/3) + 4*(1/6) = 2.5`.

3. **Lag de entrega (delivery lag)**: entre que se coloca una orden y llega,
   pasa un tiempo **Uniforme(0.5, 1.0) meses**.

### Tecnica de simulacion

Simulacion de **eventos discretos** (next-event time advance). El reloj salta
de evento en evento. Hay tres tipos de evento:

- **Llegada de demanda**: descuenta `D` unidades del inventario.
- **Llegada de orden (entrega)**: suma las unidades pedidas al inventario.
- **Evaluacion (fin de mes)**: revisa el inventario y, si `I < s`, coloca una
  orden con su correspondiente lag de entrega.

---

## 2. Parametros por defecto (justificacion)

Se adoptan **exactamente los parametros del libro de Law (cap. 1.5)** porque
es el modelo de referencia de la materia: permite contrastar los resultados
de la simulacion en Python contra los del libro y contra AnyLogic.

| Parametro                     | Simbolo | Valor por defecto      |
|-------------------------------|---------|------------------------|
| Horizonte                     | n       | 120 meses              |
| Inventario inicial            | I(0)    | 60 unidades            |
| Media tiempo entre demandas   | -       | 0.1 mes (Exponencial)  |
| Tamanos de demanda            | D       | {1,2,3,4}              |
| Probabilidades de demanda     | -       | {1/6, 1/3, 1/3, 1/6}   |
| Lag de entrega                | -       | Uniforme(0.5, 1.0) mes |
| Costo fijo de ordenar (setup) | K       | 32                     |
| Costo incremental por unidad  | i       | 3                      |
| Costo de mantenimiento        | h       | 1 por unidad y mes     |
| Costo de faltante             | pi      | 5 por unidad y mes     |

Politicas (s, S) comparadas por defecto: **(20,40), (20,60), (40,60),
(40,80)** (un subconjunto de las que evalua el libro).

---

## 3. Formulas de costos

Sea `I(t)` el nivel de inventario en el instante `t`, y sean
`I^+(t) = max(I(t), 0)` (parte positiva) e `I^-(t) = max(-I(t), 0)` (backlog).

**Costo de ordenar.** Cada orden de `Z > 0` unidades cuesta `K + i*Z`; si
`Z = 0` no hay costo. El total es la suma sobre todas las ordenes colocadas:

```
ordering_total = sum_ordenes (K + i * Z)
```

**Costo de mantenimiento (holding).** Proporcional al area bajo la parte
positiva de `I(t)`:

```
area_holding   = integral_0^n I^+(t) dt
holding_total  = h * area_holding
```

**Costo de faltante (shortage).** Proporcional al area bajo el backlog:

```
area_shortage  = integral_0^n I^-(t) dt
shortage_total = pi * area_shortage
```

**Costo total promedio por mes:**

```
total_por_mes = (ordering_total + holding_total + shortage_total) / n
```

Las integrales se calculan exactamente acumulando el aporte de `I(t)` (que es
constante por tramos) entre cada par de eventos consecutivos.

### Referencia teorica (aproximada)

El modelo (s, S) con backlog **no tiene formula cerrada** para los costos
esperados (a diferencia de M/M/1). Por eso el modulo `teorico.py` solo provee:

- La **demanda media mensual** (exacta): `(1/0.1) * 2.5 = 25 unidades/mes`.
- Una **frecuencia de ordenes** aproximada: `~ demanda_media / (S - s)`.
- Un **costo de ordenar** aproximado a partir de lo anterior.

Estos valores sirven solo como sanity check del orden de magnitud. **La fuente
confiable del valor esperado es la simulacion con muchas corridas.** El
contraste de las tres fuentes (teorico aproximado / Python / AnyLogic) se hace
igual, dejando claro que la columna teorica es orientativa.

---

## 4. Como correrlo

Requiere Python 3 y matplotlib:

```bash
pip install -r requirements.txt
```

### Ejemplos

```bash
# Corrida basica: 10 replicas, sin graficas
python programa.py -r 10 --no-plots

# Estudio completo con graficas en ./output
python programa.py -r 10

# Mas replicas y mas politicas
python programa.py -r 30 --politicas "20,40;20,60;40,60;40,80;50,100"

# Cambiar costos, inventario inicial y horizonte
python programa.py -I 60 -K 32 -i 3 -H 1 -p 5 --meses 120
```

### Opciones

| Opcion                  | Default | Descripcion                            |
|-------------------------|---------|----------------------------------------|
| `-I, --inicial`         | 60      | inventario inicial I(0)                |
| `--meses`               | 120     | horizonte en meses                     |
| `-r, --corridas`        | 10      | replicas por politica                  |
| `-s, --semilla`         | 12345   | semilla base del generador             |
| `--politicas`           | 4 pares | politicas 's,S' separadas por ';'      |
| `-K, --setup`           | 32      | costo fijo de ordenar (K)              |
| `-i, --incremental`     | 3       | costo por unidad ordenada (i)          |
| `-H, --holding`         | 1       | costo de mantenimiento (h)             |
| `-p, --shortage`        | 5       | costo de faltante (pi)                 |
| `--mean-interdemand`    | 0.1     | media exponencial entre demandas       |
| `--output-dir`          | output  | carpeta de salida de graficas          |
| `--no-plots`            | -       | no generar graficas                    |

---

## 5. Que genera

**Salida por consola:**

- Valores de referencia analiticos aproximados.
- Tabla de costos (ordenar / mantenimiento / faltante / total) por politica,
  con media e intervalo de confianza del 95 %.
- Ranking de politicas por costo total medio, con la mejor marcada.

**Graficas (en `--output-dir`, por defecto `output/`):**

- `inventario_nivel.png` — nivel de inventario I(t) vs tiempo (escalonado,
  con la linea de nivel cero).
- `inventario_costos_acumulados.png` — costos acumulados (ordenar, holding,
  faltante, total) vs tiempo de simulacion.
- `inventario_comparacion_total.png` — costo total medio por politica con IC.
- `inventario_desglose_costos.png` — desglose apilado de costos por politica.

---

## 6. Estructura del proyecto

```
inventario/
├── inventario/
│   ├── __init__.py        # API publica del paquete
│   ├── rng.py             # generador congruencial lineal (TP 2.1, reutilizado)
│   ├── simulacion.py      # motor de eventos discretos (s, S)
│   ├── teorico.py         # valores de referencia analiticos aproximados
│   ├── estadisticas.py    # agregacion de replicas, IC 95 %, comparacion
│   └── plotting.py        # generacion de graficas (matplotlib Agg)
├── programa.py            # CLI (argparse)
├── requirements.txt       # matplotlib>=3.7
└── README.md              # este archivo
```

Metodologia de generacion de variables aleatorias: todas las distribuciones se
construyen sobre el **generador congruencial lineal validado en el TP 2.1**.
Los tiempos exponenciales se obtienen por transformada inversa
(`-mean * ln(U)`), el tamano de demanda por transformada inversa de una
distribucion discreta empirica, y el lag de entrega por una Uniforme(a, b).
