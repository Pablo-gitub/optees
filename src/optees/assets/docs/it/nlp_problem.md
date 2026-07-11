# Programmazione Nonlineare Continua

Il primo flusso NLP di Optees risolve problemi continui della forma:

```text
minimizza o massimizza   f(x)
soggetto a               l_i <= x_i <= u_i
                          x in R^n
```

Il vettore decisionale `x` e' continuo, come in LP, ma l'obiettivo `f(x)` puo'
contenere potenze, prodotti, radici, funzioni trigonometriche, logaritmi o
esponenziali. Questa prima versione non ha vincoli non lineari generali; usa i
bounds per definire un box.

## Punto iniziale e ottimo locale

Un LP ha una geometria convessa speciale e un solver esatto puo' dimostrare un
ottimo finito. Un paesaggio non lineare puo' invece avere molti punti stazionari,
valli e picchi. I metodi numerici partono dal punto iniziale e usano informazioni
locali: due punti iniziali validi possono convergere a minimi locali diversi.

Per questo il risultato e' **Converged**, non **Optimal**. `Converged` significa
che il metodo ha soddisfatto una regola di arresto vicino al candidato. `Iteration
limit` indica un arresto al budget configurato; `Failed` indica che non e' stato
prodotto un candidato finito affidabile. Nessuno di questi stati dimostra un
ottimo globale.

## Metodi disponibili

- **BFGS**: approssima la curvatura ed e' pensato qui per problemi lisci senza
  bounds.
- **Nelder-Mead**: modifica un simplesso tramite riflessione, espansione,
  contrazione e shrink; e' una base utile quando le derivate sono scomode.
- **L-BFGS-B**: e' il metodo consapevole dei bounds e deve essere scelto quando
  almeno una variabile ha un limite inferiore o superiore.

## Cosa avviene quando premi Ottimizza

1. Optees valida nomi, bounds, punto iniziale, metodo ed espressione.
2. Valuta la formula nel punto iniziale; il valore deve essere uno scalare finito.
3. Per una massimizzazione passa `-f(x)` al backend e riconverte il risultato.
4. SciPy `minimize` esegue il metodo selezionato.
5. La pagina soluzione riporta candidato locale, valore originale, metodo,
   messaggio, iterazioni, valutazioni e traccia dell'obiettivo.

La traccia descrive il percorso di quella esecuzione; non prova che il metodo
abbia esplorato tutte le altre regioni dello spazio di ricerca.

## Linguaggio sicuro dell'obiettivo

Optees non esegue mai il testo come Python arbitrario. Sono ammessi variabili
dichiarate, numeri finiti, aritmetica, potenze e `abs`, `sin`, `cos`, `tan`,
`exp`, `log`, `sqrt` con un argomento. Un JSON importato e una formula manuale
seguono la stessa validazione.

Vincoli non lineari generali, ottimizzazione globale, min-max non lineare,
minimi quadrati e programmazione quadratica restano fuori da questa prima
versione e sono tracciati in `docs/NLP_FEATURE_PLAN.md`.
