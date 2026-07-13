# Esempio: classificazione di approvazione

Supponi che un'organizzazione abbia domande passate. Ogni riga storica registra
due feature numeriche:

- un punteggio del richiedente;
- un rapporto debito/reddito;

e l'esito noto: `no` oppure `si`.

La domanda non e' "quanto diventera' grande un numero?" ma "quale fra due
classi e' piu' plausibile per una nuova osservazione?" Questo e' un problema
di **classificazione binaria**.

## Piccolo dataset didattico

Crea due colonne feature chiamate `punteggio, rapporto_debito`, usa `approvata`
come nome del target e inserisci una tabella iniziale bilanciata come questa:

| punteggio | rapporto_debito | approvata |
|---:|---:|:---|
| 38 | 0.78 | no |
| 44 | 0.70 | no |
| 51 | 0.64 | no |
| 57 | 0.55 | no |
| 68 | 0.42 | si |
| 74 | 0.35 | si |
| 81 | 0.28 | si |
| 88 | 0.19 | si |

Mantieni inizialmente seed e quota test predefiniti. Optees stratifica la
divisione: entrambe le classi sono quindi presenti nelle partizioni training e
test lasciate fuori. Le feature vengono standardizzate usando solo le righe
training; poi la regressione logistica locale viene addestrata e le metriche
test sono calcolate su righe mai usate per adattare il modello.

## Come leggere il risultato

La seconda classe in ordine alfabetico e' trattata come positiva. Il risultato
mostra la sua probabilita' per ogni riga; a partire dal 50% quella classe viene
prevista. In questo esempio un coefficiente positivo per `punteggio` tende ad
aumentare la probabilita' di `si`, mentre un coefficiente positivo per
`rapporto_debito` la aumenta solo se i dati sostengono quella relazione.

Usa la matrice di confusione per distinguere falsi positivi e falsi negativi.
Quale errore sia piu' grave e' una scelta del dominio, non qualcosa che
l'accuracy possa decidere automaticamente. Il grafico 2D, quando appare, e'
una visualizzazione didattica del confine decisionale al 50%, non una prova che
il confine sia affidabile fuori dai dati osservati.

## Limite importante

Questo esempio compatto e' volutamente troppo piccolo per un sistema reale di
approvazione. Non usarlo per decisioni che incidono sulle persone. Un impiego
reale richiede dati rappresentativi, controllo delle feature, analisi di
equita' ed errori, validazione oltre una sola divisione e supervisione umana
adeguata.
