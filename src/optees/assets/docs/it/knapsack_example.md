# Esempi Knapsack 0/1

Il problema dello zaino 0/1 si usa quando devi scegliere un sottoinsieme di
oggetti. Ogni oggetto puo' essere preso una sola volta oppure escluso.

L'obiettivo e':

```text
massimizzare il valore totale
senza superare la capacita' disponibile
```

---

## Esempio 1 - Zaino didattico

Hai uno zaino con capacita' `5`. Puoi scegliere tra questi oggetti:

| Oggetto | Valore | Peso |
|---|---:|---:|
| A | 3 | 2 |
| B | 4 | 3 |
| C | 5 | 4 |

Modello:

```text
max z = 3 x_A + 4 x_B + 5 x_C

soggetto a:
  2 x_A + 3 x_B + 4 x_C <= 5

x_A, x_B, x_C in {0, 1}
```

Interpretazione delle variabili:

```text
x_A = 1  prendo A
x_A = 0  non prendo A
```

La soluzione ottima e':

```text
x_A = 1
x_B = 1
x_C = 0
```

Peso totale:

```text
2 + 3 = 5
```

Valore totale:

```text
3 + 4 = 7
```

Quindi la scelta migliore e' prendere `A` e `B`.

---

## Esempio 2 - Selezione progetti con budget

Supponi di avere un budget di `10` settimane e di dover scegliere quali progetti
sviluppare.

| Progetto | Valore atteso | Settimane richieste |
|---|---:|---:|
| Dashboard vendite | 9 | 5 |
| Automazione report | 6 | 4 |
| Portale clienti | 12 | 8 |
| Refactoring core | 7 | 3 |

Ogni progetto puo' essere scelto oppure no. Non puoi scegliere mezzo progetto,
quindi il modello e' 0/1:

```text
max z = 9 x_1 + 6 x_2 + 12 x_3 + 7 x_4

soggetto a:
  5 x_1 + 4 x_2 + 8 x_3 + 3 x_4 <= 10

x_i in {0, 1}
```

Una combinazione possibile e':

```text
dashboard + refactoring
peso = 5 + 3 = 8
valore = 9 + 7 = 16
```

Un'altra combinazione e':

```text
automazione + refactoring
peso = 4 + 3 = 7
valore = 6 + 7 = 13
```

Il solver confronta sistematicamente queste alternative e restituisce la
combinazione con valore massimo entro il budget.

---

## Esempio 3 - Carico di un furgone

Un furgone puo' trasportare al massimo `15` kg. Ogni collo ha un guadagno e un
peso.

| Collo | Guadagno | Peso |
|---|---:|---:|
| P1 | 20 | 4 |
| P2 | 30 | 6 |
| P3 | 35 | 7 |
| P4 | 12 | 3 |
| P5 | 3 | 1 |

Modello:

```text
max z = 20 x_1 + 30 x_2 + 35 x_3 + 12 x_4 + 3 x_5

soggetto a:
  4 x_1 + 6 x_2 + 7 x_3 + 3 x_4 + 1 x_5 <= 15

x_i in {0, 1}
```

La soluzione non e' necessariamente scegliere gli oggetti con valore assoluto
piu' alto. Conta il rapporto tra valore e peso, ma il rapporto da solo non basta:
serve valutare le combinazioni.

Per esempio:

```text
P2 + P3 + P5
peso = 6 + 7 + 1 = 14
valore = 30 + 35 + 3 = 68
```

Il problema Knapsack serve proprio a evitare scelte greedy miopi.

---

## Come inserirlo in Optees

1. Imposta la capacita' massima.
2. Inserisci una riga per ogni oggetto.
3. Scrivi il valore dell'oggetto.
4. Scrivi il peso intero dell'oggetto.
5. Premi `Ottimizza zaino`.

La pagina soluzione mostra:

- quali oggetti sono stati selezionati;
- il valore totale massimo;
- il peso totale usato;
- la capacita' residua.

