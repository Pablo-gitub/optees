# Esempi Knapsack

La famiglia Knapsack serve quando devi scegliere oggetti o quantita' di oggetti
massimizzando un valore e rispettando una o piu' capacita'. La differenza tra le
varianti sta nel significato della variabile decisionale `x_i`.

| Variante | Significato di `x_i` |
|---|---|
| 0/1 | oggetto escluso o scelto una volta |
| Bounded | quantita' intera con limite massimo |
| Unbounded | quantita' intera senza limite esplicito |
| Fractional | quantita' continua o frazione |
| Multi-dimensionale | una o piu' risorse: peso, volume, tempo, budget |

---

## 1. Knapsack 0/1 - scelta di oggetti

Hai uno zaino con capacita' `5`.

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

La soluzione ottima e':

```text
x_A = 1
x_B = 1
x_C = 0
```

Peso totale `2 + 3 = 5`, valore totale `3 + 4 = 7`.

Usa questa variante quando ogni oggetto puo' essere scelto al massimo una volta:
caricare un furgone, selezionare progetti, scegliere funzionalita' entro un
budget.

---

## 2. Bounded Knapsack - quantita' intere limitate

Un magazzino deve preparare un kit promozionale. Ogni articolo ha valore, peso e
un numero massimo disponibile.

| Articolo | Valore | Peso | Quantita' max |
|---|---:|---:|---:|
| Penna | 2 | 1 | 4 |
| Tazza | 8 | 3 | 2 |
| Quaderno | 5 | 2 | 3 |

Capacita': `7`.

Modello:

```text
max z = 2 x_1 + 8 x_2 + 5 x_3

soggetto a:
  1 x_1 + 3 x_2 + 2 x_3 <= 7

x_1 in {0, 1, 2, 3, 4}
x_2 in {0, 1, 2}
x_3 in {0, 1, 2, 3}
```

Una soluzione possibile e':

```text
x_1 = 1
x_2 = 2
x_3 = 0

peso = 1 + 2*3 = 7
valore = 2 + 2*8 = 18
```

Usa questa variante quando puoi scegliere piu' copie di uno stesso tipo, ma la
disponibilita' e' limitata.

---

## 3. Unbounded Knapsack - quantita' intere senza limite

Un'applicazione deve riempire una memoria di cache con blocchi replicabili.
Ogni tipo di blocco puo' essere usato piu' volte.

| Blocco | Valore | Peso |
|---|---:|---:|
| A | 3 | 1 |
| B | 5 | 3 |
| C | 9 | 4 |

Capacita': `7`.

Modello:

```text
max z = 3 x_A + 5 x_B + 9 x_C

soggetto a:
  1 x_A + 3 x_B + 4 x_C <= 7

x_A, x_B, x_C in {0, 1, 2, ...}
```

Qui il solver puo' scegliere, per esempio, due blocchi `C` se entrassero nella
capacita', oppure combinazioni ripetute di `A` e `B`.

Usa questa variante quando gli oggetti rappresentano tipi ripetibili: tagli di
materiale, lotti standard, pacchetti replicabili.

---

## 4. Fractional Knapsack - oggetti divisibili

Supponi di avere materie prime divisibili. Puoi prendere una frazione di ogni
materiale.

| Materiale | Valore | Peso |
|---|---:|---:|
| A | 60 | 10 |
| B | 100 | 20 |
| C | 120 | 30 |

Capacita': `50`.

Modello:

```text
max z = 60 x_A + 100 x_B + 120 x_C

soggetto a:
  10 x_A + 20 x_B + 30 x_C <= 50

0 <= x_A, x_B, x_C <= 1
```

Nel caso monodimensionale il criterio valore/peso e' ottimo:

```text
A: 60 / 10 = 6
B: 100 / 20 = 5
C: 120 / 30 = 4
```

Il solver prende prima `A`, poi `B`, poi una frazione di `C`:

```text
x_A = 1
x_B = 1
x_C = 2/3

valore = 60 + 100 + 80 = 240
```

Usa questa variante quando gli oggetti sono realmente divisibili: liquidi,
materie prime, fondi finanziari, tempo allocabile.

---

## 5. Multi-dimensional 0/1 - piu' risorse

Ora ogni oggetto consuma piu' risorse contemporaneamente. Per esempio peso e
volume.

| Oggetto | Valore | Peso | Volume |
|---|---:|---:|---:|
| A | 8 | 4 | 1.5 |
| B | 9 | 5 | 2 |
| C | 14 | 6 | 4.5 |
| D | 7 | 3 | 2 |

Capacita':

```text
peso <= 10
volume <= 6
```

Modello:

```text
max z = 8 x_A + 9 x_B + 14 x_C + 7 x_D

soggetto a:
  4 x_A + 5 x_B + 6 x_C + 3 x_D <= 10
  1.5 x_A + 2 x_B + 4.5 x_C + 2 x_D <= 6

x_i in {0, 1}
```

La soluzione deve rispettare entrambe le capacita'. Un insieme puo' stare nel
peso ma violare il volume, quindi non basta guardare una sola risorsa.

---

## 6. Multi-dimensional con quantita'

Nella variante multi-dimensionale puoi cambiare il dominio di `x_i`.

### Intera limitata

```text
x_i in {0, ..., u_i}
```

Esempio: scegli quante casse di ogni prodotto caricare, con scorte massime.

### Intera illimitata

```text
x_i in {0, 1, 2, ...}
```

Esempio: scegli quanti lotti standard produrre, limitati solo da ore macchina e
materia prima.

### Frazionabile

```text
0 <= x_i <= u_i
```

Esempio: scegli quanti chilogrammi di ingredienti usare, con vincoli su peso,
volume e budget. Con piu' risorse il problema non si risolve con il greedy
valore/peso: diventa un LP continuo.

---

## Come inserirli in Optees

1. Scegli la variante Knapsack.
2. Seleziona il dominio quando usi Multi-dimensionale.
3. Inserisci capacita', risorse e oggetti.
4. Inserisci eventuali limiti massimi.
5. Premi `Ottimizza zaino`.

La pagina soluzione mostra valore ottimo, oggetti o quantita' scelte, uso delle
risorse e capacita' residue.
