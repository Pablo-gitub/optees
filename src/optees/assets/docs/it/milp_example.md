# Esempi MILP

La MILP e' utile quando un modello lineare contiene decisioni che devono essere
intere oppure booleane si/no. Usa il tipo variabile `Binaria / booleana (0/1)`
per decisioni come aperto/chiuso, scelto/non scelto, attivo/non attivo.

## Problema di assegnamento

Due lavoratori devono essere assegnati a due lavori. Sia:

| Variabile | Significato | Tipo |
|---|---|---|
| x11 | lavoratore 1 sul lavoro 1 | binaria |
| x12 | lavoratore 1 sul lavoro 2 | binaria |
| x21 | lavoratore 2 sul lavoro 1 | binaria |
| x22 | lavoratore 2 sul lavoro 2 | binaria |

Minimizza il costo:

```text
min z = 1 x11 + 2 x12 + 2 x21 + 1 x22
```

Ogni lavoratore riceve esattamente un lavoro:

```text
x11 + x12 = 1
x21 + x22 = 1
```

Ogni lavoro e' coperto una sola volta:

```text
x11 + x21 = 1
x12 + x22 = 1
```

La soluzione ottima e' `x11 = 1`, `x22 = 1`, con obiettivo `z = 2`.

## Apertura impianto con spedizione

Supponi di poter spedire da un impianto solo se decidi di aprirlo. Sia:

| Variabile | Significato | Tipo |
|---|---|---|
| y | aprire l'impianto | binaria |
| x | unita' spedite | continua o intera |

Il vincolo di collegamento e':

```text
0 <= x <= 120 y
y in {0, 1}
```

Se `y = 0`, l'impianto e' chiuso e quindi `x = 0`. Se `y = 1`, puoi spedire
fino a 120 unita'. Un obiettivo tipico minimizza costo fisso e costo variabile:

```text
min z = 800 y + 6 x
```

## Minimizzazione scarti con scaglioni produttivi

La MILP e' adatta quando lo scarto unitario dipende sia dal prodotto sia dalla
fascia di quantita' prodotta. Devi decidere quanto produrre e in quale blocco
produttivo collocare ogni prodotto.

Per un prodotto `X`, supponi:

| Quantita' prodotta | Scarto unitario |
|---|---:|
| 0-999 | 8% |
| 1000+ | 4% |

Dividi la quantita' in due variabili di blocco:

```text
q_X = q_X1 + q_X2
```

| Variabile | Significato | Tipo |
|---|---|---|
| q_X1 | quantita' di X nel blocco 0-999 | continua o intera |
| q_X2 | quantita' di X nel blocco 1000+ | continua o intera |
| y_X1 | uso del blocco 0-999 | binaria |
| y_X2 | uso del blocco 1000+ | binaria |

Vincoli di blocco:

```text
0 <= q_X1 <= 999 y_X1
1000 y_X2 <= q_X2 <= M y_X2
y_X1 + y_X2 <= 1
y_X1, y_X2 in {0, 1}
```

Se vuoi minimizzare lo scarto prodotto:

```text
min z = 0.08 q_X1 + 0.04 q_X2
```

Se invece devi soddisfare una domanda netta `d_X`, cioe' pezzi buoni dopo lo
scarto, aggiungi:

```text
0.92 q_X1 + 0.96 q_X2 >= d_X
```

Per piu' prodotti, ripeti la stessa struttura per ogni prodotto `i` e ogni
blocco `k`:

```text
min sum_i sum_k scarto_i,k q_i,k
```

con vincoli di domanda:

```text
sum_k resa_i,k q_i,k >= domanda_i
```

e vincoli binari che scelgono al massimo un blocco produttivo per ciascun
prodotto.
