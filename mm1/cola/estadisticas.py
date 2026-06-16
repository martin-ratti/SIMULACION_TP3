"""Agregacion estadistica de multiples replicas de simulacion.

Una unica corrida de simulacion entrega un estimador puntual con varianza
desconocida. Para cuantificar la incertidumbre se ejecutan N replicas
independientes (cada una con su propia semilla) y se construye un
INTERVALO DE CONFIANZA al 95% sobre la media de cada medida.

Metodo (replicas independientes, Law cap. 9):
    - Cada replica i produce un valor X_i de la medida.
    - Media muestral:  X_barra = (1/N) * sum(X_i).
    - Varianza muestral (con correccion de Bessel, divide por N - 1):
          S^2 = (1/(N-1)) * sum((X_i - X_barra)^2).
    - Intervalo de confianza al 95%:
          X_barra +/- t_{N-1, 0.975} * S / sqrt(N).

El valor critico t de Student se toma de una tabla embebida para grados
de libertad chicos. Para N >= 30 se aproxima por el valor normal z = 1.96,
documentado explicitamente. No se usan numpy ni scipy: medias, varianzas e
intervalos se calculan a mano con la libreria math estandar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .simulacion import RunResult, simulate
from .teorico import TheoreticalMetrics, theoretical_metrics

# Valores criticos de la t de Student para nivel de confianza del 95%
# (cola de 0.975), indexados por grados de libertad (N - 1). Para gl >= 30
# se usa la aproximacion normal z = 1.96.
_T_TABLE_95: dict[int, float] = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045,
}
_Z_95 = 1.96  # aproximacion normal para muestras grandes (gl >= 30)


def _t_critical(degrees_freedom: int) -> float:
    """Valor critico t de Student al 95% para los grados de libertad dados."""
    if degrees_freedom <= 0:
        return _Z_95
    if degrees_freedom >= 30:
        return _Z_95
    return _T_TABLE_95.get(degrees_freedom, _Z_95)


@dataclass
class MeasureStat:
    """Estadistica agregada de UNA medida sobre las N replicas.

    Incluye media, desvio muestral, intervalo de confianza al 95% y la
    comparacion contra el valor teorico (diferencia absoluta y error
    relativo porcentual). Si el teorico es infinito o None, la comparacion
    queda como None y se marca con `theoretical_available = False`.
    """

    name: str
    mean: float
    std: float
    ci_lower: float
    ci_upper: float
    theoretical: float | None
    theoretical_available: bool
    abs_error: float | None
    rel_error_pct: float | None


def _mean(values: list[float]) -> float:
    """Media aritmetica de una lista de valores."""
    return sum(values) / len(values)


def _sample_std(values: list[float], mean_value: float) -> float:
    """Desvio estandar muestral (correccion de Bessel, divide por N - 1)."""
    n = len(values)
    if n < 2:
        return 0.0
    var = sum((x - mean_value) ** 2 for x in values) / (n - 1)
    return math.sqrt(var)


def _build_measure_stat(
    name: str,
    values: list[float],
    theoretical: float | None,
) -> MeasureStat:
    """Construye la estadistica de una medida a partir de sus N replicas."""
    n = len(values)
    mean_value = _mean(values)
    std = _sample_std(values, mean_value)
    t_crit = _t_critical(n - 1)
    half_width = t_crit * std / math.sqrt(n) if n > 0 else 0.0
    ci_lower = mean_value - half_width
    ci_upper = mean_value + half_width

    # La comparacion solo aplica si el teorico es un numero finito.
    available = theoretical is not None and math.isfinite(theoretical)
    if available:
        abs_error = abs(mean_value - theoretical)
        rel_error_pct = (abs_error / abs(theoretical) * 100.0) if theoretical != 0 else 0.0
    else:
        abs_error = None
        rel_error_pct = None

    return MeasureStat(
        name=name,
        mean=mean_value,
        std=std,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        theoretical=theoretical if available else None,
        theoretical_available=available,
        abs_error=abs_error,
        rel_error_pct=rel_error_pct,
    )


@dataclass
class ExperimentSummary:
    """Resumen de un experimento completo (N replicas de una configuracion).

    Agrupa la estadistica de cada medida y conserva una corrida
    representativa (la primera) para graficar la evolucion temporal.
    """

    lam: float
    mu: float
    rho: float
    capacity: int | None
    n_replicas: int
    sim_time: float
    stable: bool                      # estabilidad teorica (cola infinita)
    measures: dict = field(default_factory=dict)  # {nombre: MeasureStat}
    theoretical: TheoreticalMetrics | None = None
    sample_run: RunResult | None = None  # corrida representativa para plots


def run_experiment(
    lam: float,
    mu: float,
    capacity: int | None = None,
    n_replicas: int = 10,
    sim_time: float = 5000.0,
    base_seed: int = 12345,
) -> ExperimentSummary:
    """Ejecuta N replicas de una configuracion y agrega sus resultados.

    Cada replica usa una semilla distinta derivada de base_seed para
    garantizar independencia. Devuelve un ExperimentSummary con la media,
    el desvio y el intervalo de confianza al 95% de cada medida, mas la
    comparacion contra el valor teorico correspondiente.
    """
    if n_replicas < 1:
        raise ValueError("se requiere al menos una replica")

    runs: list[RunResult] = []
    for i in range(n_replicas):
        # Semillas separadas y deterministas, una por replica.
        seed = base_seed + i * 7919  # 7919 es primo: dispersa los estados
        result = simulate(
            lam=lam,
            mu=mu,
            capacity=capacity,
            max_time=sim_time,
            seed=seed,
        )
        runs.append(result)

    theo = theoretical_metrics(lam, mu, capacity)

    # Recolectar los valores de cada medida a lo largo de las replicas.
    collected: dict[str, list[float]] = {
        "L": [r.L for r in runs],
        "Lq": [r.Lq for r in runs],
        "W": [r.W for r in runs],
        "Wq": [r.Wq for r in runs],
        "rho_obs": [r.rho_obs for r in runs],
        "p_denegacion": [r.p_denegacion for r in runs],
    }

    # Mapeo de cada medida a su valor teorico de referencia.
    theo_map: dict[str, float | None] = {
        "L": theo.L,
        "Lq": theo.Lq,
        "W": theo.W,
        "Wq": theo.Wq,
        "rho_obs": theo.rho,
        "p_denegacion": theo.p_blocking,
    }

    measures = {
        name: _build_measure_stat(name, values, theo_map[name])
        for name, values in collected.items()
    }

    return ExperimentSummary(
        lam=lam,
        mu=mu,
        rho=theo.rho,
        capacity=capacity,
        n_replicas=n_replicas,
        sim_time=sim_time,
        stable=theo.stable,
        measures=measures,
        theoretical=theo,
        sample_run=runs[0],
    )


def average_pn(runs: list[RunResult], n_max: int) -> dict[int, float]:
    """Promedia la distribucion pn (fraccion de tiempo) sobre varias corridas.

    Util para comparar el histograma simulado contra la formula teorica.
    """
    if not runs:
        return {}
    acc: dict[int, float] = {n: 0.0 for n in range(n_max + 1)}
    for run in runs:
        for n in range(n_max + 1):
            acc[n] += run.pn.get(n, 0.0)
    return {n: acc[n] / len(runs) for n in range(n_max + 1)}
