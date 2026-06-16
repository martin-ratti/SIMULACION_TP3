# Explicacion sencilla: el modelo M/M/1

Una explicacion en criollo de que hace este modelo, para entenderlo rapido o
para explicarlo en clase. Sin formulas pesadas (esas estan en el `README.md` y
en el informe).

## La idea en una frase

Imaginate **una sola caja de un supermercado**: la gente llega, hace fila,
la cajera atiende de a uno, y cuando termina se va. Eso es M/M/1.

## Las 3 letras (M / M / 1)

El nombre "M/M/1" se lee asi:

- **Primera M** = como llega la gente. "M" significa que los clientes llegan
  de forma **aleatoria** (a veces juntos, a veces pasa rato sin nadie), con un
  ritmo promedio que llamamos **lambda** (λ). Ej: lambda = 0,5 -> llega en
  promedio medio cliente por minuto (uno cada 2 minutos).
- **Segunda M** = cuanto tarda la atencion. Tambien **aleatoria**: a algunos
  los atienden rapido, a otros les lleva mas. El ritmo promedio de atencion se
  llama **mu** (μ). Ej: mu = 1 -> la cajera atiende en promedio 1 cliente por
  minuto.
- **El 1** = hay **un solo servidor** (una sola caja, un solo cajero).

## El numero mas importante: rho (ρ)

`rho = lambda / mu` = que tan ocupada esta la caja.

Es la relacion entre **que tan rapido llega la gente** y **que tan rapido se la
atiende**. Se mide de 0 a 1 (o en %):

- **rho = 0,25 (25%)** -> llega poca gente, la caja casi siempre libre. Casi no
  hay fila.
- **rho = 0,75 (75%)** -> llega bastante, se empieza a notar la fila.
- **rho = 1 (100%)** -> llega exactamente al ritmo que se atiende. PROBLEMA: la
  fila empieza a crecer y **no para nunca**. El sistema "se satura".
- **rho > 1 (125%)** -> llega MAS gente de la que se puede atender. La fila se
  hace infinita. Es como si a la caja llegara mas gente de la que puede pasar:
  un desastre.

> Por eso en el TP probamos los 5 niveles: 25, 50, 75, 100 y 125%. Los dos
> ultimos muestran que pasa cuando el sistema colapsa.

## Que cosas medimos (las "medidas de rendimiento")

Son las preguntas que le hacemos al sistema:

| Medida | Pregunta que responde |
|---|---|
| **L** | En promedio, cuanta gente hay en total (en fila + siendo atendida)? |
| **Lq** | En promedio, cuanta gente hay solo en la fila esperando? |
| **W** | Cuanto tiempo pasa un cliente en total (esperar + que lo atiendan)? |
| **Wq** | Cuanto tiempo pasa un cliente solo esperando en la fila? |
| **Utilizacion (rho)** | Que porcentaje del tiempo la caja esta ocupada? |
| **Pn** | Que tan probable es encontrar exactamente n personas en el sistema? |
| **Prob. de denegacion** | Si la fila tiene lugar limitado, que chance hay de que llegue alguien y NO entre? |

## La cola finita (M/M/1/K): cuando la fila tiene tope

En la vida real las filas no son infinitas: un local tiene lugar para, digamos,
10 personas y listo. Eso es **M/M/1/K**, donde **K es el tope**.

Cuando la fila esta llena y llega alguien nuevo, **se lo rechaza** (se va sin
ser atendido). A eso le decimos **denegacion de servicio**.

En el TP probamos topes de **0, 2, 5, 10 y 50**:

- **K = 0** -> no hay sala de espera. Si la caja esta ocupada, el que llega se
  va. (rechazo altisimo)
- **K = 50** -> hay mucho lugar, casi nunca se rechaza a nadie.

Lo interesante: con tope, **el sistema nunca explota**, ni siquiera con
rho > 1, porque la fila no puede pasar de K. El precio es que rechazas gente.

## Como lo simulamos (sin entrar en detalle)

El programa hace lo que se llama **"simulacion por eventos"**: en vez de mirar
el reloj segundo a segundo, salta directo de un suceso al siguiente. Los unicos
dos sucesos que importan son:

1. **Llega un cliente.**
2. **Se va un cliente** (termino su atencion).

El programa va saltando entre estos eventos, anotando cuanta gente hay, cuanto
espera cada uno, etc. Al final saca los promedios.

Como todo es aleatorio, una sola corrida puede salir "con suerte" o "con mala
suerte". Por eso corremos **10 veces** (o mas) cada escenario y promediamos,
para que el resultado sea confiable. Eso da el **intervalo de confianza** (el
"±" que aparece en las tablas: "el valor real esta entre tanto y tanto").

## Las 3 fuentes que comparamos

El TP pide comparar tres formas de obtener los mismos numeros, para verificar
que todo cierra:

1. **Teorico** -> con las formulas de la teoria de colas (la "respuesta exacta"
   cuando rho < 1).
2. **Python** -> nuestro programa, que lo simula desde cero.
3. **AnyLogic** -> un programa visual de simulacion (lo armamos despues; la guia
   esta en `ANYLOGIC.md`).

Si las tres dan parecido, sabemos que el modelo esta bien hecho. Y en efecto:
nuestro Python da practicamente lo mismo que la teoria (error menor al 2% en la
zona estable).

## Resumen ultra rapido

- M/M/1 = una caja, gente que llega y se atiende al azar.
- rho = lambda/mu = que tan ocupada esta. Si rho >= 1, la fila explota.
- Medimos: cuanta gente hay, cuanto esperan, cuanto se usa la caja, y (con tope)
  cuanta gente se rechaza.
- Lo corremos 10 veces y promediamos.
- Comparamos teoria vs Python vs AnyLogic: dan lo mismo -> modelo validado.
