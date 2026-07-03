# Knapsack - Descrizione del problema

Il Knapsack e' una famiglia di modelli di ottimizzazione in cui devi allocare
risorse limitate scegliendo oggetti o quantita' di oggetti. La struttura comune
e':

```text
massimizzare valore
soggetto a una o piu' capacita'
```

La differenza tra le varianti e' il dominio delle variabili decisionali.

---

## Forma generale

Per ogni oggetto `i` conosci:

| Simbolo | Significato |
|---|---|
| `v_i` | valore unitario |
| `w_i` | consumo della risorsa singola, nel caso monodimensionale |
| `a_{i,r}` | consumo della risorsa `r`, nel caso multi-dimensionale |
| `C` | capacita' singola |
| `C_r` | capacita' della risorsa `r` |

La variabile `x_i` dice quanto dell'oggetto `i` scegli. Il dominio cambia in
base alla variante:

| Variante | Dominio |
|---|---|
| 0/1 | `x_i in {0, 1}` |
| Bounded | `x_i in {0, ..., u_i}` |
| Unbounded | `x_i in {0, 1, 2, ...}` |
| Fractional | `0 <= x_i <= 1` o `0 <= x_i <= u_i` |

---

## Knapsack 0/1

Il modello 0/1 e':

```text
max sum_i v_i x_i

soggetto a:
  sum_i w_i x_i <= C

x_i in {0, 1}
```

Ogni oggetto entra interamente oppure non entra. Non puoi prendere il 30% di un
oggetto. Questa variante e' adatta a selezione di progetti, colli da caricare,
funzionalita' da includere in una release.

### Algoritmo

Optees usa programmazione dinamica esatta:

```text
dp[i][c] = miglior valore usando i primi i oggetti e capacita' c
```

Per ogni oggetto confronta:

```text
1. escluderlo
2. includerlo, se entra nella capacita'
```

La ricorrenza e':

```text
dp[i][c] = max(
    dp[i-1][c],
    dp[i-1][c - w_i] + v_i
)
```

La complessita' e' pseudo-polinomiale:

```text
tempo  O(n * C)
spazio O(n * C)
```

---

## Bounded Knapsack

Nel bounded knapsack puoi scegliere piu' copie dello stesso oggetto, ma fino a
un limite massimo:

```text
max sum_i v_i x_i

soggetto a:
  sum_i w_i x_i <= C

x_i in {0, 1, ..., u_i}
```

Il limite `u_i` rappresenta disponibilita', scorta, numero massimo di lotti o
quantita' massima accettabile.

### Algoritmo

Optees usa una programmazione dinamica che prova, per ogni oggetto, tutte le
quantita' ammissibili da `0` a `u_i`. E' esatta per pesi e capacita' interi, ma
puo' crescere rapidamente quando capacita' e limiti sono grandi.

---

## Unbounded Knapsack

Nell'unbounded knapsack ogni oggetto rappresenta un tipo ripetibile:

```text
x_i in {0, 1, 2, ...}
```

Il modello e':

```text
max sum_i v_i x_i

soggetto a:
  sum_i w_i x_i <= C

x_i intero non negativo
```

E' utile per lotti standard, tagli ripetibili, pacchetti replicabili.

### Algoritmo

Optees usa programmazione dinamica consentendo di riutilizzare lo stesso oggetto
piu' volte. Anche qui il solver e' esatto per capacita' e pesi interi.

---

## Fractional Knapsack

Nel fractional knapsack puoi prendere una frazione dell'oggetto:

```text
0 <= x_i <= 1
```

Il modello e':

```text
max sum_i v_i x_i

soggetto a:
  sum_i w_i x_i <= C
  0 <= x_i <= 1
```

Nel caso monodimensionale classico, il greedy per densita' `v_i / w_i` e'
ottimo: ordini gli oggetti per valore per unita' di peso e riempi la capacita'.

Questa proprieta' non vale automaticamente quando ci sono piu' risorse.

---

## Multi-dimensional Knapsack

Nel multi-dimensional knapsack ogni oggetto consuma un vettore di risorse:

```text
max sum_i v_i x_i

soggetto a:
  sum_i a_{i,r} x_i <= C_r    per ogni risorsa r
```

Esempi di risorse:

- peso;
- volume;
- ore macchina;
- budget;
- energia;
- memoria.

La versione 0/1 usa:

```text
x_i in {0, 1}
```

Optees la risolve con branch-and-bound dedicato: esplora scelte binarie,
elimina i rami che violano una risorsa e conserva la miglior soluzione
ammissibile.

---

## Multi-dimensional con dominio variabile

Nella view Multi-dimensionale puoi scegliere il dominio della quantita':

| Dominio | Modello |
|---|---|
| 0/1 | `x_i in {0, 1}` |
| Intera limitata | `x_i in {0, ..., u_i}` |
| Intera illimitata | `x_i intero, x_i >= 0` |
| Frazionabile | `x_i continuo, 0 <= x_i <= u_i` |

Le varianti intere vengono mappate a un MILP. La variante frazionabile viene
mappata a un modello lineare continuo. Questo e' importante: con piu' risorse il
greedy valore/peso non basta, perche' non esiste una sola nozione di "peso".

---

## Relazione con MILP e LP

Molte varianti Knapsack sono casi speciali di LP o MILP:

```text
max v^T x
soggetto a A x <= b
x_i binario, intero o continuo
```

La view Knapsack e' piu' didattica perche' parla il linguaggio del problema:
oggetti, valori, capacita', risorse e quantita'. La view MILP resta piu'
generale quando vuoi scrivere vincoli arbitrari non riconducibili alla struttura
Knapsack.

---

## Come leggere la soluzione

| Campo | Significato |
|---|---|
| Stato | `Optimal` se la soluzione e' provata ottima |
| Valore migliore | valore totale della soluzione |
| Scelto | oggetto incluso nel caso 0/1 |
| Quantita' | numero di copie o quantita' continua |
| Frazione | quota scelta nel fractional monodimensionale |
| Uso risorse | consumo totale di ogni capacita' |
| Residuo | capacita' non utilizzata |

Se lo stato e' `Optimal`, la soluzione mostrata e' la migliore possibile per il
modello inserito.
