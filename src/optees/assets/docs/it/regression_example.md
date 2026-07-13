# Esempio di regressione lineare

## Obiettivo

Stimare un prezzo continuo di una casa da caratteristiche misurabili. E' un
problema di apprendimento supervisionato: le osservazioni storiche contengono
sia gli input sia il prezzo osservato.

| Superficie | Stanze | Prezzo |
|---:|---:|---:|
| 40 | 1 | 100 |
| 50 | 2 | 130 |
| 60 | 2 | 150 |
| 70 | 3 | 180 |
| 80 | 3 | 200 |
| 90 | 4 | 235 |

Nella vista di formulazione inserisci `superficie, stanze` come feature e
`prezzo` come target. Ogni riga della tabella e' un'osservazione storica.

## Divisione training e test

Con quota test `0.33` e seed `42`, Optees lascia fuori in modo deterministico
una parte della tabella. L'addestramento usa solo le righe rimanenti. MAE, MSE,
RMSE e R-quadrato test sono calcolati sulle righe lasciate fuori.

Mantenere fisso il seed permette a uno studente di riprodurre la stessa
divisione. Cambiarlo cambia le osservazioni lasciate fuori e quindi puo'
cambiare le metriche.

## Parti da OLS

Inizia con i **Minimi Quadrati Ordinari (OLS)**. Il metodo apprende un'equazione:

```text
prezzo_previsto = intercetta
                + beta_superficie * superficie
                + beta_stanze * stanze
```

OLS sceglie i coefficienti che minimizzano la somma dei residui quadratici sui
dati di training. Un residuo e' `prezzo reale - prezzo previsto`.

## Quando provare Ridge

Scegli la **regressione Ridge** quando piu' feature trasmettono informazioni
sovrapposte, ad esempio superficie e numero di stanze. Ridge aggiunge una
penalita' positiva controllata da `alpha` per ridurre i coefficienti delle
feature. L'intercetta non e' penalizzata. Confronta le metriche test con OLS
usando la stessa divisione prima di decidere se la regolarizzazione ha aiutato.

## Leggere il risultato

La soluzione mostra coefficienti appresi, metriche di entrambe le partizioni e
ogni valore reale/previsto/residuo. Con una sola feature mostra anche la retta
stimata e distingue i punti training da quelli test.

> Un errore basso su questa piccola tabella non prova che la relazione sia
> causale o che si generalizzi a un mercato futuro. E' evidenza solo per i dati
> e per la divisione scelta.
