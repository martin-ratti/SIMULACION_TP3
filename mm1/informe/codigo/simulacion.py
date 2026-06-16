"""Motor de simulacion de eventos discretos para colas M/M/1 y M/M/1/K.

Implementa el esquema de avance al proximo evento (next-event time-advance)
descrito en Law, "Simulation Modeling and Analysis", cap. 1.4, para un
sistema de cola de un solo servidor con disciplina FIFO.

Dos variantes:
    - M/M/1 : cola infinita (capacity = None). Todo arribo entra.
    - M/M/1/K : cola finita de capacidad K. Si al llegar un arribo hay ya
      K clientes en el sistema (en cola + en servicio), el cliente es
      RECHAZADO (denegacion de servicio / bloqueo). No vuelve.

Distribuciones:
    - Tiempos entre arribos: exponencial de media 1/lam.
    - Tiempos de servicio:   exponencial de media 1/mu.
    Ambos por transformada inversa sobre uniformes del GCL (clase LCG):
        x = -ln(U) / rate,  con U en (0, 1).

Medidas registradas (estimadores):
    - L  : numero medio de clientes en el sistema (promedio temporal de L(t)).
    - Lq : numero medio en cola (promedio temporal de Q(t)).
    - W  : tiempo medio en el sistema por cliente atendido.
    - Wq : tiempo medio de espera en cola por cliente atendido.
    - rho_obs : utilizacion observada = tiempo ocupado / tiempo total.
    - p_denegacion : rechazados / arribos totales.
    - pn : distribucion del numero de clientes en el sistema, ponderada
      por tiempo (fraccion de tiempo con n clientes presentes).
    - serie temporal : muestreo de L(t) en instantes regulares, para
      graficar la evolucion respecto del tiempo de simulacion.

Los promedios temporales se obtienen integrando por areas: entre dos
eventos consecutivos el numero de clientes es constante, asi que se
acumula num_clientes * delta_t (regla del rectangulo exacta para
funciones escalera).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from .rng import LCG


@dataclass
class RunResult:
    """Resultado de una unica corrida de simulacion.

    Reune los estimadores de las medidas de rendimiento mas la serie
    temporal de L(t) para graficar la evolucion.
    """

    lam: float
    mu: float
    capacity: int | None
    sim_time: float          # horizonte temporal efectivamente simulado
    L: float                 # num. medio en sistema (promedio temporal)
    Lq: float                # num. medio en cola (promedio temporal)
    W: float                 # tiempo medio en sistema (por cliente atendido)
    Wq: float                # tiempo medio en cola (por cliente atendido)
    rho_obs: float           # utilizacion observada del servidor
    p_denegacion: float      # prob. de denegacion = rechazados / arribos
    pn: dict = field(default_factory=dict)        # {n: fraccion de tiempo}
    n_arribos: int = 0       # arribos totales (admitidos + rechazados)
    n_atendidos: int = 0     # clientes que completaron servicio
    n_rechazados: int = 0    # arribos rechazados por cola llena
    time_series: list = field(default_factory=list)  # [(t, L_t), ...]
    series_L: list = field(default_factory=list)      # [(t, L acumulada)]
    series_Lq: list = field(default_factory=list)     # [(t, Lq acumulada)]
    series_rho: list = field(default_factory=list)    # [(t, util. acumulada)]


# Identificadores de los dos tipos de evento del modelo.
_ARRIVAL = 0
_DEPARTURE = 1


def simulate(
    lam: float,
    mu: float,
    capacity: int | None = None,
    max_time: float = 5000.0,
    max_customers: int | None = None,
    seed: int = 12345,
    n_samples: int = 400,
) -> RunResult:
    """Corre una simulacion de eventos discretos de la cola.

    Parametros:
        lam : tasa media de arribos (lambda > 0).
        mu  : tasa media de servicio (mu > 0).
        capacity : capacidad K del sistema. None = cola infinita (M/M/1);
            entero >= 0 = cola finita (M/M/1/K) con rechazo al llenarse.
        max_time : horizonte temporal de simulacion (criterio de parada
            por tiempo). Se ignora si se da max_customers.
        max_customers : si se especifica, la simulacion para al atender
            esa cantidad de clientes (criterio de parada por clientes).
        seed : semilla del generador congruencial (cada replica usa otra).
        n_samples : cantidad de puntos de la serie temporal a registrar.

    Devuelve un RunResult con todas las medidas estimadas.
    """
    if lam <= 0.0:
        raise ValueError("la tasa de arribos lam debe ser positiva")
    if mu <= 0.0:
        raise ValueError("la tasa de servicio mu debe ser positiva")
    if capacity is not None and capacity < 0:
        raise ValueError("la capacidad K debe ser >= 0")

    rng = LCG(seed=seed)

    # --- Estado del sistema -------------------------------------------------
    clock = 0.0                 # reloj de simulacion
    num_in_system = 0           # clientes en el sistema (cola + servicio)
    server_busy = False         # estado del servidor

    # Cola FIFO: guarda el instante de arribo de cada cliente en espera.
    waiting_queue: deque[float] = deque()
    # Instante de arribo del cliente actualmente en servicio.
    in_service_arrival: float = 0.0

    # --- Acumuladores estadisticos -----------------------------------------
    area_L = 0.0                # integral de L(t) dt -> num medio en sistema
    area_Lq = 0.0               # integral de Q(t) dt -> num medio en cola
    busy_time = 0.0             # tiempo total con servidor ocupado
    total_wait_system = 0.0     # suma de tiempos en sistema (atendidos)
    total_wait_queue = 0.0      # suma de tiempos en cola (atendidos)

    n_arribos = 0
    n_atendidos = 0
    n_rechazados = 0

    # Histograma temporal: tiempo acumulado con exactamente n clientes.
    time_in_state: dict[int, float] = {}

    # --- Serie temporal -----------------------------------------------------
    time_series: list[tuple[float, int]] = []
    series_L: list[tuple[float, float]] = []
    series_Lq: list[tuple[float, float]] = []
    series_rho: list[tuple[float, float]] = []
    sample_interval = max_time / n_samples if (max_customers is None and n_samples > 0) else None
    next_sample_time = sample_interval if sample_interval else float("inf")

    def _exp(rate: float) -> float:
        """Muestra exponencial de media 1/rate por transformada inversa."""
        return -math.log(rng.uniform_open()) / rate

    # --- Inicializacion del calendario de eventos --------------------------
    # Primer arribo programado; la primera partida no existe aun (sistema vacio).
    time_next_arrival = clock + _exp(lam)
    time_next_departure = float("inf")

    def _stop() -> bool:
        """Criterio de parada segun el modo elegido."""
        if max_customers is not None:
            return n_atendidos >= max_customers
        return clock >= max_time

    while not _stop():
        # Proximo evento: el de menor tiempo entre arribo y partida.
        next_event_time = min(time_next_arrival, time_next_departure)

        # Si la parada es por tiempo y el proximo evento la supera, cortar
        # avanzando el reloj exactamente hasta max_time (para no sesgar areas).
        if max_customers is None and next_event_time > max_time:
            delta = max_time - clock
            if delta > 0.0:
                area_L += num_in_system * delta
                q_now = num_in_system - (1 if server_busy else 0)
                area_Lq += q_now * delta
                if server_busy:
                    busy_time += delta
                time_in_state[num_in_system] = time_in_state.get(num_in_system, 0.0) + delta
            clock = max_time
            break

        # --- Avance del reloj y acumulacion de areas en [clock, next_event] -
        delta = next_event_time - clock
        area_L += num_in_system * delta
        q_now = num_in_system - (1 if server_busy else 0)
        area_Lq += q_now * delta
        if server_busy:
            busy_time += delta
        time_in_state[num_in_system] = time_in_state.get(num_in_system, 0.0) + delta

        # Muestreo de la serie temporal en instantes regulares previos al evento.
        if sample_interval is not None:
            while next_sample_time <= next_event_time and next_sample_time <= max_time:
                time_series.append((next_sample_time, num_in_system))
                acc_L = area_L / next_sample_time if next_sample_time > 0 else 0.0
                acc_Lq = area_Lq / next_sample_time if next_sample_time > 0 else 0.0
                acc_rho = busy_time / next_sample_time if next_sample_time > 0 else 0.0
                series_L.append((next_sample_time, acc_L))
                series_Lq.append((next_sample_time, acc_Lq))
                series_rho.append((next_sample_time, acc_rho))
                next_sample_time += sample_interval

        clock = next_event_time

        # --- Procesamiento del evento ------------------------------------
        if time_next_arrival <= time_next_departure:
            # EVENTO: ARRIBO
            n_arribos += 1
            # Programar el siguiente arribo.
            time_next_arrival = clock + _exp(lam)

            # Control de capacidad (M/M/1/K): rechazar si el sistema esta lleno.
            if capacity is not None and num_in_system >= capacity:
                n_rechazados += 1
            else:
                num_in_system += 1
                if not server_busy:
                    # Servidor libre: el cliente entra a servicio de inmediato.
                    server_busy = True
                    in_service_arrival = clock
                    time_next_departure = clock + _exp(mu)
                else:
                    # Servidor ocupado: el cliente espera en la cola FIFO.
                    waiting_queue.append(clock)
        else:
            # EVENTO: PARTIDA (fin de servicio del cliente actual)
            n_atendidos += 1
            total_wait_system += clock - in_service_arrival
            num_in_system -= 1

            if waiting_queue:
                # Tomar el siguiente cliente de la cola (FIFO).
                arrival_t = waiting_queue.popleft()
                total_wait_queue += clock - arrival_t  # espera en cola
                in_service_arrival = arrival_t
                time_next_departure = clock + _exp(mu)
            else:
                # Cola vacia: el servidor queda ocioso.
                server_busy = False
                time_next_departure = float("inf")

    total_time = clock if clock > 0.0 else 1e-12

    # --- Calculo de estimadores finales ------------------------------------
    L = area_L / total_time
    Lq = area_Lq / total_time
    rho_obs = busy_time / total_time
    W = total_wait_system / n_atendidos if n_atendidos > 0 else 0.0
    Wq = total_wait_queue / n_atendidos if n_atendidos > 0 else 0.0
    p_denegacion = n_rechazados / n_arribos if n_arribos > 0 else 0.0

    # Distribucion pn ponderada por tiempo (fraccion de tiempo con n clientes).
    pn = {n: t / total_time for n, t in sorted(time_in_state.items())}

    return RunResult(
        lam=lam,
        mu=mu,
        capacity=capacity,
        sim_time=total_time,
        L=L,
        Lq=Lq,
        W=W,
        Wq=Wq,
        rho_obs=rho_obs,
        p_denegacion=p_denegacion,
        pn=pn,
        n_arribos=n_arribos,
        n_atendidos=n_atendidos,
        n_rechazados=n_rechazados,
        time_series=time_series,
        series_L=series_L,
        series_Lq=series_Lq,
        series_rho=series_rho,
    )
