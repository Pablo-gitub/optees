# Descrizione del problema MILP

La Mixed-Integer Linear Programming (MILP) estende la Programmazione Lineare
aggiungendo una richiesta fondamentale: alcune variabili non possono assumere
qualsiasi valore reale, ma devono essere intere oppure binarie.

In una LP continua il solver puo' scegliere, per esempio, `x = 2.37`. In una
MILP puoi imporre che una variabile sia:

| Tipo | Significato |
|---|---|
| Continua | puo' assumere valori frazionari |
| Intera | deve assumere valori interi |
| Binaria / booleana | puo' valere solo 0 oppure 1 |

Questo cambia radicalmente il problema: non devi solo ottimizzare una funzione
lineare, devi anche scegliere una combinazione discreta ammissibile.

## Forma matematica

Un modello MILP puo' essere scritto cosi':

```text
optimize    c^T x + alpha
subject to  A_ub x <= b_ub
            A_eq x  = b_eq
            l <= x <= u
            x_j in R        per variabili continue
            x_j in Z        per variabili intere
            x_j in {0, 1}   per variabili binarie / booleane
```

Le prime righe sono uguali alla LP: obiettivo lineare, vincoli lineari e bounds.
La differenza e' nelle ultime righe, dove imponi il dominio delle variabili.

Una variabile binaria rappresenta una scelta logica:

```text
y = 1  scelta attiva
y = 0  scelta non attiva
```

Per questo la MILP e' adatta a problemi con setup, aperture, assegnamenti,
scaglioni, soglie, lotti minimi e decisioni alternative.

## Intuizione geometrica

Nella LP, i vincoli definiscono una regione continua: un poliedro. Il solver
puo' muoversi dentro questa regione e l'ottimo si trova su un vertice o su una
faccia.

Nella MILP, alcune coordinate devono cadere su valori interi. Quindi non tutti i
punti del poliedro sono utilizzabili. Il solver vede due livelli:

1. la regione continua della LP rilassata;
2. i soli punti che rispettano anche l'integralita'.

La rilassata LP puo' suggerire un punto molto buono, ma se quel punto contiene
una variabile binaria uguale a `0.43` non e' una soluzione MILP ammissibile.

## Cosa fa Optees quando premi Ottimizza

Quando premi `Ottimizza MILP`, Optees prende il modello della GUI e lo converte
in un dizionario canonico:

```text
sense         min oppure max
c             coefficienti dell'obiettivo
A_ub, b_ub    vincoli <=
A_eq, b_eq    vincoli =
bounds        limiti inferiori e superiori
integrality   C, I, B per ogni variabile
var_names     nomi delle variabili
```

I vincoli `>=` vengono trasformati in vincoli `<=` cambiando segno. Per esempio:

```text
2 x + y >= 10
```

diventa:

```text
-2 x - y <= -10
```

Le variabili binarie sono normalizzate come:

```text
0 <= y <= 1
y intera
```

Poi Optees invia il problema al solver OR-Tools:

- CP-SAT per modelli interi/binari con dati adatti;
- CBC per modelli misti o coefficienti non interi.

## Come ragiona l'algoritmo

L'idea didattica piu' importante e' questa: il solver alterna stime continue e
scelte discrete.

Prima risolve o considera una rilassata LP, cioe' il problema senza imporre che
le variabili siano intere. Questa rilassata fornisce un limite teorico: se
nemmeno la rilassata puo' fare meglio di una soluzione gia' trovata, allora
quella parte della ricerca puo' essere scartata.

Quando una variabile discreta assume un valore frazionario, il solver crea rami.
Per esempio, se nella rilassata ottiene:

```text
y = 0.43
```

allora puo' dividere il problema in due sotto-problemi:

```text
y = 0
y = 1
```

Oppure, per una variabile intera `x = 4.7`, puo' separare:

```text
x <= 4
x >= 5
```

Questo processo e' la logica del branch-and-bound.

## Incumbent, best bound e MIP gap

Durante la ricerca il solver mantiene due informazioni:

| Nome | Significato |
|---|---|
| Incumbent | migliore soluzione intera ammissibile trovata finora |
| Best bound | miglior limite teorico ancora possibile |

Per un problema di minimizzazione:

- l'incumbent e' un valore ottenuto da una soluzione vera;
- il best bound dice quanto potrebbe ancora migliorare il valore ottimo.

Il MIP gap misura la distanza relativa tra incumbent e best bound. Se il gap e'
piccolo, la soluzione trovata e' vicina alla prova di ottimalita'. Se il gap e'
zero o entro la tolleranza, il solver puo' dichiarare `Optimal`.

## Come leggere gli stati

| Stato | Significato |
|---|---|
| Optimal | il solver ha trovato una soluzione e ha provato che e' ottima |
| Feasible | il solver ha trovato una soluzione ammissibile ma non ha provato che sia ottima |
| Infeasible | non esiste alcuna soluzione che soddisfi tutti i vincoli |
| Unbounded | il valore puo' migliorare senza limite |
| NotSolved | il solver non ha prodotto una soluzione utilizzabile |

Lo stato `Feasible` e' molto importante in MILP. Non significa fallimento:
significa che la soluzione rispetta i vincoli, ma il solver non ha completato la
prova matematica di ottimalita'. Questo puo' succedere con un limite di tempo o
con modelli combinatori difficili.

## Esempio concettuale: soglie produttive

Se lo scarto di produzione cambia con la quantita', il modello contiene una
scelta discreta di blocco. Per esempio:

| Quantita' prodotta | Scarto |
|---|---:|
| 0-999 | 8% |
| 1000+ | 4% |

La domanda non e' solo "quanto produco?", ma anche "quale fascia produttiva sto
usando?". Questa seconda domanda richiede variabili binarie.

Una formulazione possibile e':

```text
q_X = q_X1 + q_X2
0 <= q_X1 <= 999 y_X1
1000 y_X2 <= q_X2 <= M y_X2
y_X1 + y_X2 <= 1
y_X1, y_X2 in {0, 1}
```

L'obiettivo di minimizzazione degli scarti diventa:

```text
min 0.08 q_X1 + 0.04 q_X2
```

Il solver decide contemporaneamente:

- quanta quantita' assegnare ai blocchi;
- quale blocco attivare;
- quale combinazione minimizza lo scarto totale rispettando domanda e vincoli.

## Limite importante

La MILP resta lineare. Questo significa che obiettivo e vincoli devono essere
scritti come somme di coefficienti per variabili. Se compaiono prodotti tra
variabili, potenze, radici o funzioni curve, il problema non e' piu' una MILP
pura e potrebbe richiedere programmazione non lineare o una riformulazione.
