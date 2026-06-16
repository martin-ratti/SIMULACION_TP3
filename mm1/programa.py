"""Programa principal del estudio de simulacion de colas M/M/1 y M/M/1/K.

Ejecuta el estudio completo del TP de Simulacion:

    1. Para cada factor de utilizacion rho (que fija lambda = rho * mu),
       corre N replicas de la cola M/M/1 de capacidad infinita y compara
       las medidas SIMULADAS (media + intervalo de confianza al 95%) contra
       las TEORICAS. Cuando rho >= 1 la cola infinita es INESTABLE: la
       simulacion igual corre (se estabiliza por el horizonte finito) pero
       NO se compara contra la formula infinita (L -> infinito). Solo tiene
       sentido analizarla con cola finita.

    2. Para cada capacidad de cola finita K y cada rho, corre las replicas
       de la cola M/M/1/K y compara la probabilidad de DENEGACION (bloqueo)
       simulada contra la teorica. Esto es valido incluso con rho >= 1.

    3. Genera las graficas del estudio (salvo que se pase --no-plots).

Uso (CLI):

    python programa.py [opciones]

    -m, --mu MU             Tasa de servicio (default 1.0).
    -r, --corridas N        Replicas por configuracion (default 10).
    -t, --tiempo T          Tiempo de simulacion por corrida (default 5000).
    -s, --semilla S         Semilla base del generador (default 12345).
        --rhos LISTA        Factores de utilizacion, coma-separados
                            (default "0.25,0.5,0.75,1.0,1.25").
        --colas LISTA       Capacidades de cola finita K, coma-separadas
                            (default "0,2,5,10,50").
        --output-dir DIR    Carpeta de salida de graficas (default "output").
        --no-plots          No generar graficas (solo tablas numericas).

Ejemplos:

    python programa.py -r 10 -t 3000 --no-plots
    python programa.py -r 20 -t 5000 --rhos 0.5,0.8 --colas 2,5,10
"""

from __future__ import annotations

import argparse
import os

from cola.estadisticas import ExperimentSummary, run_experiment
from cola.plotting import (
    plot_L_evolution,
    plot_denegacion_vs_K,
    plot_measures_vs_rho,
    plot_pn,
)
from cola.teorico import mm1k_finite


# Etiquetas legibles de cada medida para las tablas.
_MEASURE_LABELS: dict[str, str] = {
    "L": "L  (n. medio en sistema)",
    "Lq": "Lq (n. medio en cola)   ",
    "W": "W  (t. medio en sistema)",
    "Wq": "Wq (t. medio en cola)   ",
    "rho_obs": "rho (utilizacion)       ",
    "p_denegacion": "P. denegacion           ",
}


def _parse_float_list(text: str) -> list[float]:
    """Convierte 'a,b,c' en lista de floats, ignorando espacios vacios."""
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def _parse_int_list(text: str) -> list[int]:
    """Convierte 'a,b,c' en lista de enteros, ignorando espacios vacios."""
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def _fmt(value: float) -> str:
    """Formatea un numero para la tabla; 'inf' si es infinito."""
    if value != value:  # NaN
        return "  nan  "
    if value == float("inf"):
        return "  inf  "
    return f"{value:8.4f}"


def _print_header(title: str) -> None:
    """Imprime un encabezado de seccion."""
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def _print_infinite_table(summary: ExperimentSummary) -> None:
    """Imprime la tabla de medidas simuladas vs teoricas (cola infinita)."""
    print()
    print(f"  rho = {summary.rho:.2f}   (lambda = {summary.lam:.4f}, mu = {summary.mu:.4f})"
          f"   |   {summary.n_replicas} replicas x t = {summary.sim_time:.0f}")
    print("  " + "-" * 74)

    if not summary.stable:
        print("  >> COLA INFINITA INESTABLE (rho >= 1): L, Lq, W, Wq -> INFINITO.")
        print("  >> La simulacion se estabiliza solo por el horizonte finito de tiempo;")
        print("  >> NO se compara contra la formula infinita. Ver analisis con cola finita.")
        print("  " + "-" * 74)

    print(f"  {'Medida':<26}{'Simulado':>10}  {'IC 95%':>20}  {'Teorico':>10}  {'Err%':>7}")
    print("  " + "-" * 74)

    for key in ("L", "Lq", "W", "Wq", "rho_obs"):
        stat = summary.measures[key]
        label = _MEASURE_LABELS[key]
        ci = f"[{stat.ci_lower:7.3f},{stat.ci_upper:7.3f}]"
        if stat.theoretical_available:
            theo = _fmt(stat.theoretical)
            err = f"{stat.rel_error_pct:6.2f}%"
        else:
            theo = "  inf  " if key in ("L", "Lq", "W", "Wq") else "   -   "
            err = "   -   "
        print(f"  {label:<26}{stat.mean:10.4f}  {ci:>20}  {theo:>10}  {err:>7}")


def _print_finite_table(rho_value: float, mu: float, summaries: dict[int, ExperimentSummary]) -> None:
    """Imprime la tabla de denegacion simulada vs teorica (cola finita)."""
    print()
    print(f"  rho = {rho_value:.2f}   (lambda = {rho_value * mu:.4f}, mu = {mu:.4f})")
    print("  " + "-" * 74)
    print(f"  {'K':>4}  {'P.deneg sim.':>14}  {'IC 95%':>22}  {'P.deneg teo.':>14}  {'Err%':>7}")
    print("  " + "-" * 74)

    for k in sorted(summaries.keys()):
        summary = summaries[k]
        stat = summary.measures["p_denegacion"]
        theo = mm1k_finite(rho_value * mu, mu, k).p_blocking
        ci = f"[{stat.ci_lower:8.5f},{stat.ci_upper:8.5f}]"
        if theo != 0:
            err = f"{abs(stat.mean - theo) / abs(theo) * 100.0:6.2f}%"
        else:
            err = "   -   "
        print(f"  {k:>4}  {stat.mean:14.5f}  {ci:>22}  {theo:14.5f}  {err:>7}")


def main() -> None:
    """Punto de entrada: parsea la CLI y corre el estudio completo."""
    parser = argparse.ArgumentParser(
        description="Estudio de simulacion de colas M/M/1 y M/M/1/K (TP Simulacion).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-m", "--mu", type=float, default=1.0,
                        help="Tasa media de servicio mu.")
    parser.add_argument("-r", "--corridas", type=int, default=10,
                        help="Cantidad de replicas por configuracion (minimo 10).")
    parser.add_argument("-t", "--tiempo", type=float, default=5000.0,
                        help="Tiempo de simulacion por corrida.")
    parser.add_argument("-s", "--semilla", type=int, default=12345,
                        help="Semilla base del generador congruencial.")
    parser.add_argument("--rhos", type=str, default="0.25,0.5,0.75,1.0,1.25",
                        help="Factores de utilizacion rho, coma-separados.")
    parser.add_argument("--colas", type=str, default="0,2,5,10,50",
                        help="Capacidades de cola finita K, coma-separadas.")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Carpeta de salida de las graficas.")
    parser.add_argument("--no-plots", action="store_true",
                        help="No generar graficas (solo salida numerica).")
    args = parser.parse_args()

    mu = args.mu
    n_replicas = args.corridas
    sim_time = args.tiempo
    base_seed = args.semilla
    rhos = _parse_float_list(args.rhos)
    capacities = _parse_int_list(args.colas)
    output_dir = args.output_dir
    make_plots = not args.no_plots

    print()
    print("#" * 78)
    print("#  ESTUDIO DE SIMULACION DE COLAS  M/M/1  Y  M/M/1/K")
    print("#  Simulacion de eventos discretos (next-event time-advance)")
    print("#" * 78)
    print(f"  mu = {mu}   |   replicas = {n_replicas}   |   tiempo/corrida = {sim_time}")
    print(f"  semilla base = {base_seed}   |   rhos = {rhos}   |   colas K = {capacities}")

    # ------------------------------------------------------------------
    # PARTE 1: cola M/M/1 infinita, medidas simuladas vs teoricas por rho.
    # ------------------------------------------------------------------
    _print_header("PARTE 1 - COLA M/M/1 INFINITA: medidas simuladas vs teoricas")
    print()
    print("  Para cada rho se fija lambda = rho * mu y se corren las replicas.")
    print("  Recordatorio: la cola infinita SOLO es estable si rho < 1. Con")
    print("  rho >= 1 las medidas teoricas L, Lq, W, Wq divergen a infinito y")
    print("  no se las compara (se analizan con cola finita en la Parte 2).")

    infinite_summaries: list[ExperimentSummary] = []
    for rho_value in rhos:
        lam = rho_value * mu
        summary = run_experiment(
            lam=lam,
            mu=mu,
            capacity=None,
            n_replicas=n_replicas,
            sim_time=sim_time,
            base_seed=base_seed,
        )
        infinite_summaries.append(summary)
        _print_infinite_table(summary)

    # ------------------------------------------------------------------
    # PARTE 2: cola M/M/1/K finita, probabilidad de denegacion por K y rho.
    # ------------------------------------------------------------------
    _print_header("PARTE 2 - COLA M/M/1/K FINITA: probabilidad de denegacion")
    print()
    print("  Con capacidad finita K, un arribo que encuentra K clientes en el")
    print("  sistema es RECHAZADO (denegacion de servicio). Esta cola es")
    print("  SIEMPRE estable, incluso con rho >= 1, porque la capacidad acota.")
    print("  Se compara la prob. de denegacion simulada contra la teorica pn(K).")

    # data para la grafica de denegacion: {rho: [(K, sim, teo), ...]}
    deneg_data: dict[float, list[tuple[int, float, float]]] = {}
    finite_by_rho: dict[float, dict[int, ExperimentSummary]] = {}

    for rho_value in rhos:
        lam = rho_value * mu
        per_k: dict[int, ExperimentSummary] = {}
        deneg_points: list[tuple[int, float, float]] = []
        for k in capacities:
            summary = run_experiment(
                lam=lam,
                mu=mu,
                capacity=k,
                n_replicas=n_replicas,
                sim_time=sim_time,
                base_seed=base_seed,
            )
            per_k[k] = summary
            sim_deneg = summary.measures["p_denegacion"].mean
            theo_deneg = mm1k_finite(lam, mu, k).p_blocking
            deneg_points.append((k, sim_deneg, theo_deneg))
        finite_by_rho[rho_value] = per_k
        deneg_data[rho_value] = deneg_points
        _print_finite_table(rho_value, mu, per_k)

    # ------------------------------------------------------------------
    # PARTE 3: graficas.
    # ------------------------------------------------------------------
    if make_plots:
        _print_header("PARTE 3 - GENERACION DE GRAFICAS")
        os.makedirs(output_dir, exist_ok=True)
        generated: list[str] = []

        # 3.1 Evolucion de L para una corrida representativa (rho estable mas alto).
        stable_summaries = [s for s in infinite_summaries if s.stable]
        ref_summary = (stable_summaries[-1] if stable_summaries else infinite_summaries[0])
        if ref_summary.sample_run is not None:
            path = plot_L_evolution(ref_summary.sample_run, output_dir,
                                    f"L_evolucion_rho_{ref_summary.rho:.2f}.png")
            generated.append(path)

        # 3.2 Distribucion Pn (cola infinita) para los rhos estables.
        for summary in infinite_summaries:
            if summary.sample_run is not None and summary.stable:
                path = plot_pn(summary.sample_run, summary.rho, None, output_dir,
                               f"pn_infinita_rho_{summary.rho:.2f}.png")
                generated.append(path)

        # 3.3 Comparacion de medidas L, Lq, W, Wq vs rho.
        for measure in ("L", "Lq", "W", "Wq"):
            path = plot_measures_vs_rho(infinite_summaries, measure, output_dir)
            generated.append(path)

        # 3.4 Probabilidad de denegacion vs K para cada rho.
        path = plot_denegacion_vs_K(deneg_data, output_dir)
        generated.append(path)

        # 3.5 Distribucion Pn de una cola finita representativa (K medio).
        if capacities:
            k_mid = sorted(capacities)[len(capacities) // 2]
            for rho_value in rhos:
                summary = finite_by_rho[rho_value][k_mid]
                if summary.sample_run is not None:
                    path = plot_pn(summary.sample_run, rho_value, k_mid, output_dir,
                                   f"pn_finita_K{k_mid}_rho_{rho_value:.2f}.png",
                                   n_max=k_mid)
                    generated.append(path)

        print()
        print(f"  Se generaron {len(generated)} graficas en '{os.path.abspath(output_dir)}':")
        for path in generated:
            print(f"    - {os.path.basename(path)}")
    else:
        _print_header("GRAFICAS OMITIDAS (--no-plots)")

    print()
    print("#" * 78)
    print("#  FIN DEL ESTUDIO")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()
