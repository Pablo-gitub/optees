# Programmazione Lineare — Teoria e Algoritmi

## Cos'è la Programmazione Lineare?

Un **Programma Lineare (LP)** è un problema di ottimizzazione in cui sia la funzione
obiettivo che tutti i vincoli sono **funzioni lineari** di variabili decisionali continue.

L'LP è il fondamento della ricerca operativa moderna e viene applicata in logistica,
pianificazione della produzione, finanza, diete ottimali, trasporti e molto altro.

---

## Forma Matematica Standard

Il problema LP generale in notazione matriciale:

```
minimizza (o massimizza)    z = c₁x₁ + c₂x₂ + … + cₙxₙ + offset

soggetto a:
  a₁₁x₁ + a₁₂x₂ + … + a₁ₙxₙ  ≤  b₁     ← vincoli di disuguaglianza (A_ub x ≤ b_ub)
  a₂₁x₁ + …                   ≤  b₂
  …
  e₁₁x₁ + …                   =  d₁     ← vincoli di uguaglianza    (A_eq x = b_eq)
  lbᵢ  ≤  xᵢ  ≤  ubᵢ                    ← bounds sulle variabili
```

**Notazione chiave:**

- **x ∈ ℝⁿ** — variabili decisionali (possono essere frazionarie)
- **c ∈ ℝⁿ** — coefficienti dell'obiettivo (profitto o costo per unità)
- **A_ub, b_ub** — matrice dei vincoli di disuguaglianza e termine noto
- **A_eq, b_eq** — matrice dei vincoli di uguaglianza e termine noto
- **lb, ub** — limiti inferiori e superiori (usa −∞ / +∞ per illimitato)
- **offset** — termine costante aggiunto all'obiettivo (non influisce sull'ottimo)

> **Massimizzazione → Minimizzazione:** ogni LP di massimizzazione si risolve come
> minimizzazione negando l'obiettivo: max cᵀx  =  min (−c)ᵀx

---

## Geometria: Regione Ammissibile e Faccia Ottima

L'insieme dei vincoli definisce un **poliedro convesso** — la regione ammissibile.
Una funzione obiettivo lineare raggiunge sempre il suo ottimo su una **faccia** di questo poliedro.

| Faccia ottima | Dimensione | Significato |
|---|---|---|
| Singolo vertice | 0 | Soluzione ottima **unica** |
| Spigolo (faccia 1-D) | 1 | Infiniti ottimi lungo un segmento |
| Faccia k-dimensionale | k ≥ 2 | Infiniti ottimi su una superficie k-D |

**Teorema fondamentale dell'LP:**
Se un LP ammissibile ha un ottimo finito, allora almeno un **vertice** del poliedro
è una soluzione ottima. Questo è il fondamento matematico dell'algoritmo Simplex.

---

## L'Algoritmo Simplex (Dantzig, 1947)

Il metodo Simplex si sposta di vertice in vertice lungo gli spigoli del poliedro,
migliorando sempre la funzione obiettivo:

```
Algoritmo Simplex:
  1. Trova una soluzione di base ammissibile iniziale (un vertice)
  2. Calcola i costi ridotti per tutte le variabili non basiche
  3. Se tutti i costi ridotti ≥ 0  →  il vertice corrente è ottimo  (STOP)
  4. Scegli la variabile entrante  (costo ridotto più negativo)
  5. Scegli la variabile uscente   (test del rapporto minimo)
  6. Esegui lo scambio di base (pivot)  →  passa al vertice adiacente
  7. Torna al passo 2
```

**Il pivot in dettaglio:**

- Una *base* è un insieme di n vincoli attivi linearmente indipendenti (n = num. variabili)
- Una *soluzione di base ammissibile* è l'unico vertice definito da una base
- La **variabile entrante** è scelta per diminuire l'obiettivo più rapidamente
- La **variabile uscente** garantisce che la nuova soluzione rimanga ammissibile

Il Simplex ha complessità **esponenziale** nel caso peggiore (in teoria) ma opera
in tempo quasi lineare su praticamente tutti i problemi pratici.

---

## Metodi di Punto Interno (Karmarkar, 1984)

Invece di percorrere gli spigoli, i metodi di punto interno si muovono attraverso
l'**interno** della regione ammissibile lungo un percorso curvo verso l'ottimo:

```
Algoritmo (barriera/percorso centrale):
  1. Parti da un punto interno strettamente ammissibile
  2. Segui il percorso centrale (minimizza obiettivo + funzione barriera)
  3. Riduci il peso della barriera → la soluzione converge alla faccia ottima
  4. Fermati quando il gap di dualità < tolleranza
```

- **Complessità:** O(n³ · L) — polinomiale nella dimensione del problema
- Preferito per problemi molto grandi o numericamente mal condizionati
- Usato internamente da HiGHS per certe classi di problemi

---

## Il Solver HiGHS (usato da Optees)

Optees usa **[HiGHS](https://highs.dev)** — un solver LP/MIP open-source di ultima generazione —
tramite `scipy.optimize.linprog`:

```python
from scipy.optimize import linprog

result = linprog(
    c,                              # coefficienti obiettivo (minimizzazione)
    A_ub=A_ub, b_ub=b_ub,         # vincoli di disuguaglianza
    A_eq=A_eq, b_eq=b_eq,         # vincoli di uguaglianza (opzionale)
    bounds=list(zip(lb, ub)),      # bounds sulle variabili
    method="highs",                 # back-end HiGHS
)

# Codici result.status:
#   0  Soluzione ottima trovata
#   2  Problema inammissibile
#   3  Problema illimitato
#   4  Limite di iterazioni / tempo raggiunto
```

HiGHS sceglie automaticamente l'algoritmo più efficace (Simplex o punto interno).
Il codice di stato grezzo viene poi mappato da Optees in: **Ottimale / Non fattibile / Illimitato / Non risolto**.

---

## Dualità

Ogni LP ha un **problema duale** associato che fornisce informazioni complementari:

```
Primale:  min cᵀx   v.c. Ax ≥ b,  x ≥ 0
Duale:    max bᵀy   v.c. Aᵀy ≤ c, y ≥ 0
```

**Risultati chiave della dualità:**

- **Dualità debole:** obiettivo duale ≤ obiettivo primale (per coppia min/max)
- **Dualità forte:** all'ottimo, valore primale = valore duale
- **Prezzi ombra (variabili duali yᵢ):** la variazione di z\* per unità di aumento di bᵢ

I prezzi ombra indicano quanto vale rilassare ogni vincolo di un'unità.

---

## Intervalli Ottimi delle Variabili (Funzione di Optees)

Dopo aver trovato il valore ottimo **z\***, Optees calcola l'intervallo di ogni variabile
su **tutte** le soluzioni ottime tramite un algoritmo di post-elaborazione:

```
Algoritmo — Analisi degli Intervalli Ottimi:
  1. Risolvi LP  →  ottieni il valore ottimo z*
  2. Aggiungi il vincolo di uguaglianza:  cᵀx = z*   (fissa l'obiettivo all'ottimo)
  3. Per ogni variabile decisionale xᵢ  (i = 1 … n):
       risolvi LP_min:  min xᵢ   soggetto ai vincoli originali + cᵀx = z*
       risolvi LP_max:  max xᵢ   soggetto ai vincoli originali + cᵀx = z*
       → intervallo ottimo di xᵢ  =  [min xᵢ,  max xᵢ]
  4. Se  min xᵢ < max xᵢ  per qualche i  →  esistono molteplici soluzioni ottime
```

Questo è solo un **passo di post-elaborazione**: 2n risoluzioni LP aggiuntive, ognuna
economica perché la matrice dei vincoli viene riutilizzata dal problema originale.

**Interpretazione:**

- Intervallo = `[a, a]` (punto singolo): la variabile è **fissata** all'ottimo
- Intervallo = `[a, b]` con a < b: la variabile è **libera di variare** — esistono infiniti ottimi
