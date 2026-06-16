"""Programa principal del estudio de simulacion del inventario (s, S).

Modelo de referencia: Law, "Simulation Modeling and Analysis", capitulo 1.5.
Simula un sistema de inventario de un producto con politica de revision
periodica (s, S), compara varias politicas por su costo total medio mensual
y rankea cual conviene. Contrasta el resultado simulado con un valor de
referencia analitico aproximado y, opcionalmente, genera las graficas.

Uso (CLI):

    # Corrida basica (10 replicas, sin graficas):
    python programa.py -r 10 --no-plots

    # Estudio completo con graficas en ./output:
    python programa.py -r 10

    # Otras politicas y mas replicas:
    python programa.py -r 30 --politicas "20,40;20,60;40,60;40,80;50,100"

    # Cambiar costos e inventario inicial:
    python programa.py -I 60 -K 32 -i 3 -H 1 -p 5 --meses 120

Opciones principales:

    -I/--inicial          inventario inicial I(0)           (default 60)
    --meses               horizonte en meses                (default 120)
    -r/--corridas         numero de replicas por politica   (default 10)
    -s/--semilla          semilla base del generador        (default 12345)
    --politicas           pares "s,S" separados por ';'     (default 4 pares)
    -K/--setup            costo fijo de ordenar K           (default 32)
    -i/--incremental      costo por unidad ordenada i       (default 3)
    -H/--holding          costo de mantenimiento h          (default 1)
    -p/--shortage         costo de faltante pi              (default 5)
    --mean-interdemand    media exponencial entre demandas  (default 0.1)
    --output-dir          carpeta de salida de graficas     (default output)
    --no-plots            no generar graficas
"""

from __future__ import annotations

import argparse

from inventario import (
    InventorySimulation,
    best_policy,
    compare_policies,
    plot_cost_breakdown,
    plot_cumulative_costs,
    plot_inventory_level,
    plot_total_cost_comparison,
    run_experiment,
    theoretical_reference,
)
from inventario.estadisticas import ExperimentSummary, Statistic

DEFAULT_POLICIES = "20,40;20,60;40,60;40,80"


def parse_policies(text: str) -> list[tuple[int, int]]:
    """Parsea la cadena de politicas "s1,S1;s2,S2;..." a pares (s, S).

    Valida que cada par tenga dos enteros con s < S.
    """
    policies: list[tuple[int, int]] = []
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split(",")
        if len(parts) != 2:
            raise ValueError(f"politica mal formada: '{chunk}' (se espera 's,S')")
        s_val = int(parts[0])
        big_s_val = int(parts[1])
        if s_val >= big_s_val:
            raise ValueError(f"politica invalida ({s_val},{big_s_val}): requiere s < S")
        policies.append((s_val, big_s_val))
    if not policies:
        raise ValueError("no se especifico ninguna politica valida")
    return policies


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos de la linea de comandos."""
    parser = argparse.ArgumentParser(
        description=(
            "Simulacion de un sistema de inventario con politica (s, S) "
            "(modelo de Law cap. 1.5). Compara politicas por costo total medio."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-I", "--inicial", type=int, default=60,
        help="inventario inicial I(0)",
    )
    parser.add_argument(
        "--meses", type=int, default=120,
        help="horizonte de simulacion en meses",
    )
    parser.add_argument(
        "-r", "--corridas", type=int, default=10,
        help="numero de replicas (corridas) por politica",
    )
    parser.add_argument(
        "-s", "--semilla", type=int, default=12345,
        help="semilla base del generador congruencial",
    )
    parser.add_argument(
        "--politicas", type=str, default=DEFAULT_POLICIES,
        help="pares 's,S' separados por ';' (ej: '20,40;20,60')",
    )
    parser.add_argument(
        "-K", "--setup", type=float, default=32.0,
        help="costo fijo por colocar una orden (setup K)",
    )
    parser.add_argument(
        "-i", "--incremental", type=float, default=3.0,
        help="costo incremental por unidad ordenada (i)",
    )
    parser.add_argument(
        "-H", "--holding", type=float, default=1.0,
        help="costo de mantenimiento por unidad y por mes (h)",
    )
    parser.add_argument(
        "-p", "--shortage", type=float, default=5.0,
        help="costo de faltante por unidad y por mes (pi)",
    )
    parser.add_argument(
        "--mean-interdemand", type=float, default=0.1,
        help="media del tiempo exponencial entre demandas (meses)",
    )
    parser.add_argument(
        "--output-dir", type=str, default="output",
        help="directorio donde guardar las graficas",
    )
    parser.add_argument(
        "--no-plots", action="store_true",
        help="no generar graficas (solo salida numerica)",
    )
    return parser


def _fmt_stat(stat: Statistic) -> str:
    """Formatea 'media +/- semiancho' de un Statistic con 2 decimales."""
    return f"{stat.mean:8.2f} +/- {stat.half_width:6.2f}"


def print_reference(args: argparse.Namespace) -> None:
    """Imprime los valores de referencia analiticos aproximados."""
    ref = theoretical_reference(
        s=0, big_s=1,  # placeholder; demanda media no depende de la politica
        mean_interdemand=args.mean_interdemand,
        setup_cost=args.setup,
        incremental_cost=args.incremental,
    )
    print("=" * 78)
    print("VALORES DE REFERENCIA ANALITICOS (APROXIMADOS)")
    print("=" * 78)
    print(f"  Tasa de demandas por mes      : {ref.demand_rate_per_month:8.3f}")
    print(f"  Tamano medio de demanda       : {ref.mean_demand_size:8.3f}")
    print(f"  Demanda media por mes         : {ref.mean_demand_per_month:8.3f} unidades")
    print()
    print("  NOTA: el modelo (s, S) con backlog no tiene formula cerrada exacta.")
    print("  Estos valores son una aproximacion analitica orientativa; la")
    print("  referencia confiable es la simulacion con muchas corridas.")
    print()


def print_policy_table(summaries: list[ExperimentSummary], args: argparse.Namespace) -> None:
    """Imprime la tabla de costos (media +/- IC 95 %) por politica."""
    print("=" * 78)
    print(f"RESULTADOS DE SIMULACION ({args.corridas} replicas, {args.meses} meses)")
    print("=" * 78)
    header = (
        f"{'Politica':>10} | {'Ordenar':>17} | {'Mantenim.':>17} | "
        f"{'Faltante':>17} | {'TOTAL':>17}"
    )
    print(header)
    print("-" * len(header))
    for sm in summaries:
        label = f"({sm.s},{sm.big_s})"
        print(
            f"{label:>10} | {_fmt_stat(sm.ordering):>17} | "
            f"{_fmt_stat(sm.holding):>17} | {_fmt_stat(sm.shortage):>17} | "
            f"{_fmt_stat(sm.total):>17}"
        )
    print("-" * len(header))
    print("  Valores en costo promedio por mes. '+/-' es el semiancho del IC 95%.")
    print()


def print_ranking(ranked: list[ExperimentSummary]) -> None:
    """Imprime el ranking de politicas por costo total medio."""
    print("=" * 78)
    print("RANKING POR COSTO TOTAL MEDIO (menor es mejor)")
    print("=" * 78)
    for position, sm in enumerate(ranked, start=1):
        mark = "  <== MEJOR" if position == 1 else ""
        print(
            f"  {position}. politica (s={sm.s:>3}, S={sm.big_s:>3}) -> "
            f"total = {sm.total.mean:8.2f} +/- {sm.total.half_width:6.2f}{mark}"
        )
    print()
    best = ranked[0]
    print(
        f"  La politica recomendada es (s={best.s}, S={best.big_s}) con un costo "
        f"total medio\n  de {best.total.mean:.2f} por mes "
        f"(IC 95%: [{best.total.ci_low:.2f}, {best.total.ci_high:.2f}])."
    )
    print()


def generate_plots(
    summaries: list[ExperimentSummary],
    output_dir: str,
) -> None:
    """Genera todas las graficas del estudio e informa las rutas."""
    print("=" * 78)
    print("GENERACION DE GRAFICAS")
    print("=" * 78)

    # Para las series temporales se usa la primera corrida de la primera
    # politica como corrida representativa.
    representative = summaries[0].runs[0]
    paths = [
        plot_inventory_level(representative, output_dir),
        plot_cumulative_costs(representative, output_dir),
        plot_total_cost_comparison(summaries, output_dir),
        plot_cost_breakdown(summaries, output_dir),
    ]
    for path in paths:
        print(f"  guardada: {path}")
    print()


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del programa."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        policies = parse_policies(args.politicas)
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # parser.error sale, pero por claridad de tipos

    print()
    print("#" * 78)
    print("# SIMULACION DE INVENTARIO CON POLITICA (s, S) - MODELO DE LAW CAP. 1.5")
    print("#" * 78)
    print(
        f"  Inventario inicial : {args.inicial} unidades\n"
        f"  Horizonte          : {args.meses} meses\n"
        f"  Replicas           : {args.corridas}\n"
        f"  Costos             : K={args.setup}, i={args.incremental}, "
        f"h={args.holding}, pi={args.shortage}\n"
        f"  Media entre demandas: {args.mean_interdemand} mes (Exponencial)\n"
    )

    print_reference(args)

    # Ejecutar el experimento para cada politica.
    summaries: list[ExperimentSummary] = []
    for s_val, big_s_val in policies:
        sim = InventorySimulation(
            s=s_val,
            big_s=big_s_val,
            n_months=args.meses,
            initial_inventory=args.inicial,
            mean_interdemand=args.mean_interdemand,
            setup_cost=args.setup,
            incremental_cost=args.incremental,
            holding_cost=args.holding,
            shortage_cost=args.shortage,
        )
        summary = run_experiment(sim, n_runs=args.corridas, base_seed=args.semilla)
        summaries.append(summary)

    print_policy_table(summaries, args)

    ranked = compare_policies(summaries)
    print_ranking(ranked)

    if not args.no_plots:
        generate_plots(summaries, args.output_dir)
    else:
        print("  (graficas omitidas por --no-plots)\n")

    best = best_policy(summaries)
    print("#" * 78)
    print(
        f"# CONCLUSION: la mejor politica es (s={best.s}, S={best.big_s}) "
        f"con costo total {best.total.mean:.2f}/mes"
    )
    print("#" * 78)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
