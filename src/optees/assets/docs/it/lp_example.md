# LP — Esempi Pratici

Usa questi esempi come modelli di riferimento quando costruisci il tuo problema di ottimizzazione lineare.
Ogni esempio può essere inserito direttamente nel form LP.

---

## Esempio 1 — Mix Produttivo (Massimizzazione)

**Scenario:** Un laboratorio produce sedie (**X₁**) e tavoli (**X₂**).

| Risorsa | Sedie (X₁) | Tavoli (X₂) | Disponibile |
|---------|-----------|------------|-------------|
| Ore macchina | 2 | 4 | ≤ 80 |
| Posti magazzino | 1 | 1 | ≤ 30 |
| **Profitto / unità** | **30** | **50** | — |

**Obiettivo:** massimizza **z = 30 X₁ + 50 X₂**

**Vincoli:**

- 2 X₁ + 4 X₂ ≤ 80  *(ore macchina)*
- X₁ + X₂ ≤ 30  *(magazzino)*

**Bounds:** X₁ ≥ 0, X₂ ≥ 0  *(continuo — la produzione frazionaria è ammessa)*

**Soluzione ottima:** X₁ = 10, X₂ = 15, **z\* = 1050**

```python
# SciPy minimizza sempre — nega i coefficienti per massimizzare
c      = [-30, -50]             # massimizza 30·X₁ + 50·X₂
A_ub   = [[2, 4], [1, 1]]
b_ub   = [80, 30]
bounds = [(0, None), (0, None)]
```

---

## Esempio 2 — Dieta / Miscelazione (Minimizzazione)

**Scenario:** Trovare il mix più economico di due ingredienti che soddisfi i requisiti nutrizionali.
Sia **X₁** = kg di ingrediente A, **X₂** = kg di ingrediente B.

**Obiettivo:** minimizza **z = 4 X₁ + 7 X₂**

**Vincoli (requisiti minimi):**

- 3 X₁ + X₂ ≥ 12  *(proteine ≥ 12 g)*
- X₁ + 2 X₂ ≥ 10  *(vitamine ≥ 10 mg)*

**Bounds:** X₁ ≥ 0, X₂ ≥ 0

> **Suggerimento — inserire vincoli ≥:** moltiplica entrambi i lati per −1 per ottenere la forma ≤:
> - −3 X₁ − X₂ ≤ −12
> - −X₁ − 2 X₂ ≤ −10

```python
c      = [4, 7]                   # minimizza il costo
A_ub   = [[-3, -1], [-1, -2]]    # vincoli ≥ ribaltati in ≤
b_ub   = [-12, -10]
bounds = [(0, None), (0, None)]
```

---

## Esempio 3 — Soluzioni Ottime Multiple

Quando la funzione obiettivo è **parallela** a un vincolo attivo, l'intero arco è ottimo
anziché un singolo vertice.

**Modello:** massimizza **z = X₁ + X₂** soggetto a X₁ + X₂ ≤ 6, X₁ ≥ 0, X₂ ≥ 0

Ogni punto dell'arco **X₁ + X₂ = 6** è ottimo → z\* = 6.

Optees lo rileva automaticamente e riporta:

```
X₁ ∈ [0, 6]   (libera di variare all'ottimo)
X₂ ∈ [0, 6]   (libera di variare all'ottimo)
→ Esistono infiniti ottimi
```

---

## Esempio 4 — Modello a Tre Variabili

**Modello:** massimizza **z = X₁ + X₂ + X₃** soggetto a X₁ + X₂ + X₃ ≤ 6, Xᵢ ≥ 0

L'insieme ammissibile è un simplesso 3D (tetraedro).
La faccia ottima è il triangolo dove X₁ + X₂ + X₃ = 6, dando **z\* = 6**
con infiniti ottimi.

```
Output Optees:
  Obiettivo   z* = 6.0
  X₁ ∈ [0, 6]   X₂ ∈ [0, 6]   X₃ ∈ [0, 6]
  Stato: Esistono infiniti ottimi
```

*Prova:* aggiungi 3 variabili, imposta un solo vincolo `X₁ + X₂ + X₃ ≤ 6` e premi **Ottimizza**.
