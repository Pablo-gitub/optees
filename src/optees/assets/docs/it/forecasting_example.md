# Esempi di previsione

Ogni esempio usa un payload valido e committato e il risultato verificato dai
test di riferimento di Optees. Incolla un payload in **Importa JSON** per
riprodurlo, oppure digita le osservazioni nella tabella.

## 1. Domanda stabile — Naive

Una serie piatta senza trend ne' stagione. L'ultimo valore si ripete, quindi la
baseline naive e' esatta.

| Timestamp | Valore |
|---|---:|
| 2026-01-01 | 5 |
| 2026-01-02 | 5 |
| 2026-01-03 | 5 |
| 2026-01-04 | 5 |

```json
{
  "version": "1",
  "problem_type": "univariate_forecasting",
  "target_name": "constant_demand",
  "frequency": "daily",
  "horizon": 2,
  "method": "naive",
  "observations": [
    {"timestamp": "2026-01-01", "value": 5},
    {"timestamp": "2026-01-02", "value": 5},
    {"timestamp": "2026-01-03", "value": 5},
    {"timestamp": "2026-01-04", "value": 5}
  ],
  "evaluation": {"strategy": "holdout", "holdout_size": 1}
}
```

**Risultato verificato:** previsione `[5, 5]`; MAE, RMSE e MAPE tutti `0`;
validazione indipendente `verified`. Quando la serie e' piatta, nessun metodo
piu' sofisticato puo' fare meglio.

## 2. Domanda in crescita — Naive come baseline

Un trend lineare pulito di `+2` al giorno. Naive puo' solo ripetere l'ultimo
valore, quindi resta sistematicamente indietro rispetto a un trend. E' il caso
in cui un metodo con trend deve guadagnarsi il posto.

| Timestamp | Valore |
|---|---:|
| 2026-01-01 | 2 |
| 2026-01-02 | 4 |
| 2026-01-03 | 6 |
| 2026-01-04 | 8 |
| 2026-01-05 | 10 |

```json
{
  "version": "1",
  "problem_type": "univariate_forecasting",
  "target_name": "trend_demand",
  "frequency": "daily",
  "horizon": 2,
  "method": "naive",
  "observations": [
    {"timestamp": "2026-01-01", "value": 2},
    {"timestamp": "2026-01-02", "value": 4},
    {"timestamp": "2026-01-03", "value": 6},
    {"timestamp": "2026-01-04", "value": 8},
    {"timestamp": "2026-01-05", "value": 10}
  ],
  "evaluation": {"strategy": "holdout", "holdout_size": 2}
}
```

**Risultato verificato:** previsione `[10, 10]`; MAE `3`, RMSE `3.16`, MAPE
`32.5%`, **MASE `1.5`**. Un MASE sopra `1` conferma che qui naive fa peggio della
baseline interna — un segnale per provare Holt-Winters, che puo' seguire il
trend.

## 3. Domanda stagionale — Naive stagionale

Un ciclo ripetuto di tre mesi `10, 20, 30`. Con `season_length = 3`, il naive
stagionale copia il valore di una stagione fa e riproduce il ciclo esattamente.

| Timestamp | Valore | | Timestamp | Valore |
|---|---:|---|---|---:|
| 2025-01-01 | 10 | | 2025-06-01 | 30 |
| 2025-02-01 | 20 | | 2025-07-01 | 10 |
| 2025-03-01 | 30 | | 2025-08-01 | 20 |
| 2025-04-01 | 10 | | 2025-09-01 | 30 |
| 2025-05-01 | 20 | | | |

```json
{
  "version": "1",
  "problem_type": "univariate_forecasting",
  "target_name": "seasonal_demand",
  "frequency": "monthly",
  "horizon": 3,
  "method": "seasonal_naive",
  "season_length": 3,
  "observations": [
    {"timestamp": "2025-01-01", "value": 10},
    {"timestamp": "2025-02-01", "value": 20},
    {"timestamp": "2025-03-01", "value": 30},
    {"timestamp": "2025-04-01", "value": 10},
    {"timestamp": "2025-05-01", "value": 20},
    {"timestamp": "2025-06-01", "value": 30},
    {"timestamp": "2025-07-01", "value": 10},
    {"timestamp": "2025-08-01", "value": 20},
    {"timestamp": "2025-09-01", "value": 30}
  ],
  "evaluation": {"strategy": "holdout", "holdout_size": 3}
}
```

**Risultato verificato:** previsione `[10, 20, 30]`; MAE, RMSE e MAPE tutti `0`;
validazione `verified`. Quando domina un ciclo fisso, il naive stagionale e' una
baseline molto forte.

## Leggere i casi limite

- **Storia troppo corta**: con pochi punti la valutazione puo' essere non
  disponibile e le metriche restituiscono `non disponibile` invece di un valore
  a caso.
- **Un valore reale pari a zero**: il MAPE resta **indefinito** perche'
  dividerebbe per zero; MAE e RMSE sono comunque riportati.
- **Valori futuri reali**: la tabella della soluzione mostra le righe future
  senza valore reale. Una cella vuota significa "non ancora osservato", mai `0`.
