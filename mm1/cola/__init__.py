"""Paquete `cola`: estudio de simulacion de colas M/M/1 y M/M/1/K.

Reune el generador de numeros pseudoaleatorios (GCL del TP 2.1), el motor
de simulacion de eventos discretos, las formulas teoricas de las colas
markovianas, la agregacion estadistica de replicas y las graficas.

Exporta la API publica del paquete para que el programa principal y otros
modulos importen desde `cola` sin conocer la estructura interna.
"""

from __future__ import annotations

from .rng import LCG
from .simulacion import RunResult, simulate
from .teorico import (
    TheoreticalMetrics,
    mm1_infinite,
    mm1_pn,
    mm1k_finite,
    mm1k_pn,
    rho,
    theoretical_metrics,
)
from .estadisticas import (
    ExperimentSummary,
    MeasureStat,
    average_pn,
    run_experiment,
)

__all__ = [
    "LCG",
    "RunResult",
    "simulate",
    "TheoreticalMetrics",
    "mm1_infinite",
    "mm1_pn",
    "mm1k_finite",
    "mm1k_pn",
    "rho",
    "theoretical_metrics",
    "ExperimentSummary",
    "MeasureStat",
    "average_pn",
    "run_experiment",
]
