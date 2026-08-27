# Esempi svolti

Tre problemi piccoli, ciascuno con una risposta verificabile a mano.
Inseriscili nella pagina di formulazione e confronta i risultati.

## 1. Un ottimo interno

Nessun vincolo. La conca ha un fondo, e il fondo è la risposta.

```
minimizza  ½ (2x₁² + 2x₂² + 2x₁x₂) − 4x₁ − 6x₂
```

Da inserire come:

| Campo | Valore |
| --- | --- |
| Verso | Minimizza |
| Q | `[[2, 1], [1, 2]]` |
| c | `[-4, -6]` |
| α | `0` |
| Limiti | entrambi vuoti (illimitati) |
| Vincoli | nessuno |

Annullando il gradiente `Qx + c` si ottiene l'ottimo esatto

```
x* = (2/3, 8/3) ≈ (0.6667, 2.6667)      f(x*) = −28/3 ≈ −9.3333
```

Entrambe le variabili risultano **Interne**: nulla le sta trattenendo.

## 2. Un ottimo sul bordo

Qui è il vincolo a fare il lavoro.

```
minimizza  ½ (x₁² + x₂²)
soggetto a  x₁ + x₂ ≥ 2,  x₁ ≥ 0,  x₂ ≥ 0
```

| Campo | Valore |
| --- | --- |
| Verso | Minimizza |
| Q | `[[1, 0], [0, 1]]` |
| c | `[0, 0]` |
| Limiti | limite inferiore `0` per entrambe |
| Vincolo | `1·x₁ + 1·x₂ ≥ 2` |

Il minimo non vincolato è l'origine, ma l'origine non è ammissibile. La
risposta è il punto ammissibile più vicino a essa:

```
x* = (1, 1)      f(x*) = 1
```

La riga del vincolo risulta **Attivo** con scarto nullo e porta un
moltiplicatore duale non nullo: rilassare il termine noto migliorerebbe
l'obiettivo. Con due variabili il grafico lo mostra direttamente: curve di
livello concentriche spinte contro la retta del vincolo, che la toccano in
esattamente un punto.

## 3. Massimizzazione concava

Il caso speculare. `Q` è definita negativa, quindi la superficie è una cupola.

```
massimizza  −½ (2x₁² + 2x₂²) + 4x₁ + 6x₂
soggetto a  x₁ ≥ 0,  x₂ ≥ 0
```

| Campo | Valore |
| --- | --- |
| Verso | Massimizza |
| Q | `[[-2, 0], [0, -2]]` |
| c | `[4, 6]` |
| Limiti | limite inferiore `0` per entrambe |

```
x* = (2, 3)      f(x*) = 13
```

Nota che la stessa matrice con **Minimizza** selezionato viene rifiutata: una
cupola non ha minimo, e il messaggio indica la curvatura come motivo.

## Due fallimenti istruttivi

Vale la pena riprodurli di proposito: il rifiuto è la lezione.

**Non ammissibile.** Aggiungi a un problema qualsiasi sia `x₁ + x₂ ≤ 1` sia
`x₁ + x₂ ≥ 3`. Nessun punto soddisfa entrambi. L'esito è `Non ammissibile`,
senza vettore candidato.

**Illimitato.** Minimizza con `Q = [[1, 0], [0, 0]]` e `c = [0, −2]`, con
entrambe le variabili limitate inferiormente a zero e illimitate superiormente.
Aumentare `x₂` non costa nulla e rende −2 per unità all'infinito. L'esito è
`Illimitato`.

**Indefinita.** Prova `Q = [[1, 2], [2, 1]]` con Minimizza. I suoi autovalori
sono 3 e −1: una sella. Il problema viene rifiutato prima di risolvere, perché
questa capability non si pronuncia su obiettivi non convessi.

## Importazione ed esportazione

Ogni problema di questa pagina può essere salvato con **Esporta JSON** e
riaperto con **Importa JSON**. È lo stesso documento accettato dalla riga di
comando e dall'API locale: un problema costruito qui può quindi essere
riprodotto in uno script senza riscriverlo.
