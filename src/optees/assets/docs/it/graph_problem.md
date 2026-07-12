# Cammini Minimi Con Dijkstra

## Modello

Sia dato un grafo con vertici `V` e archi pesati `E`. Date una sorgente `s` e una
destinazione `t`, scegli un cammino `P` che minimizza il peso totale:

```text
min sum(w_e per e in P)
```

I pesi possono rappresentare distanza, tempo, denaro, energia o qualsiasi
quantita' additiva. In questo flusso devono essere finiti e non negativi.

## Perche' L'Algoritmo Funziona

Dijkstra mantiene una distanza provvisoria per ogni vertice. All'inizio solo
`s` ha distanza zero. A ogni passo rende definitivo il vertice non definitivo
con la minima distanza provvisoria e rilassa i suoi archi uscenti.

Quando un vertice viene reso definitivo, la sua distanza e' finale. Ogni cammino
concorrente dovrebbe passare da un vertice non definitivo con distanza
provvisoria non minore, poi aggiungere un arco di peso non negativo. Questo
argomento fallisce con archi negativi, che Optees rifiuta in questa schermata.

## Interpretazione Del Risultato

La soluzione mostra il percorso selezionato, il suo peso totale e l'ordine dei
vertici resi definitivi. Se la destinazione e' **Non raggiungibile**, l'algoritmo
ha esaurito tutti i vertici raggiungibili dalla sorgente: non e' un errore del
solver.

## Perimetro

Questo primo flusso supporta grafi finiti diretti o non diretti e pesi non
negativi. Archi negativi, cammini tra tutte le coppie, alberi ricoprenti, flussi,
matching e TSP sono flussi futuri separati.
