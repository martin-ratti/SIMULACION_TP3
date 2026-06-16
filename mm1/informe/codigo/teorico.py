"""Formulas analiticas de las colas M/M/1 y M/M/1/K.

Este modulo concentra las medidas de rendimiento de las colas markovianas
de un solo servidor. Sirve como "fuente de verdad" contra la cual se
contrasta la simulacion de eventos discretos.

Convencion de notacion:
    - lam : tasa media de arribos (lambda).
    - mu  : tasa media de servicio.
    - rho : factor de utilizacion = lam / mu (intensidad de trafico).
    - L   : numero medio de clientes en el sistema.
    - Lq  : numero medio de clientes en la cola.
    - W   : tiempo medio en el sistema (espera + servicio).
    - Wq  : tiempo medio de espera en la cola.
    - pn  : probabilidad de encontrar n clientes en el sistema.

Caso M/M/1 (cola infinita): las formulas solo son validas si rho < 1.
Si rho >= 1 el sistema es INESTABLE: la cola crece sin limite y las
medidas L, Lq, W, Wq divergen a infinito. En ese caso se devuelve
float('inf') y se documenta la inestabilidad.

Caso M/M/1/K (cola finita): el sistema admite a lo sumo K clientes
(en cola + en servicio). Cuando llegan K clientes el arribo se rechaza
(denegacion de servicio / bloqueo). Estas formulas son SIEMPRE validas,
incluso con rho >= 1, porque la capacidad finita acota el sistema.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def rho(lam: float, mu: float) -> float:
    """Factor de utilizacion rho = lam / mu (intensidad de trafico)."""
    if mu <= 0.0:
        raise ValueError("la tasa de servicio mu debe ser positiva")
    return lam / mu


@dataclass
class TheoreticalMetrics:
    """Contenedor de las medidas teoricas de una cola markoviana.

    Para la cola infinita inestable (rho >= 1) las medidas L, Lq, W y Wq
    valen float('inf') y el atributo `stable` es False.
    """

    lam: float
    mu: float
    rho: float
    capacity: int | None  # None = cola infinita (M/M/1)
    stable: bool
    L: float
    Lq: float
    W: float
    Wq: float
    p_blocking: float  # prob. de bloqueo (denegacion); 0 en cola infinita estable
    pn: dict = field(default_factory=dict)  # {n: probabilidad}


def mm1_pn(n: int, rho_value: float) -> float:
    """Probabilidad de n clientes en M/M/1 infinita: (1 - rho) * rho**n.

    Solo tiene sentido con rho < 1 (sistema estable).
    """
    if rho_value >= 1.0:
        raise ValueError("M/M/1 infinita requiere rho < 1 para tener distribucion estacionaria")
    return (1.0 - rho_value) * (rho_value ** n)


def mm1_infinite(lam: float, mu: float, n_max_pn: int = 30) -> TheoreticalMetrics:
    """Medidas teoricas de la cola M/M/1 con capacidad infinita.

    Si rho >= 1 el sistema es inestable y las medidas divergen: se
    devuelven con valor infinito y stable=False. La distribucion pn se
    deja vacia porque no existe estacionario.
    """
    r = rho(lam, mu)
    if r >= 1.0:
        # Sistema inestable: la cola crece sin cota, no hay estacionario.
        return TheoreticalMetrics(
            lam=lam,
            mu=mu,
            rho=r,
            capacity=None,
            stable=False,
            L=float("inf"),
            Lq=float("inf"),
            W=float("inf"),
            Wq=float("inf"),
            p_blocking=0.0,
            pn={},
        )

    L = r / (1.0 - r)
    Lq = (r ** 2) / (1.0 - r)
    W = 1.0 / (mu - lam)
    Wq = r / (mu - lam)
    pn = {n: mm1_pn(n, r) for n in range(n_max_pn + 1)}
    return TheoreticalMetrics(
        lam=lam,
        mu=mu,
        rho=r,
        capacity=None,
        stable=True,
        L=L,
        Lq=Lq,
        W=W,
        Wq=Wq,
        p_blocking=0.0,
        pn=pn,
    )


def mm1k_pn(n: int, rho_value: float, capacity: int) -> float:
    """Probabilidad de n clientes en M/M/1/K finita.

    pn = rho**n * (1 - rho) / (1 - rho**(K + 1))    si rho != 1
    pn = 1 / (K + 1)                                si rho == 1

    Valida para 0 <= n <= K. Siempre existe (capacidad finita).
    """
    if n < 0 or n > capacity:
        return 0.0
    if abs(rho_value - 1.0) < 1e-12:
        return 1.0 / (capacity + 1)
    numerator = (rho_value ** n) * (1.0 - rho_value)
    denominator = 1.0 - (rho_value ** (capacity + 1))
    return numerator / denominator


def mm1k_finite(lam: float, mu: float, capacity: int) -> TheoreticalMetrics:
    """Medidas teoricas de la cola M/M/1/K con capacidad finita K.

    Siempre es estable (la capacidad acota el sistema), incluso con
    rho >= 1. La probabilidad de bloqueo es pn(K): un cliente que llega
    y encuentra K clientes es rechazado.

    L y Lq se calculan por sumatoria directa sobre n = 0..K, evitando
    formulas cerradas para mantener el codigo robusto ante rho == 1.

    Las medidas temporales usan la tasa de arribos EFECTIVA:
        lam_eff = lam * (1 - p_blocking)
    porque solo los clientes admitidos atraviesan el sistema (Little).
    """
    if capacity < 0:
        raise ValueError("la capacidad K debe ser >= 0")
    r = rho(lam, mu)

    pn = {n: mm1k_pn(n, r, capacity) for n in range(capacity + 1)}

    # Numero medio en el sistema: L = sum(n * pn).
    L = sum(n * pn[n] for n in range(capacity + 1))

    p_blocking = pn[capacity]
    lam_eff = lam * (1.0 - p_blocking)

    # Numero medio en cola: Lq = L - (clientes en servicio).
    # Clientes en servicio en promedio = lam_eff / mu = utilizacion real.
    util_real = lam_eff / mu
    Lq = L - util_real

    # Little con tasa efectiva (clientes que realmente entran).
    if lam_eff > 0.0:
        W = L / lam_eff
        Wq = Lq / lam_eff
    else:
        W = 0.0
        Wq = 0.0

    return TheoreticalMetrics(
        lam=lam,
        mu=mu,
        rho=r,
        capacity=capacity,
        stable=True,
        L=L,
        Lq=Lq,
        W=W,
        Wq=Wq,
        p_blocking=p_blocking,
        pn=pn,
    )


def theoretical_metrics(lam: float, mu: float, capacity: int | None = None) -> TheoreticalMetrics:
    """Despacha a la formula correcta segun haya o no capacidad finita.

    capacity == None  -> M/M/1 infinita.
    capacity is int   -> M/M/1/K finita.
    """
    if capacity is None:
        return mm1_infinite(lam, mu)
    return mm1k_finite(lam, mu, capacity)
