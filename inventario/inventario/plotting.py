"""Generacion de graficas del estudio de inventario (s, S).

Usa matplotlib con backend "Agg" (sin ventana grafica) para poder guardar
PNG en entornos sin display. Convencion de colores del usuario: "steelblue"
para lo simulado y "crimson" para lo teorico o de referencia.

Cada funcion genera una figura, la guarda en el directorio de salida y
devuelve la ruta del archivo PNG creado.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .estadisticas import ExperimentSummary  # noqa: E402
from .simulacion import RunResult  # noqa: E402

COLOR_SIM = "steelblue"
COLOR_REF = "crimson"


def _save(fig, output_dir: str, filename: str) -> str:
    """Guarda la figura en output_dir/filename y devuelve la ruta.

    Crea el directorio de salida si no existe. Cierra la figura para liberar
    memoria luego de guardarla.
    """
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, filename)
    fig.savefig(target, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return target


def plot_inventory_level(
    run: RunResult,
    output_dir: str,
    filename: str = "inventario_nivel.png",
) -> str:
    """Grafica el nivel de inventario I(t) de una corrida (escalonado).

    El inventario cambia por saltos (demandas, entregas), de modo que la
    curva natural es una funcion escalon (drawstyle "steps-post"). Se marca
    el nivel cero con una linea horizontal para distinguir holding de
    shortage de un vistazo.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(
        run.series.inventory_time,
        run.series.inventory_level,
        drawstyle="steps-post",
        color=COLOR_SIM,
        linewidth=1.2,
        label="Nivel de inventario I(t)",
    )
    ax.axhline(0.0, color=COLOR_REF, linewidth=1.0, linestyle="--", label="Nivel cero")
    ax.set_xlabel("Tiempo de simulacion (meses)")
    ax.set_ylabel("Unidades en inventario")
    ax.set_title(f"Nivel de inventario I(t) - politica (s={run.s}, S={run.big_s})")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    return _save(fig, output_dir, filename)


def plot_cumulative_costs(
    run: RunResult,
    output_dir: str,
    filename: str = "inventario_costos_acumulados.png",
) -> str:
    """Grafica los costos acumulados vs tiempo de simulacion.

    Muestra ordering, holding, shortage y total acumulados (no promediados)
    en funcion del tiempo, ilustrando como se construyen las medidas a lo
    largo del horizonte.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    s = run.series
    ax.plot(s.cost_time, s.total_cum, color=COLOR_SIM, linewidth=1.6, label="Total")
    ax.plot(
        s.cost_time, s.ordering_cum, color="darkorange", linewidth=1.1, label="Ordenar"
    )
    ax.plot(
        s.cost_time, s.holding_cum, color="seagreen", linewidth=1.1, label="Mantenimiento"
    )
    ax.plot(
        s.cost_time, s.shortage_cum, color=COLOR_REF, linewidth=1.1, label="Faltante"
    )
    ax.set_xlabel("Tiempo de simulacion (meses)")
    ax.set_ylabel("Costo acumulado")
    ax.set_title(f"Costos acumulados - politica (s={run.s}, S={run.big_s})")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    return _save(fig, output_dir, filename)


def plot_total_cost_comparison(
    summaries: list[ExperimentSummary],
    output_dir: str,
    filename: str = "inventario_comparacion_total.png",
) -> str:
    """Grafica de barras del costo total medio por politica, con IC 95 %.

    Las barras de error representan el semiancho del intervalo de confianza
    del 95 %, mostrando la precision de cada estimacion.
    """
    labels = [f"({sm.s},{sm.big_s})" for sm in summaries]
    means = [sm.total.mean for sm in summaries]
    errors = [sm.total.half_width for sm in summaries]

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    positions = list(range(len(labels)))
    ax.bar(
        positions,
        means,
        yerr=errors,
        capsize=5,
        color=COLOR_SIM,
        alpha=0.85,
        label="Costo total medio (IC 95%)",
    )
    # Resaltar la mejor politica (menor costo total medio).
    best_index = min(range(len(means)), key=lambda i: means[i])
    ax.bar(
        best_index,
        means[best_index],
        yerr=errors[best_index],
        capsize=5,
        color=COLOR_REF,
        alpha=0.9,
        label="Mejor politica",
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Politica (s, S)")
    ax.set_ylabel("Costo total medio por mes")
    ax.set_title("Comparacion de costo total medio entre politicas (s, S)")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(loc="best")
    return _save(fig, output_dir, filename)


def plot_cost_breakdown(
    summaries: list[ExperimentSummary],
    output_dir: str,
    filename: str = "inventario_desglose_costos.png",
) -> str:
    """Grafica de barras apiladas del desglose de costos por politica.

    Cada barra apila ordering, holding y shortage, permitiendo ver que
    componente domina en cada politica.
    """
    labels = [f"({sm.s},{sm.big_s})" for sm in summaries]
    ordering = [sm.ordering.mean for sm in summaries]
    holding = [sm.holding.mean for sm in summaries]
    shortage = [sm.shortage.mean for sm in summaries]

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    positions = list(range(len(labels)))
    ax.bar(positions, ordering, color="darkorange", label="Ordenar")
    bottom_h = list(ordering)
    ax.bar(positions, holding, bottom=bottom_h, color="seagreen", label="Mantenimiento")
    bottom_s = [o + h for o, h in zip(ordering, holding)]
    ax.bar(positions, shortage, bottom=bottom_s, color=COLOR_REF, label="Faltante")

    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Politica (s, S)")
    ax.set_ylabel("Costo medio por mes")
    ax.set_title("Desglose de costos por politica (s, S)")
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(loc="best")
    return _save(fig, output_dir, filename)
