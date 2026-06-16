# Guia paso a paso: modelo M/M/1 en AnyLogic

Esta guia reproduce en **AnyLogic** (Personal Learning Edition sirve) el mismo
sistema de colas M/M/1 que simula `programa.py`, para obtener la **tercera
fuente de datos** del TP (valor teorico / Python / AnyLogic) y poder
contrastar las tres.

> **Como usar esta guia con ayuda de IA.** Cada paso esta escrito como una
> instruccion atomica y concreta. Si te trabas, copiale a la IA el numero de
> paso + lo que ves en pantalla. Los nombres de bloques (Source, Queue,
> Service, Sink) son los exactos de la *Process Modeling Library* de AnyLogic,
> asi que la IA los va a reconocer.

## 0. Referencia: modelos de ejemplo del libro

En el material del curso ya hay modelos M/M/1 resueltos que conviene tener
abiertos al lado como referencia (libro *The Art of Process-Centric Modeling
with AnyLogic*):

| Modelo de ejemplo | Carpeta | Que muestra |
|---|---|---|
| **Base Model** | `Models/Chapter 2/02. Base Model/Base Model.alp` | M/M/1 clasico (Source -> Queue -> Service -> Sink) |
| With Truncation | `Models/Chapter 2/04. With Truncation/` | Cola **finita** M/M/1/K (con denegacion de servicio) |
| Erlang Loss | `Models/Chapter 2/05. Erlang Loss/` | Sistema con perdida (bloqueo cuando esta lleno) |
| Multi Server | `Models/Chapter 2/03. Multi Server/` | M/M/c (varios servidores) — no lo necesitamos, solo de referencia |

> Abri primero `Base Model.alp`, miralo funcionar, y despues replicalo desde
> cero siguiendo esta guia. Reproducir > copiar te da el entendimiento que pide
> el TP.

---

## 1. Crear el modelo

1. Abrir AnyLogic -> **File > New > Model**.
2. Nombre: `MM1`. Unidad de tiempo del modelo: **minutes** (Model time units:
   `minutes`). Finish.
3. Va a quedar abierto el agente `Main` con un canvas vacio. Todo el diagrama
   de procesos se arma sobre `Main`.

---

## 2. Parametros (para "facilitar el ingreso de parametros en clase")

El TP pide poder variar los parametros para mostrar en clase. En AnyLogic eso
se hace con **Parameters** del agente `Main`, asi se editan desde la ventana de
propiedades sin tocar bloques.

Desde la paleta **Agent** arrastrar al canvas de `Main` estos *Parameter*:

| Nombre | Tipo | Valor por defecto | Significado |
|---|---|---|---|
| `lambda_` | double | `0.5` | tasa de arribo (clientes/min) |
| `mu` | double | `1.0` | tasa de servicio (clientes/min) |
| `K` | int | `-1` | capacidad de la cola finita; `-1` = cola infinita |

> Se usa `lambda_` con guion bajo porque `lambda` es palabra reservada de Java.
>
> Para los experimentos del TP, `lambda_` se setea como `rho * mu` con
> `rho` en {0.25, 0.5, 0.75, 1.0, 1.25}. Con `mu = 1.0`, basta poner
> `lambda_` = 0.25, 0.5, 0.75, 1.0 o 1.25.

---

## 3. Diagrama de proceso (Source -> Queue -> Service -> Sink)

Abrir la paleta **Process Modeling Library** y arrastrar en orden, conectando
la salida de cada bloque con la entrada del siguiente:

### 3.1 Source (arribos)
- Arrastrar **Source**. Nombre: `source`.
- Propiedades:
  - *Arrivals defined by*: **Rate**
  - *Arrival rate*: `lambda_` (unidad: `per minute`)
  - (Esto genera arribos Poisson con tasa lambda = tiempos entre arribos
    exponenciales, exactamente como en Python.)

### 3.2 Queue (cola)
- Arrastrar **Queue**. Nombre: `queue`.
- Propiedades:
  - *Capacity*: marcar segun el caso:
    - **Cola infinita (M/M/1):** tildar **Maximum capacity** (capacidad
      ilimitada). En esta version `K` se ignora.
    - **Cola finita (M/M/1/K):** destildar *Maximum capacity* y poner
      *Capacity* = `K`. Cuando la cola esta llena el cliente debe ser
      rechazado (ver paso 3.5).

### 3.3 Service (servidor)
- Arrastrar **Service**. Nombre: `service`.
- Propiedades:
  - *Seize*: `(default)` — toma 1 unidad de recurso.
  - *Delay time*: `exponential(mu)` — **tiempo de servicio exponencial** de
    media `1/mu`. (En AnyLogic `exponential(x)` tiene tasa `x`, asi que la
    media es `1/mu`, justo lo que queremos.)
  - *Capacity (resource)*: AnyLogic crea un ResourcePool asociado; dejarlo en
    **1** servidor (es lo que hace M/M/**1**).

### 3.4 Sink (salida)
- Arrastrar **Sink**. Nombre: `sink`. Sin configuracion especial.

### 3.5 Manejo de la denegacion (solo cola finita M/M/1/K)
Para medir la **probabilidad de denegacion de servicio** cuando la cola es
finita hay dos formas; usar la mas simple:

- **Opcion A (recomendada, como en "With Truncation"):** poner un
  **SelectOutput** *antes* de la Queue. Condicion:
  `queue.size() < K` -> sale por la rama "true" hacia la Queue;
  si no, sale por la rama "false" hacia un **Sink** aparte llamado
  `sinkRechazados`. Asi cada cliente que llega con la cola llena se cuenta como
  rechazado.
- **Opcion B:** usar la propiedad de la Queue *On enter (blocked)* / rebound,
  pero es mas engorrosa. Quedarse con la Opcion A.

Diagrama resultante para cola finita:

```
source --> selectOutput --[true: queue.size()<K]--> queue --> service --> sink
                         \--[false]----------------> sinkRechazados
```

Para cola infinita simplemente: `source --> queue --> service --> sink`
(sin SelectOutput).

---

## 4. Medidas de rendimiento (las que pide el TP)

AnyLogic ya calcula casi todo internamente. Agregar estos elementos para
leer/graficar cada medida.

### 4.1 Utilizacion del servidor (rho)
- El bloque **Service** (o su ResourcePool) expone la utilizacion. Agregar un
  **Time Plot** o un *Statistics* y graficar:
  `service.resourcePool.utilization()` -> da rho observado.
- Valor teorico esperado: `rho = lambda_ / mu`.

### 4.2 Clientes en sistema (L) y en cola (Lq)
- AnyLogic tiene estadisticas de ocupacion. Las mas directas:
  - **Lq** (en cola): `queue.statsSize.mean()` -> promedio temporal del
    tamano de la cola.
  - **L** (en sistema): `queue.statsSize.mean() + service.statsSize.mean()`
    (cola + los que estan en servicio). Alternativamente sumar el contenido
    del Service.
- Mostrarlas en cajas de texto que se actualizan (ver paso 5).

### 4.3 Tiempo en sistema (W) y en cola (Wq)
- En el **Sink**, AnyLogic puede medir el tiempo total del agente en el
  sistema si se activa el time-in-system. La forma mas robusta para el TP:
  - Crear dos **statistics** (objeto *Statistics*) en `Main`: `statW` y
    `statWq`.
  - En el agente que circula (o en el Source: *Agent type*), guardar el
    instante de creacion: en *On enter* del Source -> `agent.tArrival = time();`
    (definir antes una variable `double tArrival` en el tipo de agente).
  - En el *On enter* del Service -> `statWq.add( time() - agent.tArrival );`
    (tiempo esperado en cola).
  - En el *On enter* del Sink -> `statW.add( time() - agent.tArrival );`
    (tiempo total en sistema).
- Leer `statW.mean()` y `statWq.mean()`.

### 4.4 Probabilidad de encontrar n clientes en cola (Pn)
- Crear un **Histogram Data** o un *array* que acumule el tiempo que la cola
  pasa en cada tamano `n`. Lo mas simple en AnyLogic:
  - Graficar la distribucion del tamano de la cola con un **Histogram**
    alimentado por `queue.size()` muestreado por un *Event* ciclico
    (cada, por ej., 0.01 min). Eso aproxima `P(n en cola)`.
- Para comparar con la teoria: `Pn = (1 - rho) * rho^n` (cola infinita).

### 4.5 Probabilidad de denegacion de servicio
- Definir dos variables enteras en `Main`: `nLlegan` y `nRechazados`.
- En *On enter* del `source` (o del SelectOutput) -> `nLlegan++;`
- En *On enter* del `sinkRechazados` -> `nRechazados++;`
- Probabilidad de denegacion = `nRechazados / (double) nLlegan`.
- Valor teorico (cola finita): `P_bloqueo = P_K = rho^K * (1-rho)/(1-rho^(K+1))`.

---

## 5. Mostrar resultados en pantalla (para la clase)

Agregar en `Main` varios **Text** dinamicos (propiedad *Text* con una
expresion Java, marcando que se actualice en runtime). Por ejemplo:

```
L  (sistema) = " + (queue.statsSize.mean() + service.statsSize.mean())
Lq (cola)    = " + queue.statsSize.mean()
W            = " + statW.mean()
Wq           = " + statWq.mean()
rho (util.)  = " + service.resourcePool.utilization()
P deneg.     = " + (nLlegan>0 ? nRechazados/(double)nLlegan : 0)
```

Asi, al variar `lambda_` / `K` antes de correr, se ve en vivo como cambian las
medidas: cubre el requisito de "facilitar el ingreso de parametros para mostrar
en clase".

---

## 6. Correr 1 replica (warm-up + medicion)

1. Click en **Run** (el modelo `Main`).
2. Importante para que los numeros sean comparables con Python y la teoria:
   dejar correr un **periodo de calentamiento (warm-up)** antes de empezar a
   medir, porque las formulas teoricas son de **estado estacionario**. Config:
   - En las propiedades del experimento *Simulation*, *Model time* ->
     **Stop time** = por ej. `5000` min.
   - Para el warm-up: usar el campo *Warm up time* si esta disponible, o
     resetear las `statistics` con un *Event* a, por ejemplo, `time() == 500`.
3. Anotar L, Lq, W, Wq, rho y P deneg. al final de la corrida.

---

## 7. Correr 10+ replicas (lo que exige el TP)

El TP pide **minimo 10 corridas por experimento** y promedios con variabilidad.
En AnyLogic eso es un **Monte Carlo / Multiple Run experiment**:

1. Click derecho en el modelo (en el *Projects* tree) -> **New > Experiment**.
2. Tipo: **Monte Carlo** (o *Parameter Variation* con *Replications*).
3. Configurar:
   - *Number of replications*: `10` (o mas).
   - Asegurar que cada replica use **semilla aleatoria distinta**: en la
     pestana *Randomness* elegir **Random seed (unique simulation runs)**.
   - Como salida, recolectar el valor final de cada medida (L, Lq, W, Wq, rho,
     P deneg.) en *Histograms* o *DataSet*; AnyLogic te da media y desvio entre
     replicas -> de ahi sale el intervalo de confianza para comparar con
     Python.
4. Run. Exportar/anotar **media +/- desvio** de cada medida.

---

## 8. Barrido de los 5 niveles de carga (rho)

El TP pide variar la tasa de arribo a **25%, 50%, 75%, 100%, 125%** de mu.
Dos formas:

- **Manual:** correr el Monte Carlo 5 veces, cambiando `lambda_` a 0.25, 0.5,
  0.75, 1.0, 1.25 (con `mu=1`). Anotar resultados en una tabla.
- **Automatica (mejor):** usar un experimento **Parameter Variation**:
  - Variar `lambda_` en el rango `[0.25 .. 1.25]` paso `0.25`.
  - Con *Replications per iteration* = 10.
  - Recolectar L, Lq, W, Wq por cada valor de `lambda_`.

> **Ojo con rho >= 1 (casos 100% y 125%):** teoricamente la cola **infinita**
> es **inestable** (L -> infinito, nunca alcanza estado estacionario). En
> AnyLogic vas a ver la cola crecer sin parar. Eso esta **bien** y hay que
> documentarlo: para esos dos casos el contraste valido es con **cola finita**
> M/M/1/K, no con la formula infinita. Es exactamente lo que hace el programa
> de Python.

---

## 9. Barrido de tamanos de cola finita (denegacion)

El TP pide la probabilidad de denegacion para colas finitas de tamano
**0, 2, 5, 10, 50**:

1. Activar el diseno con SelectOutput (paso 3.5) y la Queue finita (paso 3.2).
2. Correr (Monte Carlo, 10 replicas) variando `K` en {0, 2, 5, 10, 50}.
   - Tip: usar **Parameter Variation** sobre `K` con esos valores discretos.
3. Para cada `K` anotar `P deneg.` simulada y compararla con la teorica
   `P_K = rho^K (1-rho)/(1-rho^(K+1))`.

> `K = 0` significa que **no hay sala de espera**: si el servidor esta ocupado,
> todo arribo se rechaza. Es el caso extremo (sistema de perdida puro, tipo
> Erlang Loss).

---

## 10. Exportar para el informe

Para la tabla comparativa de las **tres fuentes** (teorico / Python / AnyLogic)
del informe LaTeX:

- Anotar en una tabla, por cada `rho`: L, Lq, W, Wq, rho_obs de AnyLogic
  (media +/- desvio de las 10 replicas).
- Para denegacion: una tabla `K` x `rho` con P deneg. de AnyLogic.
- Si AnyLogic deja exportar a Excel/CSV (boton *Export* en los DataSet),
  guardarlo en `mm1/output/anylogic/` para versionarlo.

Esos numeros se cargan despues en las columnas `% TODO AnyLogic` que quedaron
marcadas en `informe/informe.tex`.

---

## Checklist final (que tiene que quedar)

- [ ] Modelo `MM1.alp` con Source -> Queue -> Service -> Sink.
- [ ] Variante con SelectOutput + sinkRechazados para cola finita.
- [ ] Parametros `lambda_`, `mu`, `K` editables.
- [ ] Textos en pantalla con L, Lq, W, Wq, rho, P deneg.
- [ ] Experimento Monte Carlo con 10+ replicas y semilla unica por corrida.
- [ ] Barrido de `lambda_` en {0.25, 0.5, 0.75, 1.0, 1.25}.
- [ ] Barrido de `K` en {0, 2, 5, 10, 50} para denegacion.
- [ ] Resultados anotados/exportados para la tabla de 3 fuentes del informe.

## Equivalencias rapidas Python <-> AnyLogic

| Concepto | Python (`programa.py`) | AnyLogic |
|---|---|---|
| Arribos Poisson | `-ln(U)/lambda` (LCG) | Source, *Arrival rate* = `lambda_` |
| Servicio exponencial | `-ln(U)/mu` (LCG) | Service, *Delay* = `exponential(mu)` |
| Cola finita K | rechazo si `len(cola)==K` | SelectOutput `queue.size()<K` |
| rho observado | `busy_time/total_time` | `service.resourcePool.utilization()` |
| 10 corridas | `-r 10` (semillas distintas) | Monte Carlo, 10 replicas, seed unico |
| Variar carga | `--rhos 0.25,...,1.25` | Parameter Variation sobre `lambda_` |
