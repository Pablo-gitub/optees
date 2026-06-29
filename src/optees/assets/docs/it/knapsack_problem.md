# Knapsack 0/1 - Descrizione del problema

Il problema Knapsack 0/1 e' uno dei modelli classici della ricerca operativa.
Il nome viene dall'immagine dello zaino: hai una capacita' limitata e devi
decidere quali oggetti portare con te.

La caratteristica fondamentale e':

```text
ogni oggetto puo' essere scelto oppure escluso
```

Non puoi prendere il 30% di un oggetto. Questa e' la parte `0/1` del problema.

---

## Forma matematica

Dato un insieme di `n` oggetti, per ogni oggetto `i` conosci:

| Simbolo | Significato |
|---|---|
| `v_i` | valore dell'oggetto |
| `w_i` | peso dell'oggetto |
| `C` | capacita' massima dello zaino |

Introduci una variabile binaria:

```text
x_i = 1  se l'oggetto i viene scelto
x_i = 0  se l'oggetto i viene escluso
```

Il modello e':

```text
max z = sum_i v_i x_i

soggetto a:
  sum_i w_i x_i <= C

x_i in {0, 1}
```

L'obiettivo massimizza il valore totale degli oggetti scelti. Il vincolo dice
che il peso totale non puo' superare la capacita'.

---

## Perche' non basta ordinare per valore/peso

Una regola intuitiva sarebbe scegliere prima gli oggetti con rapporto
`valore / peso` piu' alto. Questa idea funziona per il knapsack frazionario,
dove puoi prendere anche parti di oggetti, ma non garantisce l'ottimo nel
knapsack 0/1.

Nel modello 0/1 un oggetto entra interamente oppure non entra. Quindi la
combinazione migliore puo' dipendere dagli incastri tra pesi.

Esempio:

```text
capacita' = 10

A: valore 60, peso 10
B: valore 35, peso 6
C: valore 30, peso 4
```

Il rapporto migliore e' di `C`, poi `B`, poi `A`. La combinazione `B + C` pesa
10 e vale 65, quindi batte `A`, anche se nessuno dei due oggetti da solo vale
quanto `A`.

---

## Algoritmo implementato in Optees

La prima implementazione usa programmazione dinamica esatta.

L'idea e' costruire una tabella:

```text
dp[i][c]
```

dove:

- `i` indica quanti oggetti stiamo considerando;
- `c` indica una capacita' disponibile da `0` a `C`;
- `dp[i][c]` contiene il massimo valore ottenibile con i primi `i` oggetti e
  capacita' `c`.

Per ogni oggetto hai due possibilita':

```text
1. non prendere l'oggetto
2. prendere l'oggetto, se il suo peso entra nella capacita' corrente
```

La ricorrenza e':

```text
dp[i][c] = max(
    dp[i-1][c],
    dp[i-1][c - w_i] + v_i
)
```

La seconda opzione e' disponibile solo se `w_i <= c`.

Alla fine il valore ottimo si trova in:

```text
dp[n][C]
```

Optees ricostruisce poi quali oggetti sono stati scelti camminando all'indietro
nella tabella.

---

## Complessita'

La programmazione dinamica e' esatta, ma ha complessita':

```text
tempo  O(n * C)
spazio O(n * C)
```

dove:

- `n` e' il numero di oggetti;
- `C` e' la capacita'.

Questa complessita' si chiama pseudo-polinomiale: dipende dal valore numerico
della capacita', non solo dal numero di cifre usate per scriverla.

Per questo Optees impone un limite pratico alla dimensione della tabella DP. Se
un'istanza e' troppo grande per questa implementazione, la soluzione viene
marcata come `NotSolved` con un messaggio diagnostico.

---

## Relazione con MILP

Il Knapsack 0/1 e' anche un caso particolare di MILP:

```text
max v^T x
soggetto a w^T x <= C
x_i in {0, 1}
```

Quindi un solver MILP puo' risolverlo. Tuttavia, una view dedicata Knapsack e'
piu' didattica e piu' rapida da usare quando il problema ha esattamente questa
struttura: oggetti, valori, pesi e capacita'.

La view MILP resta piu' generale; la view Knapsack espone direttamente il
linguaggio naturale del problema.

---

## Come leggere la soluzione

La soluzione mostra:

| Campo | Significato |
|---|---|
| Stato | `Optimal` se la soluzione e' provata ottima |
| Valore migliore | somma dei valori degli oggetti scelti |
| Peso totale | peso usato nello zaino |
| Capacita' residua | capacita' non utilizzata |
| Scelto | indica se l'oggetto entra nella soluzione |

Se lo stato e' `Optimal`, la combinazione mostrata e' la migliore possibile tra
tutte le combinazioni ammissibili.

