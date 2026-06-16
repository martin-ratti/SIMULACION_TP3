"""Generacion de graficas del estudio de colas M/M/1 y M/M/1/K.

Usa matplotlib con backend "Agg" (sin ventana grafica) para guardar las
figuras directamente como PNG, lo que permite correr el estudio en
servidores o pipelines sin entorno de escritorio.

Convencion de colores del TP:
    - "steelblue" : datos provenientes de la SIMULACION.
    - "crimson"   : valores TEORICOS (formulas analiticas).

Cada funcion genera una figura, la guarda en output_dir y devuelve el path
absoluto del archivo creado.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .estadisticas import ExperimentSummary  # noqa: E402
from .simulacion import RunResult  # noqa: E402
from .teorico import mm1k_pn, mm1_pn  # noqa: E402


def _save(fig, output_dir: str, filename: str) -> str:
    """Guarda la figura como PNG y devuelve el path. Cierra la figura."""
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, filename)
    fig.savefig(target, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return target


def plot_L_evolution(run: RunResult, output_dir: str, filename: str = "L_evolucion.png") -> str:
    """Evolucion del numero de clientes en el sistema vs tiempo de simulacion.

    Dibuja dos curvas: L(t) instantaneo (escalera) y el promedio temporal
    acumulado, que deberia converger al L estacionario.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    if run.time_series:
        ts = [t for t, _ in run.time_series]
        ls = [v for _, v in run.time_series]
        ax.plot(ts, ls, color="steelblue", alpha=0.45, linewidth=0.8,
                label="L(t) instantaneo")

    if run.series_L:
        ts_acc = [t for t, _ in run.series_L]
        ls_acc = [v for _, v in run.series_L]
        ax.plot(ts_acc, ls_acc, color="crimson", linewidth=1.8,
                label="L promedio acumulado")

    cap_txt = "infinita" if run.capacity is None else f"K={run.capacity}"
    ax.set_title(f"Evolucion de clientes en el sistema (rho={run.lam / run.mu:.2f}, cola {cap_txt})")
    ax.set_xlabel("Tiempo de simulacion")
    ax.set_ylabel("Clientes en el sistema L(t)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    return _save(fig, output_dir, filename)


def plot_pn(
    run: RunResult,
    rho_value: float,
    capacity: int | None,
    output_dir: str,
    filename: str = "pn.png",
    n_max: int = 12,
) -> str:
    """Distribucion Pn: barras simuladas (steelblue) vs teoricas (crimson)."""
    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    ns = list(range(n_max + 1))
    sim = [run.pn.get(n, 0.0) for n in ns]

    if capacity is None:
        # Cola infinita: solo tiene pn teorico si es estable (rho < 1).
        if rho_value < 1.0:
            theo = [mm1_pn(n, rho_value) for n in ns]
        else:
            theo = [0.0 for _ in ns]
    else:
        theo = [mm1k_pn(n, rho_value, capacity) for n in ns]

    width = 0.4
    ax.bar([n - width / 2 for n in ns], sim, width=width,
           color="steelblue", label="Simulado", alpha=0.85)
    ax.bar([n + width / 2 for n in ns], theo, width=width,
           color="crimson", label="Teorico", alpha=0.85)

    cap_txt = "infinita" if capacity is None else f"K={capacity}"
    ax.set_title(f"Distribucion Pn (rho={rho_value:.2f}, cola {cap_txt})")
    ax.set_xlabel("Numero de clientes en el sistema (n)")
    ax.set_ylabel("Probabilidad Pn")
    ax.set_xticks(ns)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    return _save(fig, output_dir, filename)


def plot_measures_vs_rho(
    summaries: list[ExperimentSummary],
    measure: str,
    output_dir: str,
    filename: str | None = None,
) -> str:
    """Compara una medida (L, Lq, W, Wq) simulada vs teorica a traves de rho.

    Solo grafica el punto teorico cuando existe (cola infinita estable,
    rho < 1). Los puntos simulados se dibujan siempre. Las barras de error
    muestran el intervalo de confianza al 95%.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    summaries = sorted(summaries, key=lambda s: s.rho)
    rhos = [s.rho for s in summaries]

    sim_means = [s.measures[measure].mean for s in summaries]
    sim_err = [
        (s.measures[measure].mean - s.measures[measure].ci_lower)
        for s in summaries
    ]
    ax.errorbar(rhos, sim_means, yerr=sim_err, fmt="o-", color="steelblue",
                capsize=4, label="Simulado (media + IC 95%)")

    # Puntos teoricos disponibles (descartando inf en rho >= 1).
    theo_rhos = [s.rho for s in summaries if s.measures[measure].theoretical_available]
    theo_vals = [
        s.measures[measure].theoretical
        for s in summaries
        if s.measures[measure].theoretical_available
    ]
    if theo_rhos:
        ax.plot(theo_rhos, theo_vals, "s--", color="crimson",
                label="Teorico (M/M/1, rho<1)")

    ax.set_title(f"Medida {measure} vs factor de utilizacion rho")
    ax.set_xlabel("Factor de utilizacion rho")
    ax.set_ylabel(measure)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")

    if filename is None:
        filename = f"medida_{measure}_vs_rho.png"
    return _save(fig, output_dir, filename)


def plot_denegacion_vs_K(
    data: dict[float, list[tuple[int, float, float]]],
    output_dir: str,
    filename: str = "denegacion_vs_K.png",
) -> str:
    """Probabilidad de denegacion vs tamano de cola K, una curva por rho.

    data: {rho: [(K, p_deneg_simulada, p_deneg_teorica), ...]}.
    Dibuja la simulada con marcadores y la teorica con linea punteada del
    mismo color, para comparar visualmente por cada rho.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.5))

    colors = ["steelblue", "darkorange", "seagreen", "crimson", "purple", "saddlebrown"]
    for idx, rho_value in enumerate(sorted(data.keys())):
        points = sorted(data[rho_value], key=lambda p: p[0])
        ks = [p[0] for p in points]
        sim = [p[1] for p in points]
        theo = [p[2] for p in points]
        color = colors[idx % len(colors)]
        ax.plot(ks, sim, "o-", color=color, label=f"rho={rho_value:.2f} (sim.)")
        ax.plot(ks, theo, "x--", color=color, alpha=0.6, label=f"rho={rho_value:.2f} (teo.)")

    ax.set_title("Probabilidad de denegacion vs tamano de cola K")
    ax.set_xlabel("Capacidad de la cola K")
    ax.set_ylabel("Probabilidad de denegacion")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    return _save(fig, output_dir, filename)
