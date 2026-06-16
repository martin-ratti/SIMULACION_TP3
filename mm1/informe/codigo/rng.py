"""Fuente de numeros pseudoaleatorios uniformes para el TP 2.2.

Reutiliza el Generador Congruencial Lineal (GCL) validado en el TP 2.1
--- el mismo que supero las pruebas de uniformidad, Kolmogorov-Smirnov,
rachas y poker --- como fuente de valores U(0, 1) para construir todas las
demas distribuciones de probabilidad.

La eleccion del GCL responde al espiritu del enunciado: "ahora que tenemos
un generador testeado, es hora de empezar a utilizarlo". Todos los metodos
de generacion (transformacion inversa, rechazo, convolucion) parten de uno
o varios uniformes producidos por esta clase.
"""

from __future__ import annotations


class LCG:
    """Generador Congruencial Lineal (GCL), configuracion MINSTD revisada.

    Recurrencia:

        X_{n+1} = (a * X_n + c) mod m

    con a = 48271, c = 0, m = 2**31 - 1 (Park & Miller, 1993). El uniforme
    en [0, 1) se obtiene como X_{n+1} / m. Es el generador que en el TP 2.1
    paso 4 de 5 pruebas estadisticas.
    """

    def __init__(
        self,
        seed: int = 12345,
        a: int = 48271,
        c: int = 0,
        m: int = 2 ** 31 - 1,
    ) -> None:
        if m <= 0:
            raise ValueError("el modulo m debe ser positivo")
        self.a = a
        self.c = c
        self.m = m
        self._state = seed % m
        if self._state == 0 and c == 0:
            self._state = 1

    def next_int(self) -> int:
        """Siguiente entero crudo del estado del GCL."""
        self._state = (self.a * self._state + self.c) % self.m
        return self._state

    def uniform(self) -> float:
        """Siguiente valor uniforme en [0, 1)."""
        return self.next_int() / self.m

    def uniform_open(self) -> float:
        """Uniforme en (0, 1), evitando el 0 exacto.

        Util para metodos que aplican logaritmo (exponencial, normal por
        Box-Muller, etc.), donde log(0) no esta definido.
        """
        u = self.uniform()
        while u <= 0.0:
            u = self.uniform()
        return u

    def uniform_sample(self, n: int) -> list:
        """Lista de n uniformes en [0, 1)."""
        if n <= 0:
            raise ValueError("n debe ser un entero positivo")
        return [self.uniform() for _ in range(n)]
