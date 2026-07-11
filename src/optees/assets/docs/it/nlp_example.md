# Esempi di Programmazione Nonlineare

La Programmazione Nonlineare continua e' adatta quando le variabili decisionali
sono reali ma l'obiettivo non e' lineare. In questo primo flusso di Optees
fornisci un punto iniziale ammissibile e risolvi un problema senza vincoli
generali oppure con soli bounds.

Il risultato e' un **candidato numerico locale**. Punti iniziali diversi possono
portare a candidati diversi quando il paesaggio ha piu' valli o picchi.

## Valle di Rosenbrock

La funzione di Rosenbrock ha una valle stretta e curva:

```text
min f(x1, x2) = (1 - x1)^2 + 100 (x2 - x1^2)^2
```

Usa `x1 = -1.2`, `x2 = 1`, bounds vuoti, **Nelder-Mead**, e:

```text
(1 - x1)**2 + 100 * (x2 - x1**2)**2
```

La basin scelta contiene il minimo `(1, 1)` con `f = 0`. L'esempio mostra
perche' la scelta del metodo conta: un simplesso derivative-free e' una buona
base su una valle stretta, mentre BFGS con differenze finite puo' riportare una
terminazione legata alla precisione prima di dichiarare convergenza.

## Quadratica nonlineare con bounds

Minimizza:

```text
min f(x1, x2) = (x1 - 5)^2 + (x2 - 1)^2
```

con `0 <= x1 <= 2` e `-2 <= x2 <= 2`. Parti da `(0, 0)` e scegli
**L-BFGS-B**. Il minimo non vincolato sarebbe `(5, 1)`, ma `x1 = 5` non e'
ammesso. Il candidato vincolato e' `(2, 1)` con obiettivo `9`.

I bounds non aggiungono una formula all'obiettivo: restringono i punti che il
metodo numerico puo' considerare come candidati.

## Massimizzazione nonlineare

Optees accetta anche la massimizzazione:

```text
max f(x1) = 10 - (x1 - 3)^2
```

Parti da `x1 = 0`, lascia i bounds vuoti e scegli BFGS. Il miglior candidato
locale e' `x1 = 3`, con valore dell'obiettivo `10`. Internamente il backend
minimizza `-f(x1)`, ma il risultato mostra sempre il valore originale.

## Sintassi dell'espressione

Il campo obiettivo e' un linguaggio matematico ristretto, non una console
Python. Accetta i nomi delle variabili dichiarate, numeri, parentesi, `+`, `-`,
`*`, `/`, `**`, segni unari e queste funzioni a un argomento:

```text
abs, sin, cos, tan, exp, log, sqrt
```

Per esempio: `sqrt(x1**2 + x2**2) + exp(x1)`. Nomi sconosciuti, import,
attributi, indici, confronti e codice Python vengono rifiutati prima del solve.
Ogni valutazione deve essere finita: `log(-1)`, `sqrt(-1)`, divisione per zero,
`NaN` e infinito sono segnalati come errori.
