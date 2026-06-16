"""Agregacion estadistica de multiples corridas de la simulacion.

Una unica corrida de un sistema estocastico es solo una realizacion: su
resultado puede estar lejos del valor esperado por puro azar. Para estimar
los costos esperados con su incertidumbre se ejecutan varias REPLICAS
independientes (semillas distintas) y se resumen con:

    * Media muestral.
    * Desvio estandar muestral (denominador n - 1, estimador insesgado).
    * Intervalo de confianza del 95 %.

Sobre el intervalo de confianza: con n >= 10 replicas y para mantener el
calculo "a mano" sin tabla t de Student, se usa la aproximacion normal con
z = 1.96 (cuantil 0.975 de la normal estandar). El IC es

    media +/- z * (desvio / sqrt(n)).

Es la convencion adoptada en el TP; para n grande la t y la normal coinciden.
No se usa numpy ni scipy: medias, varianzas y raices se calculan con math.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .simulacion import InventorySimulation, RunResult

# Cuantil 0.975 de la normal estandar, usado para el IC del 95 %.
Z_95 = 1.96


@dataclass
class Statistic:
    """Resumen estadistico de una medida sobre las replicas.

    Atributos:
        mean      -> media muestral.
        std       -> desvio estandar muestral (n - 1).
        half_width-> semiancho del IC 95 % (z * std / sqrt(n)).
        ci_low    -> extremo inferior del IC 95 %.
        ci_high   -> extremo superior del IC 95 %.
        n         -> numero de replicas.
    """

    mean: float
    std: float
    half_width: float
    ci_low: float
    ci_high: float
    n: int


@dataclass
class ExperimentSummary:
    """Resumen de un experimento (varias replicas de una politica (s, S)).

    Agrupa el resumen estadistico de cada uno de los cuatro costos junto con
    la identificacion de la politica y la lista cruda de RunResult por si se
    quiere graficar una corrida representativa.
    """

    s: int
    big_s: int
    n_runs: int
    ordering: Statistic
    holding: Statistic
    shortage: Statistic
    total: Statistic
    runs: list[RunResult]


def _mean(values: list[float]) -> float:
    """Media aritmetica de una lista no vacia."""
    return sum(values) / len(values)


def _sample_std(values: list[float], mean: float) -> float:
    """Desvio estandar muestral con denominador n - 1.

    Con una sola observacion el desvio no esta definido: se devuelve 0.0.
    """
    n = len(values)
    if n < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(variance)


def summarize(values: list[float]) -> Statistic:
    """Construye el Statistic (media, desvio, IC 95 %) de una lista."""
    if not values:
        raise ValueError("se necesita al menos una observacion")
    n = len(values)
    mean = _mean(values)
    std = _sample_std(values, mean)
    half_width = Z_95 * std / math.sqrt(n) if n > 0 else 0.0
    return Statistic(
        mean=mean,
        std=std,
        half_width=half_width,
        ci_low=mean - half_width,
        ci_high=mean + half_width,
        n=n,
    )


def run_experiment(
    sim: InventorySimulation,
    n_runs: int = 10,
    base_seed: int = 12345,
) -> ExperimentSummary:
    """Ejecuta n_runs replicas de 'sim' y devuelve el ExperimentSummary.

    Cada replica usa una semilla distinta derivada de 'base_seed' para que
    los flujos de numeros aleatorios sean independientes entre corridas.
    """
    if n_runs < 1:
        raise ValueError("n_runs debe ser >= 1")

    runs: list[RunResult] = []
    for k in range(n_runs):
        # Semillas separadas para independencia entre replicas. El salto
        # grande evita solapamiento temprano de las secuencias del LCG.
        seed = base_seed + k * 7919
        runs.append(sim.run(seed=seed))

    ordering = summarize([r.ordering_cost for r in runs])
    holding = summarize([r.holding_cost for r in runs])
    shortage = summarize([r.shortage_cost for r in runs])
    total = summarize([r.total_cost for r in runs])

    return ExperimentSummary(
        s=sim.s,
        big_s=sim.big_s,
        n_runs=n_runs,
        ordering=ordering,
        holding=holding,
        shortage=shortage,
        total=total,
        runs=runs,
    )


def compare_policies(
    summaries: list[ExperimentSummary],
) -> list[ExperimentSummary]:
    """Ordena las politicas por costo total medio (de menor a mayor).

    La primera de la lista resultante es la politica recomendada (menor costo
    total esperado).
    """
    return sorted(summaries, key=lambda s: s.total.mean)


def best_policy(summaries: list[ExperimentSummary]) -> ExperimentSummary:
    """Devuelve la politica de menor costo total medio."""
    if not summaries:
        raise ValueError("no hay politicas para comparar")
    return min(summaries, key=lambda s: s.total.mean)
