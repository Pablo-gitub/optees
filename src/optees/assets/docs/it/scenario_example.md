# Esempio: allocazione robusta della produzione

Un produttore deve distribuire dieci unita' fra i prodotti `x1` e `x2`. Le
condizioni di mercato sono incerte, quindi la stessa allocazione viene valutata
in tre scenari di costo.

| Variabile | Limite inferiore | Vincolo |
| --- | ---: | --- |
| `x1` | 0 | `x1 + x2 = 10` |
| `x2` | 0 | `x1 + x2 = 10` |

| Scenario | Espressione del costo |
| --- | --- |
| Regime 1 | `2 x1 - x2 + 5` |
| Regime 2 | `-x1 + 3 x2 + 2` |
| Regime 3 | `x1 + x2 - 4` |

Seleziona **Minimizza la perdita massima**. Optees trova l'allocazione
ammissibile il cui costo piu' alto fra gli scenari e' il piu' piccolo possibile.
Gli scenari attivi spiegano quali regimi impediscono di migliorare la garanzia.

Per esplorare la semantica opposta, seleziona **Massimizza il rendimento
minimo** e inserisci coefficienti che rappresentano rendimenti. Non riutilizzare
i coefficienti di perdita senza cambiarne il significato: i due orientamenti
rispondono a domande differenti.

Usa **Esporta JSON** per esaminare il documento versionato e importalo di nuovo
per verificare che l'ordine di variabili e scenari venga preservato.
