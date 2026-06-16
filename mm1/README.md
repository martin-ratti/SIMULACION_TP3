# Simulacion de colas M/M/1 y M/M/1/K

Estudio de simulacion de eventos discretos de un sistema de colas de un solo
servidor, con dos variantes:

- **M/M/1**: cola de capacidad **infinita**. Todo cliente que llega entra al
  sistema.
- **M/M/1/K**: cola de capacidad **finita** K. Cuando el sistema ya tiene K
  clientes (en cola + en servicio), un nuevo arribo es **rechazado**
  (denegacion de servicio / bloqueo).

El objetivo es **contrastar** las medidas de rendimiento obtenidas por
simulacion contra las **formulas analiticas** de la teoria de colas, y estudiar
como evolucionan respecto del **tiempo de simulacion**, del **factor de
utilizacion** rho y del **tamano de la cola** K.

La fuente de aleatoriedad es el **Generador Congruencial Lineal (GCL)** validado
en el TP 2.1 (`cola/rng.py`, configuracion MINSTD: a = 48271, c = 0,
m = 2^31 - 1). Los tiempos exponenciales se obtienen por **transformada inversa**.

---

## Marco teorico

### Notacion

| Simbolo | Significado |
|---------|-------------|
| lambda  | Tasa media de arribos |
| mu      | Tasa media de servicio |
| rho     | Factor de utilizacion = lambda / mu |
| L       | Numero medio de clientes en el sistema |
| Lq      | Numero medio de clientes en la cola |
| W       | Tiempo medio en el sistema (espera + servicio) |
| Wq      | Tiempo medio de espera en la cola |
| Pn      | Probabilidad de hallar n clientes en el sistema |

Arribos segun un proceso de Poisson (tiempos entre arribos exponenciales de
media 1/lambda) y servicio exponencial de media 1/mu. Disciplina **FIFO**, un
solo servidor.

### M/M/1 (cola infinita)

Valida **solo si rho < 1** (sistema estable). Si rho >= 1 la cola crece sin
limite y las medidas divergen a infinito.

```
rho = lambda / mu

L  = rho / (1 - rho)
Lq = rho^2 / (1 - rho)
W  = 1 / (mu - lambda)
Wq = rho / (mu - lambda)

Pn = (1 - rho) * rho^n        (n = 0, 1, 2, ...)
```

### M/M/1/K (cola finita)

**Siempre estable**, incluso con rho >= 1, porque la capacidad K acota el
sistema.

```
            rho^n * (1 - rho)
Pn  =  ------------------------       si rho != 1,   0 <= n <= K
            1 - rho^(K+1)

Pn  =  1 / (K + 1)                    si rho == 1

P_bloqueo = Pn(K)                     (prob. de denegacion / rechazo)

L  = sum_{n=0}^{K} n * Pn(n)
Lq = L - (1 - Pn(0))                  (clientes en servicio = utilizacion real)
```

Las medidas temporales usan la **tasa de arribos efectiva**
`lambda_eff = lambda * (1 - P_bloqueo)` (solo los clientes admitidos atraviesan
el sistema), aplicando la **Ley de Little**: `W = L / lambda_eff`,
`Wq = Lq / lambda_eff`.

### Caso rho >= 1 (importante)

Para `rho = 1.0` y `rho = 1.25` la **cola infinita es inestable**: las formulas
dan L, Lq, W, Wq = infinito. La simulacion igual corre y se "estabiliza" de
forma artificial por el horizonte temporal finito, pero **no se la compara**
contra la formula infinita. El analisis con sentido en ese regimen es el de la
**cola finita M/M/1/K**, cuya formula **si** se compara contra la simulacion.
El programa marca explicitamente este caso en su salida.

---

## Como funciona la simulacion

Motor de **avance al proximo evento** (next-event time-advance, Law cap. 1.4):

1. Se mantiene un reloj de simulacion y un calendario con dos eventos:
   proximo arribo y proxima partida.
2. En cada paso se avanza el reloj hasta el evento mas proximo y se procesa.
3. Entre eventos el numero de clientes es constante, asi que los promedios
   temporales **L** y **Lq** se calculan integrando por areas
   (acumulando `num_clientes * delta_t`).
4. Se registran ademas: tiempos de espera por cliente (para W y Wq), tiempo de
   servidor ocupado (para la utilizacion observada), contadores de arribos,
   atendidos y rechazados (para la denegacion), histograma temporal de n
   clientes (para Pn) y una serie temporal muestreada de L(t).

Para cuantificar la incertidumbre se corren **N replicas** independientes (cada
una con otra semilla) y se construye un **intervalo de confianza al 95%** con la
**t de Student** (z = 1.96 para N >= 30). Medias, varianzas e intervalos se
calculan a mano, sin numpy ni scipy.

---

## Estructura

```
mm1/
├── cola/
│   ├── __init__.py        API publica del paquete
│   ├── rng.py             GCL (generador del TP 2.1) - NO modificar
│   ├── simulacion.py      motor de eventos discretos (M/M/1 y M/M/1/K)
│   ├── teorico.py         formulas analiticas
│   ├── estadisticas.py    replicas + intervalos de confianza
│   └── plotting.py        graficas (matplotlib backend Agg)
├── programa.py            CLI del estudio completo
├── requirements.txt       matplotlib>=3.7
└── README.md
```

---

## Como correrlo

Instalar la dependencia (solo matplotlib, para las graficas):

```bash
pip install -r requirements.txt
```

Correr el estudio completo (tablas + graficas):

```bash
python programa.py
```

Solo las tablas numericas, sin graficas (mas rapido):

```bash
python programa.py -r 10 -t 3000 --no-plots
```

Personalizar parametros:

```bash
python programa.py -m 1.0 -r 20 -t 5000 --rhos 0.5,0.8 --colas 2,5,10
```

### Opciones de la CLI

| Opcion | Descripcion | Default |
|--------|-------------|---------|
| `-m`, `--mu` | Tasa de servicio mu | `1.0` |
| `-r`, `--corridas` | Replicas por configuracion | `10` |
| `-t`, `--tiempo` | Tiempo de simulacion por corrida | `5000` |
| `-s`, `--semilla` | Semilla base del generador | `12345` |
| `--rhos` | Factores de utilizacion (coma-separados) | `0.25,0.5,0.75,1.0,1.25` |
| `--colas` | Capacidades de cola finita K | `0,2,5,10,50` |
| `--output-dir` | Carpeta de salida de graficas | `output` |
| `--no-plots` | No generar graficas | (desactivado) |

---

## Que genera

**Salida por consola:**

- **Parte 1** – Tabla por cada rho con las medidas de la cola infinita:
  simulado (media + IC 95%) vs teorico, con el error relativo. Para rho >= 1
  marca la inestabilidad y omite la comparacion infinita.
- **Parte 2** – Tabla por cada rho con la probabilidad de denegacion de la cola
  finita M/M/1/K para cada K: simulado (media + IC 95%) vs teorico.

**Graficas** (en `output/`, salvo `--no-plots`):

- `L_evolucion_rho_*.png` – Evolucion de L(t) y su promedio acumulado vs el
  tiempo de simulacion (convergencia al estacionario).
- `pn_infinita_rho_*.png` – Distribucion Pn simulada (steelblue) vs teorica
  (crimson), cola infinita.
- `pn_finita_K*_rho_*.png` – Distribucion Pn de la cola finita.
- `medida_{L,Lq,W,Wq}_vs_rho.png` – Cada medida simulada vs teorica a traves de
  los rho.
- `denegacion_vs_K.png` – Probabilidad de denegacion vs tamano de cola K, una
  curva por rho.

---

## Validacion rapida

Para `rho = 0.5` y `mu = 1.0` los valores teoricos son `L = 1.0`, `Lq = 0.5`,
`W = 2.0`, `Wq = 1.0`, `rho_obs = 0.5`. La simulacion debe aproximarse a estos
valores dentro del intervalo de confianza.
