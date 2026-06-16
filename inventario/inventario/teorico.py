"""Valores de referencia analiticos (aproximados) del modelo de inventario.

A diferencia de modelos de colas como M/M/1 --- donde existen formulas
cerradas exactas para L, Lq, W, Wq --- el modelo de inventario (s, S) con
backlog NO tiene una expresion analitica simple para los costos esperados.
La razon es que el nivel de inventario I(t) es un proceso estocastico cuya
distribucion estacionaria depende de la interaccion entre la demanda
compuesta, el lag de entrega aleatorio y la politica (s, S); no se reduce a
una formula elemental.

Por eso este modulo entrega APROXIMACIONES ANALITICAS, utiles como sanity
check del orden de magnitud, pero NO como verdad de referencia. La fuente
confiable del valor esperado es la propia simulacion ejecutada con muchas
corridas (ver estadisticas.py). El contraste de las tres fuentes
--- teorico aproximado / Python / AnyLogic --- se hace de todos modos, dejando
explicito que la columna teorica es orientativa.

Aproximaciones implementadas:

    * Demanda media mensual:
        E[D_mes] = (tasa de demandas por mes) * (tamano medio de demanda)
                 = (1 / mean_interdemand) * sum(value_k * prob_k)

    * Frecuencia esperada de ordenes:
        Entre dos ordenes se consume, en promedio, una cantidad cercana a
        (S - s) unidades antes de cruzar el umbral. Asi, el numero esperado
        de ordenes por mes se aproxima por:
            f_orden ~ E[D_mes] / (S - s)
        Es una aproximacion gruesa: ignora el overshoot por debajo de s y el
        efecto del lag, pero captura la tendencia (a mayor brecha S - s,
        menos ordenes y mas grandes).

    * Costo de ordenar esperado por mes:
        E[ordering] ~ f_orden * (K + i * Q_media)
      con Q_media ~ (S - s) + E[overshoot]; aqui se toma Q_media ~ (S - s)
      mas medio tamano medio de demanda como correccion del overshoot.

    * Holding y shortage:
        E[holding] = h * E[I^+]   y   E[shortage] = pi * E[I^-]
      donde I^+ e I^- son las partes positiva y negativa del inventario en
      regimen estacionario. No se calculan en forma cerrada: se documentan
      las formulas y se deja su estimacion a la simulacion.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TheoreticalReference:
    """Valores de referencia analiticos aproximados del modelo (s, S).

    Atributos:
        mean_demand_per_month -> demanda media mensual (exacta).
        mean_demand_size      -> tamano medio de una demanda (exacto).
        demand_rate_per_month -> tasa de demandas por mes (exacta).
        expected_order_freq   -> ordenes esperadas por mes (aproximado).
        expected_order_size   -> tamano medio de orden aproximado.
        approx_ordering_cost  -> costo de ordenar mensual aproximado.
        note                  -> recordatorio de que es una aproximacion.
    """

    mean_demand_per_month: float
    mean_demand_size: float
    demand_rate_per_month: float
    expected_order_freq: float
    expected_order_size: float
    approx_ordering_cost: float
    note: str


def mean_demand_size(
    demand_values: tuple[int, ...] = (1, 2, 3, 4),
    demand_probs: tuple[float, ...] = (1 / 6, 1 / 3, 1 / 3, 1 / 6),
) -> float:
    """Tamano medio de una demanda: sum(value_k * prob_k). Valor exacto."""
    return sum(v * p for v, p in zip(demand_values, demand_probs))


def mean_demand_per_month(
    mean_interdemand: float = 0.1,
    demand_values: tuple[int, ...] = (1, 2, 3, 4),
    demand_probs: tuple[float, ...] = (1 / 6, 1 / 3, 1 / 3, 1 / 6),
) -> float:
    """Demanda media por mes: tasa de demandas * tamano medio. Valor exacto.

    Con mean_interdemand = 0.1 mes hay 1 / 0.1 = 10 demandas/mes, y el tamano
    medio es 2.5, de modo que E[D_mes] = 10 * 2.5 = 25 unidades/mes (es el
    valor del ejemplo de Law).
    """
    rate = 1.0 / mean_interdemand
    return rate * mean_demand_size(demand_values, demand_probs)


def theoretical_reference(
    s: int,
    big_s: int,
    mean_interdemand: float = 0.1,
    setup_cost: float = 32.0,
    incremental_cost: float = 3.0,
    demand_values: tuple[int, ...] = (1, 2, 3, 4),
    demand_probs: tuple[float, ...] = (1 / 6, 1 / 3, 1 / 3, 1 / 6),
) -> TheoreticalReference:
    """Calcula los valores de referencia analiticos aproximados.

    ATENCION: salvo la demanda media (exacta), el resto son aproximaciones
    gruesas pensadas solo para validar ordenes de magnitud. El valor de
    referencia confiable proviene de la simulacion con muchas corridas.
    """
    size = mean_demand_size(demand_values, demand_probs)
    rate = 1.0 / mean_interdemand
    demand_month = rate * size

    gap = float(big_s - s)
    # Frecuencia de ordenes aproximada: cuantos "ciclos" de (S - s) unidades
    # se consumen por mes.
    order_freq = demand_month / gap if gap > 0 else 0.0
    # Tamano de orden aproximado: la brecha mas medio tamano medio como
    # correccion del overshoot por debajo de s.
    order_size = gap + size / 2.0
    approx_ordering = order_freq * (setup_cost + incremental_cost * order_size)

    note = (
        "Aproximacion analitica orientativa: el modelo (s, S) con backlog no "
        "tiene formula cerrada. La referencia confiable es la simulacion."
    )
    return TheoreticalReference(
        mean_demand_per_month=demand_month,
        mean_demand_size=size,
        demand_rate_per_month=rate,
        expected_order_freq=order_freq,
        expected_order_size=order_size,
        approx_ordering_cost=approx_ordering,
        note=note,
    )
