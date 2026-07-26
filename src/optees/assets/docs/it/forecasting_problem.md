# Previsione di serie storiche

## Cosa stai davvero chiedendo

La previsione stima i **valori futuri** di una grandezza a partire dal suo
**passato ordinato**. Optees lavora su una singola serie univariata: una colonna
di timestamp e un target numerico, campionati a frequenza regolare.

Non e' lo stesso problema della regressione lineare. La regressione assume che
le righe siano indipendenti e le divide a caso. Una serie storica e' l'opposto:
l'ordine porta l'informazione e il futuro non deve mai servire a prevedere il
passato. Optees tiene apposta separate le due capability.

## Ordine temporale e leakage

La regola piu' importante e' che un modello puo' imparare solo da dati esistenti
**prima** dell'istante che prevede. Usare una qualsiasi osservazione futura in
fase di fit o valutazione — anche indirettamente, mescolando le righe o mediando
sull'intera serie — si chiama **leakage**. Il leakage produce metriche
ottime in laboratorio che crollano nella realta'.

Ogni valutazione di Optees e' *cronologica*: ogni finestra di addestramento
finisce strettamente prima della finestra su cui viene misurata. Nulla viene
mescolato.

## Il vocabolario

- **Osservazione** — un timestamp e un valore finito.
- **Origine della previsione** — l'ultima osservazione che il modello puo'
  vedere.
- **Orizzonte** — quanti periodi futuri chiedi dopo l'origine.
- **Lunghezza stagione** — quante osservazioni formano un ciclo completo (12 per
  dati mensili con ciclo annuale, 7 per dati giornalieri con ciclo settimanale).
- **Trend** — una deriva persistente verso l'alto o il basso.
- **Stagionalita'** — un pattern che si ripete a ogni lunghezza di stagione.
- **Residuo** — reale meno stimato; cio' che il modello non ha spiegato.

## Come ogni metodo calcola una previsione

Notazione: la serie di addestramento e' `y[1], y[2], ..., y[T]`, dove `T` e'
l'origine della previsione (l'ultimo periodo osservato). Una previsione a `h`
passi si scrive `yhat[T+h]` e `m` e' la lunghezza della stagione.

### Naive

```
yhat[T+h] = y[T]        per ogni h = 1, 2, 3, ...
```

Ogni valore futuro e' uguale all'ultimo valore osservato. Porta avanti il
livello attuale e assume nessun trend e nessuna stagione. E' esatto quando la
serie e' piatta.

### Naive stagionale

```
yhat[T+h] = y[T + h - m * (floor((h - 1) / m) + 1)]
```

Ogni previsione ripete il valore nella posizione corrispondente dell'ultima
stagione completa. Con dati mensili e `m = 12`, il prossimo gennaio e' uguale
allo scorso gennaio. Richiede almeno due stagioni complete di storia.

### Holt-Winters (additivo)

Tre componenti vengono aggiornate a ogni passo con pesi di smoothing
`alpha, beta, gamma` in `[0, 1]`:

```
livello   l[t] = alpha*(y[t] - s[t-m]) + (1 - alpha)*(l[t-1] + b[t-1])
trend     b[t] = beta *(l[t] - l[t-1]) + (1 - beta )*b[t-1]
stagione  s[t] = gamma*(y[t] - l[t-1] - b[t-1]) + (1 - gamma)*s[t-m]
previsione yhat[T+h] = l[T] + h*b[T] + s[T + h - m*(floor((h-1)/m) + 1)]
```

Il **livello** indica dove si trova ora la serie, il **trend** quanto
velocemente si muove e i termini **stagionali** gli scarti ripetuti che si
sommano sopra. Un peso piu' grande reagisce piu' in fretta ai dati recenti; un
peso piu' piccolo e' piu' liscio. Optees stima `alpha, beta, gamma` in modo
deterministico tramite lo stimatore `ExponentialSmoothing` di statsmodels (in
questa versione solo trend e stagione additivi).

## Scegliere un metodo

Optees offre tre metodi deterministici. Un metodo piu' complesso **non** e'
automaticamente migliore.

- **Naive** ripete l'ultimo valore. E' la baseline onesta per una serie senza
  trend e senza stagione stabile. Se un modello piu' sofisticato non batte
  naive, non sta aiutando.
- **Naive stagionale** ripete il valore di una stagione fa. Quando domina un
  ciclo fisso (afflusso settimanale, domanda mensile) e' molto difficile da
  battere.
- **Holt-Winters (additivo)** stima livello, trend additivo e stagionalita'
  additiva. Usalo solo quando trend e ciclo stagionale sono davvero presenti; su
  una serie piatta o puramente stagionale puo' fare *peggio* delle baseline
  perche' stima parametri che non servono.

La metrica **MASE** misura l'errore rispetto a una baseline naive: sotto 1
significa che hai battuto naive, sopra 1 che hai fatto peggio.

## Valutare onestamente

- **Holdout** riserva gli ultimi periodi come unica finestra di test e vi misura
  la previsione.
- **Rolling origin** ripete quel test su piu' finestre mobili, dando una stima
  piu' stabile sulle serie corte.
- **Nessuna** salta la valutazione e produce solo la previsione futura.

Sulle coppie valutate di valori `reale` e `previsto`, le metriche sono:

```
MAE  = mean(|reale - previsto|)                  errore medio, stessa unita' di y
RMSE = sqrt(mean((reale - previsto)^2))           penalizza di piu' gli errori grandi
MAPE = 100 * mean(|(reale - previsto) / reale|)   errore percentuale; indefinito se qualche reale = 0
MASE = MAE / mean(|y[t] - y[t-m]|)                errore relativo a un passo naive (m = 1, o la lunghezza stagione)
```

`MASE < 1` significa che hai battuto la baseline naive; `MASE > 1` che hai fatto
peggio.

Le metriche riportate sono ricalcolate in modo **indipendente** dalle previsioni
e osservazioni pubbliche, non prese sulla fiducia dal solver. Il MAPE resta
**indefinito** quando un valore reale e' zero (non ci si puo' dividere): Optees
lo dichiara invece di inventare un numero.

## L'incertezza non e' una garanzia

Un intervallo di previsione descrive un range con semantica di copertura
documentata. E' **specifico del metodo**: quando un metodo non puo' giustificare
un intervallo, Optees lo omette invece di disegnare una banda rassicurante ma
priva di senso. Un intervallo stima l'incertezza, non e' mai una promessa.

## La previsione non e' causalita'

Una previsione dice "se il pattern passato continua, questo e' il valore
probabile". **Non** spiega il *perche'* e non autorizza affermazioni causali
("se facciamo X, allora Y"). Rotture strutturali — un nuovo concorrente, un
cambio di prezzo, una pandemia — possono invalidare qualsiasi modello addestrato
prima di esse.

## Limiti noti

- **Storia insufficiente**: con troppo pochi punti la valutazione puo' essere
  non disponibile e le metriche restituiscono uno stato esplicito "non
  disponibile".
- **Outlier e rotture strutturali**: un singolo shock puo' dominare una serie
  corta; guarda il grafico dei residui.
- **Periodi mancanti**: i buchi irregolari vengono rifiutati se non e' impostata
  una politica esplicita. Optees non li riempie mai in silenzio.
- **Nessuna garanzia di produzione**: sono baseline didattiche e deterministiche.
  Superare i controlli integrati verifica le proprieta' registrate; non e' una
  prova di accuratezza nel mondo reale.
