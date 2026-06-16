# Explicacion sencilla: el modelo de Inventario (s, S)

Una explicacion en criollo de que hace este modelo, para entenderlo rapido o
explicarlo en clase. Sin formulas pesadas (esas estan en el `README.md` y en el
informe).

## La idea en una frase

Imaginate que tenes un **kiosco** y vendes, digamos, gaseosas. Cada tanto
revisas el deposito y decidis si pedir mas o no. El modelo (s, S) es justamente
**la regla para decidir cuanto y cuando reponer stock**.

## El problema de fondo

Tener stock cuesta plata de tres formas, y estan en conflicto:

1. **Pedir mercaderia cuesta** (el flete, el tramite, el minimo de compra) ->
   **costo de ordenar**. Conviene pedir poco seguido.
2. **Guardar mercaderia cuesta** (espacio, plata inmovilizada, que se venza) ->
   **costo de mantenimiento (holding)**. Conviene tener poco stock.
3. **Quedarte sin stock cuesta** (perdes ventas, clientes enojados) ->
   **costo de faltante (shortage)**. Conviene tener mucho stock.

Fijate la trampa: si pedis seguido para no quedarte sin nada, gastas mucho en
ordenar y en guardar. Si pedis poco para ahorrar, te quedas sin stock y perdes
ventas. **No se pueden minimizar los tres a la vez.** El objetivo es encontrar
el equilibrio que de el **menor costo total**.

## La regla (s, S): que significan las dos letras

Es una politica de **revision periodica**: cada cierto tiempo (en nuestro caso
**una vez por mes**) miras cuanto stock te queda y aplicas esta regla:

- **s** (minuscula) = el **nivel de alarma**. Si el stock bajo de `s`, hay que
  reponer.
- **S** (mayuscula) = el **nivel objetivo**. Cuando repones, pedis hasta llegar
  a `S`.

En criollo:

> "Cada fin de mes miro el deposito. Si tengo menos de **s** unidades, pido las
> que falten para llegar a **S**. Si tengo **s** o mas, no pido nada."

Ejemplo con la politica **(20, 60)**:
- Si me quedan 12 unidades (menos de 20) -> pido 48 para llegar a 60.
- Si me quedan 35 unidades (mas de 20) -> no pido nada este mes.

## Que mas pasa en el modelo

- **La demanda es aleatoria**: los clientes llegan en momentos al azar y cada
  uno compra una cantidad al azar (1, 2, 3 o 4 unidades, con distinta chance).
  En promedio se venden **25 unidades por mes**.
- **El pedido no llega al instante**: cuando ordenas, tarda entre **medio mes y
  un mes** en llegar (el "lag" de entrega). Mientras tanto te podes quedar sin
  stock.
- **Si te quedas sin stock**, las ventas no se pierden del todo: quedan
  "anotadas" (backlog) y se entregan cuando llega la reposicion. Pero igual te
  cobran el **costo de faltante** por el tiempo que estuviste en rojo.

## Que medimos

Los cuatro costos, **promediados por mes**:

| Medida | Que es |
|---|---|
| **Costo de ordenar** | lo que gastas en hacer pedidos (un fijo por pedido + un extra por unidad pedida) |
| **Costo de mantenimiento** | lo que cuesta tener stock guardado |
| **Costo de faltante** | lo que cuesta estar sin stock (ventas en espera) |
| **Costo TOTAL** | la suma de los tres -> esto es lo que queremos minimizar |

## Los parametros (y por que esos)

Usamos los valores del libro de **Law (capitulo 1.5)**, que es el ejemplo
clasico de la materia, asi son faciles de justificar:

| Parametro | Valor | Que significa |
|---|---|---|
| Stock inicial | 60 unidades | con cuanto arrancamos |
| Horizonte | 120 meses | cuanto tiempo simulamos (10 años) |
| Demanda media | 25 u/mes | cuanto se vende |
| Costo fijo por pedido | 32 | el "flete" de cada orden |
| Costo por unidad pedida | 3 | extra por cada unidad que pedis |
| Mantenimiento | 1 por unidad-mes | guardar una unidad un mes cuesta 1 |
| Faltante | 5 por unidad-mes | estar sin una unidad un mes cuesta 5 |

> Nota: el faltante (5) cuesta mucho mas que el mantenimiento (1). Tiene logica:
> perder un cliente duele mas que tener un poco de stock de mas.

## Que politicas comparamos

Probamos 4 reglas distintas y vemos cual sale mas barata:

| Politica (s, S) | Idea |
|---|---|
| (20, 40) | alarma baja, objetivo bajo -> poco stock |
| **(20, 60)** | alarma baja, objetivo alto -> **la ganadora** |
| (40, 60) | alarma alta, objetivo medio -> mucho colchon |
| (40, 80) | alarma alta, objetivo alto -> mucho stock |

**Resultado: gana (20, 60)** con un costo total de ~122 por mes. Las otras
rondan los 127. La diferencia no es enorme (todas andan parecido), lo cual es
normal: cerca del optimo el costo es "plano".

## Como lo simulamos (sin detalle)

Igual que el otro modelo, es **simulacion por eventos**: el programa salta de un
suceso al siguiente. Los sucesos que importan son:

1. **Llega un cliente** y compra (baja el stock).
2. **Llega un pedido** que habiamos ordenado (sube el stock).
3. **Fin de mes**: se revisa el stock y se decide si ordenar.

El programa va anotando cuanto stock hay en cada momento para calcular los
costos. Como la demanda es al azar, corremos **10 veces** cada politica y
promediamos, para tener un resultado confiable (de ahi sale el "±" de las
tablas).

## Las 3 fuentes que comparamos

El TP pide verificar los numeros con tres metodos:

1. **Referencia analitica** -> calculos aproximados a mano (ej: demanda media 25
   u/mes). Ojo: este modelo NO tiene una "formula magica" exacta como el de
   colas, asi que la referencia es solo orientativa.
2. **Python** -> nuestro programa, la fuente mas confiable aca.
3. **AnyLogic** -> el programa visual (lo armamos despues; guia en
   `ANYLOGIC.md`).

## Resumen ultra rapido

- Manejas stock de algo y cada mes decidis si reponer.
- Regla (s, S): si el stock bajo de **s**, pedis hasta **S**.
- Hay 3 costos en conflicto: pedir, guardar y quedarte sin stock.
- Buscas la politica con el **menor costo total**: gana **(20, 60)**.
- Lo corremos 10 veces y promediamos.
- Comparamos referencia vs Python vs AnyLogic.
