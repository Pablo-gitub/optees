# Come funziona la classificazione binaria

## La domanda di modellazione

La classificazione binaria apprende da esempi con una di due classi note. Ogni
osservazione ha feature numeriche `x_i` e un target categorico `y_i`, per
esempio `no`/`si`, `negativo`/`positivo` o `non_spam`/`spam`.

Il primo flusso Optees accetta volutamente solo due classi testuali non vuote e
feature numeriche finite. Non esegue classificazione del testo, classificazione
multiclasse, imputazione di valori mancanti, selezione automatica delle feature
o inferenza causale.

## Punteggio logistico e probabilita'

Per il vettore di feature standardizzato `z_i`, la regressione logistica forma
un punteggio lineare:

```text
s_i = beta_0 + beta_1 z_i1 + ... + beta_p z_ip
```

e lo trasforma nella probabilita' della classe positiva con la sigmoide:

```text
p_i = 1 / (1 + exp(-s_i))
```

Optees assegna la classe positiva quando `p_i >= 0.5`; altrimenti assegna la
classe negativa. La classe positiva e' la seconda dopo l'ordinamento
alfabetico. Una probabilita' e' l'output del modello condizionato a dati e
assunzioni: non e' una garanzia sul singolo caso.

## Obiettivo di addestramento

Solo sulle righe training, l'implementazione minimizza la perdita logistica
regolarizzata:

```text
mean_i[-y_i log(p_i) - (1-y_i) log(1-p_i)] + 0.5 * alpha * sum_j beta_j^2
```

Qui le classi sono codificate come `0` e `1`. Il termine L2 controllato da
`alpha` scoraggia coefficienti delle feature molto grandi; l'intercetta non e'
penalizzata. Optees usa gradient descent full-batch deterministico. Learning
rate e limite di iterazioni controllano questo processo numerico. La
convergenza indica che e' stato raggiunto il criterio sul gradiente, non che il
modello sia universalmente corretto.

## Valutazione onesta

Prima dell'addestramento, le righe sono divise per classe in modo stratificato
usando il seed configurato. Media e scala delle feature sono calcolate **solo
sulla partizione training**, poi applicate alle righe test. Questo evita che
informazioni test entrino nell'adattamento del modello.

- **Accuracy**: quota complessiva di previsioni corrette.
- **Precision**: quota di previsioni positive che erano davvero positive.
- **Recall**: quota di classi positive reali trovate.
- **F1**: equilibrio armonico fra precision e recall.

La matrice di confusione esplicita i quattro esiti: vero negativo, falso
positivo, falso negativo e vero positivo. La sola accuracy puo' essere
fuorviante, soprattutto quando una classe e' rara. Confronta training e test,
ispeziona entrambi gli errori e usa validazioni ripetute per lavori seri.
