# Come funziona la regressione lineare

## La domanda di modellazione

La regressione apprende una relazione numerica da esempi. Per ogni osservazione
`i` registriamo valori delle feature `x_i` e un target continuo `y_i`. Esempi
sono prezzo, consumo energetico, tempo di consegna o domanda.

Il primo flusso Optees accetta solo dati numerici finiti. Testo categorico,
valori mancanti e assunzioni di previsione temporale sono fuori da questo primo
ambito educativo.

## Modello lineare

Con `p` feature il modello prevede:

```text
y_hat_i = beta_0 + beta_1 x_i1 + ... + beta_p x_ip
```

`beta_0` e' l'intercetta e gli altri coefficienti descrivono il contributo
lineare stimato di ogni feature mantenendo fisse le altre. Non sono
automaticamente effetti causali.

## Obiettivo OLS

Sulle osservazioni di training, OLS sceglie coefficienti che minimizzano:

```text
sum_i (y_i - y_hat_i)^2
```

Il quadrato fa pesare maggiormente residui grandi e fornisce una soluzione
numerica comoda. Optees risolve direttamente questo problema di algebra
lineare; non e' un ottimizzatore iterativo opaco.

## Obiettivo Ridge

Ridge modifica l'obiettivo di training in:

```text
sum_i (y_i - y_hat_i)^2 + alpha * sum_j beta_j^2
```

L'`alpha` positivo scoraggia coefficienti delle feature molto grandi.
L'intercetta e' esclusa dalla penalita'. Ridge puo' essere utile quando le
feature sono fortemente correlate o quando la tabella training e' piccola
rispetto al numero di feature, ma puo' anche introdurre bias.

## Valutazione onesta

Prima dell'addestramento, Optees usa il seed selezionato per dividere le righe
in partizioni training e test. Le righe test non sono usate per scegliere i
coefficienti.

- **MAE**: residuo assoluto medio, nell'unita' del target.
- **MSE**: residuo quadratico medio, che enfatizza errori grandi.
- **RMSE**: radice di MSE, ancora nell'unita' del target.
- **R-quadrato**: miglioramento rispetto alla previsione della media test. Puo'
  essere negativo e non e' disponibile quando il target e' costante.

Confronta i metodi solo con stesso dataset e stessa divisione. Per lavoro
serio usa piu' dati e valutazioni ripetute o cross-validation, ispeziona la
qualita' dei dati e considera se i dati di utilizzo avranno la stessa
distribuzione.
