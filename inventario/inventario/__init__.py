"""Paquete de simulacion del modelo de inventario (s, S) de Law cap. 1.5.

Expone la API publica del estudio: el generador de numeros aleatorios
reutilizado del TP 2.1, el motor de simulacion de eventos discretos, los
valores de referencia teoricos aproximados, la agregacion estadistica de
multiples corridas y las funciones de graficado.
"""

from __future__ import annotations

from .rng import LCG
from .simulacion import (
    InventorySimulation,
    RunResult,
    TimeSeries,
)
from .teorico import (
    TheoreticalReference,
    mean_demand_per_month,
    mean_demand_size,
    theoretical_reference,
)
from .estadisticas import (
    ExperimentSummary,
    Statistic,
    best_policy,
    compare_policies,
    run_experiment,
    summarize,
)
from .plotting import (
    plot_cost_breakdown,
    plot_cumulative_costs,
    plot_inventory_level,
    plot_total_cost_comparison,
)

__all__ = [
    "LCG",
    "InventorySimulation",
    "RunResult",
    "TimeSeries",
    "TheoreticalReference",
    "mean_demand_per_month",
    "mean_demand_size",
    "theoretical_reference",
    "ExperimentSummary",
    "Statistic",
    "best_policy",
    "compare_policies",
    "run_experiment",
    "summarize",
    "plot_cost_breakdown",
    "plot_cumulative_costs",
    "plot_inventory_level",
    "plot_total_cost_comparison",
]
