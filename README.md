# SIMULACION 2026 - TP 3

Estudio de simulacion de un modelo **M/M/1** (teoria de colas) y un modelo de
**Inventario (s, S)**, catedra de Simulacion, UTN FRRO, 2026.

Para cada modelo se comparan **tres fuentes de datos**: el valor teorico
esperado, un programa construido en Python y una implementacion en AnyLogic.

## Estructura del repositorio

```
SIMULACION_TP3/
  mm1/              # Sistema de colas M/M/1 y M/M/1/K (cola finita)
    cola/           # paquete: rng (GCL), simulacion (eventos discretos),
                    #          teorico (formulas), estadisticas, plotting
    programa.py     # CLI argparse
    output/         # PNGs generados (gitignored)
    informe/        # informe LaTeX
    requirements.txt
    README.md
    ANYLOGIC.md     # guia paso a paso para reproducir el modelo en AnyLogic

  inventario/       # Modelo de inventario (s, S), parametros de Law cap. 1.5
    inventario/     # paquete: rng, simulacion, teorico, estadisticas, plotting
    programa.py     # CLI argparse
    output/         # PNGs generados (gitignored)
    informe/        # informe LaTeX
    requirements.txt
    README.md
    ANYLOGIC.md     # guia paso a paso para reproducir el modelo en AnyLogic
```

Cada modelo es independiente: tiene su propio `programa.py`, paquete,
`requirements.txt`, `output/` e `informe/`.

## MM1 - Sistema de colas M/M/1

Simula un sistema de cola con un servidor (arribos Poisson, servicio
exponencial) por **eventos discretos** y lo contrasta con las formulas
analiticas de estado estacionario. Incluye cola finita M/M/1/K para medir la
**probabilidad de denegacion de servicio**.

Medidas: L, Lq, W, Wq, utilizacion del servidor, Pn (prob. de n en sistema) y
prob. de denegacion. Se varia la carga rho en {0.25, 0.5, 0.75, 1.0, 1.25} y la
capacidad de cola en {0, 2, 5, 10, 50}, con minimo 10 corridas por experimento.

```bash
cd mm1
pip install -r requirements.txt
python programa.py -m 1.0 -r 10 -t 5000
```

Detalles en `mm1/README.md`. Guia AnyLogic en `mm1/ANYLOGIC.md`.

## Inventario - Politica (s, S)

Simula un sistema de inventario de revision periodica mensual con politica
(s, S), demanda aleatoria y lag de entrega, siguiendo el ejemplo de Law
(cap. 1.5). Mide costo de **ordenar**, de **mantenimiento**, de **faltante** y
**total** (por mes), comparando varias politicas con minimo 10 corridas.

```bash
cd inventario
pip install -r requirements.txt
python programa.py -r 10
```

Detalles en `inventario/README.md`. Guia AnyLogic en `inventario/ANYLOGIC.md`.

## Referencias

- Law, A. M. (2014). *Simulation Modeling and Analysis* (5.a ed.), cap. 1-2.
- *The Art of Process-Centric Modeling with AnyLogic*.
- Catedra Simulacion, UTN FRRO, 2026.
