"""Motor de simulacion de eventos discretos para el modelo de inventario (s, S).

Implementa el modelo clasico de Law "Simulation Modeling and Analysis"
capitulo 1.5: un sistema de inventario de un solo producto con politica de
revision periodica (s, S). Cada mes se revisa el nivel de inventario; si esta
por debajo del umbral 's' se ordena hasta llevarlo a 'S'.

Tecnica: simulacion de eventos discretos (next-event time advance). El reloj
de simulacion avanza saltando de evento en evento. Los tres tipos de evento
del modelo son:

    1. arrival_demand  -> llega un cliente y demanda D unidades.
    2. arrival_order   -> llega una orden colocada previamente (entrega).
    3. evaluation      -> fin de mes: se revisa el inventario y, si hace
                          falta, se coloca una orden.

Medidas de salida (todas promedio por mes a lo largo del horizonte):

    * ordering_cost  -> costo de ordenar (setup + incremental).
    * holding_cost   -> costo de mantenimiento del inventario positivo.
    * shortage_cost  -> costo de faltante (backlog), inventario negativo.
    * total_cost     -> suma de los tres.

Se integra el area bajo la curva I(t) separando la parte positiva (holding)
de la negativa (shortage), acumulando entre eventos consecutivos. Asi se
obtiene el promedio temporal del inventario sin depender de la grilla mensual.

Reutiliza el generador congruencial lineal (LCG) validado en el TP 2.1 como
unica fuente de aleatoriedad.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .rng import LCG

# Tipos de evento del modelo de eventos discretos.
EVENT_ORDER_ARRIVAL = "arrival_order"
EVENT_DEMAND = "arrival_demand"
EVENT_EVALUATION = "evaluation"
EVENT_END = "end"


@dataclass
class TimeSeries:
    """Series temporales registradas durante una corrida.

    Sirven para graficar las medidas en relacion al tiempo de simulacion.
    Cada lista esta indexada por el mismo numero de muestras: 'time' marca
    el instante (en meses) y el resto las magnitudes en ese instante.
    """

    # Nivel de inventario I(t): pares (tiempo, nivel) en cada cambio.
    inventory_time: list[float] = field(default_factory=list)
    inventory_level: list[float] = field(default_factory=list)

    # Costos acumulados (no promediados) vs tiempo de simulacion.
    cost_time: list[float] = field(default_factory=list)
    ordering_cum: list[float] = field(default_factory=list)
    holding_cum: list[float] = field(default_factory=list)
    shortage_cum: list[float] = field(default_factory=list)
    total_cum: list[float] = field(default_factory=list)


@dataclass
class RunResult:
    """Resultado de una unica corrida de la simulacion.

    Los cuatro costos estan expresados como promedio por mes sobre el
    horizonte completo, que es la forma en que Law reporta las medidas de
    desempeno del sistema de inventario.
    """

    ordering_cost: float
    holding_cost: float
    shortage_cost: float
    total_cost: float
    series: TimeSeries
    s: int
    big_s: int
    n_months: int


class InventorySimulation:
    """Simulacion de eventos discretos de un sistema de inventario (s, S).

    Parametros configurables (todos con los valores por defecto de Law
    capitulo 1.5):

        s, big_s        -> umbrales de la politica (s, S).
        n_months        -> horizonte de simulacion en meses.
        initial_inventory -> inventario inicial I(0).
        demand_values   -> tamanos posibles de cada demanda de cliente.
        demand_probs    -> probabilidades de cada tamano (deben sumar 1).
        mean_interdemand-> media del tiempo exponencial entre demandas.
        setup_cost      -> K, costo fijo por colocar una orden.
        incremental_cost-> i, costo por unidad ordenada.
        holding_cost    -> h, costo de mantenimiento por unidad y por mes.
        shortage_cost   -> pi, costo de faltante por unidad y por mes.
        delivery_lag    -> par (min, max) del lag uniforme de entrega.
    """

    def __init__(
        self,
        s: int = 20,
        big_s: int = 40,
        n_months: int = 120,
        initial_inventory: int = 60,
        demand_values: tuple[int, ...] = (1, 2, 3, 4),
        demand_probs: tuple[float, ...] = (1 / 6, 1 / 3, 1 / 3, 1 / 6),
        mean_interdemand: float = 0.1,
        setup_cost: float = 32.0,
        incremental_cost: float = 3.0,
        holding_cost: float = 1.0,
        shortage_cost: float = 5.0,
        delivery_lag: tuple[float, float] = (0.5, 1.0),
    ) -> None:
        if s >= big_s:
            raise ValueError("la politica requiere s < S")
        if len(demand_values) != len(demand_probs):
            raise ValueError("demand_values y demand_probs deben tener igual longitud")
        if abs(sum(demand_probs) - 1.0) > 1e-9:
            raise ValueError("demand_probs debe sumar 1")
        if delivery_lag[0] > delivery_lag[1]:
            raise ValueError("delivery_lag mal definido (min > max)")

        self.s = s
        self.big_s = big_s
        self.n_months = n_months
        self.initial_inventory = initial_inventory
        self.demand_values = demand_values
        self.demand_probs = demand_probs
        # Probabilidades acumuladas para la transformada inversa discreta.
        self._demand_cdf = self._build_cdf(demand_probs)
        self.mean_interdemand = mean_interdemand
        self.setup_cost = setup_cost
        self.incremental_cost = incremental_cost
        self.holding_cost = holding_cost
        self.shortage_cost = shortage_cost
        self.delivery_lag = delivery_lag

    @staticmethod
    def _build_cdf(probs: tuple[float, ...]) -> list[float]:
        """Construye la funcion de distribucion acumulada (CDF) discreta."""
        cdf: list[float] = []
        acc = 0.0
        for p in probs:
            acc += p
            cdf.append(acc)
        # Forzar el ultimo a 1.0 para evitar problemas de redondeo.
        cdf[-1] = 1.0
        return cdf

    def _sample_exponential(self, rng: LCG, mean: float) -> float:
        """Tiempo exponencial de media 'mean' por transformada inversa."""
        return -mean * math.log(rng.uniform_open())

    def _sample_demand(self, rng: LCG) -> int:
        """Tamano de demanda discreto por transformada inversa empirica."""
        u = rng.uniform()
        for value, threshold in zip(self.demand_values, self._demand_cdf):
            if u < threshold:
                return value
        return self.demand_values[-1]

    def _sample_lag(self, rng: LCG) -> float:
        """Lag de entrega uniforme en [delivery_lag[0], delivery_lag[1]]."""
        low, high = self.delivery_lag
        return low + (high - low) * rng.uniform()

    def run(self, seed: int = 12345) -> RunResult:
        """Ejecuta una corrida completa y devuelve el RunResult.

        La integracion del area bajo I(t) se hace por tramos: cada vez que
        el reloj salta de 'sim_time' al instante del proximo evento, se
        acumula el aporte del nivel de inventario constante en ese tramo,
        separando holding (I > 0) de shortage (I < 0).
        """
        rng = LCG(seed=seed)

        # Estado del sistema.
        inventory = float(self.initial_inventory)
        sim_time = 0.0

        # Acumuladores de area (integral de I(t)).
        area_holding = 0.0   # integral de la parte positiva de I(t)
        area_shortage = 0.0  # integral del valor absoluto de la parte negativa
        ordering_total = 0.0  # costo de ordenar acumulado (setup + incremental)

        # Reloj de los eventos. La entrega pendiente se modela con un unico
        # tiempo de arribo: cuando no hay orden en transito vale infinito.
        time_next_demand = sim_time + self._sample_exponential(rng, self.mean_interdemand)
        time_next_evaluation = 0.0   # primera evaluacion al inicio del mes 1
        time_next_order_arrival = math.inf
        amount_pending_order = 0      # unidades de la orden en transito

        series = TimeSeries()
        # Registro inicial de las series.
        series.inventory_time.append(sim_time)
        series.inventory_level.append(inventory)
        self._record_costs(series, sim_time, ordering_total, area_holding, area_shortage)

        end_time = float(self.n_months)

        while True:
            # Determinar el proximo evento (minimo de los relojes).
            time_next_event, event_type = self._next_event(
                time_next_demand,
                time_next_evaluation,
                time_next_order_arrival,
                end_time,
            )

            # Integrar el area bajo I(t) en el tramo [sim_time, time_next_event].
            delta = time_next_event - sim_time
            if delta > 0.0:
                if inventory > 0.0:
                    area_holding += inventory * delta
                elif inventory < 0.0:
                    area_shortage += (-inventory) * delta
            sim_time = time_next_event

            if event_type == EVENT_END:
                # Cierre del horizonte: registrar el ultimo punto y salir.
                series.inventory_time.append(sim_time)
                series.inventory_level.append(inventory)
                self._record_costs(series, sim_time, ordering_total, area_holding, area_shortage)
                break

            if event_type == EVENT_DEMAND:
                # Llega un cliente: descuenta su demanda del inventario.
                demand = self._sample_demand(rng)
                inventory -= demand
                time_next_demand = sim_time + self._sample_exponential(
                    rng, self.mean_interdemand
                )
                series.inventory_time.append(sim_time)
                series.inventory_level.append(inventory)

            elif event_type == EVENT_ORDER_ARRIVAL:
                # Llega la orden en transito: suma las unidades pedidas.
                inventory += amount_pending_order
                amount_pending_order = 0
                time_next_order_arrival = math.inf
                series.inventory_time.append(sim_time)
                series.inventory_level.append(inventory)

            elif event_type == EVENT_EVALUATION:
                # Fin de mes: revisar el inventario y ordenar si I < s.
                if inventory < self.s:
                    amount = self.big_s - int(inventory)
                    amount_pending_order = amount
                    ordering_total += self.setup_cost + self.incremental_cost * amount
                    lag = self._sample_lag(rng)
                    time_next_order_arrival = sim_time + lag
                    self._record_costs(
                        series, sim_time, ordering_total, area_holding, area_shortage
                    )
                # Programar la proxima evaluacion (proximo mes).
                time_next_evaluation = sim_time + 1.0

        # Promedios por mes sobre el horizonte completo.
        holding_total = self.holding_cost * area_holding
        shortage_total = self.shortage_cost * area_shortage
        ordering_cost = ordering_total / self.n_months
        holding_cost = holding_total / self.n_months
        shortage_cost = shortage_total / self.n_months
        total_cost = ordering_cost + holding_cost + shortage_cost

        return RunResult(
            ordering_cost=ordering_cost,
            holding_cost=holding_cost,
            shortage_cost=shortage_cost,
            total_cost=total_cost,
            series=series,
            s=self.s,
            big_s=self.big_s,
            n_months=self.n_months,
        )

    @staticmethod
    def _next_event(
        time_demand: float,
        time_evaluation: float,
        time_order: float,
        time_end: float,
    ) -> tuple[float, str]:
        """Devuelve (instante, tipo) del proximo evento mas cercano.

        Si el horizonte termina antes que cualquier evento programado, se
        devuelve el evento de fin (EVENT_END).
        """
        candidates = [
            (time_order, EVENT_ORDER_ARRIVAL),
            (time_demand, EVENT_DEMAND),
            (time_evaluation, EVENT_EVALUATION),
        ]
        time_next, event_type = min(candidates, key=lambda c: c[0])
        if time_end < time_next:
            return time_end, EVENT_END
        return time_next, event_type

    def _record_costs(
        self,
        series: TimeSeries,
        sim_time: float,
        ordering_total: float,
        area_holding: float,
        area_shortage: float,
    ) -> None:
        """Registra el estado acumulado de costos en las series temporales."""
        holding_cum = self.holding_cost * area_holding
        shortage_cum = self.shortage_cost * area_shortage
        total_cum = ordering_total + holding_cum + shortage_cum
        series.cost_time.append(sim_time)
        series.ordering_cum.append(ordering_total)
        series.holding_cum.append(holding_cum)
        series.shortage_cum.append(shortage_cum)
        series.total_cum.append(total_cum)
