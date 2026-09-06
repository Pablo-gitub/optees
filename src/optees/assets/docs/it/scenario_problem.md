# Ottimizzazione Min-Max / Max-Min

Questo flusso sceglie un solo insieme di variabili decisionali e lo valuta in
ogni scenario fornito esplicitamente. Non assegna probabilita' e non ottimizza
un risultato medio.

## Perdita min-max

Usa **minimizza la perdita massima** quando i valori rappresentano costi,
perdite o penalita'. Optees minimizza il valore piu' alto, ottenendo un limite
superiore che nessuno scenario elencato supera.

## Rendimento max-min

Usa **massimizza il rendimento minimo** quando i valori rappresentano
rendimenti, benefici o guadagni. Optees massimizza il valore piu' basso,
ottenendo un limite inferiore raggiunto da ogni scenario elencato.

Ogni scenario e' lineare nelle stesse variabili ordinate. Limiti delle
variabili e vincoli condivisi definiscono le decisioni ammissibili. Un termine
lineare condiviso facoltativo viene aggiunto a ogni scenario. I problemi
continui usano una riduzione LP; variabili intere o binarie selezionano la
corrispondente riduzione MILP.

Il risultato riporta il valore garantito, la valutazione di ogni scenario e
tutti gli scenari attivi. Optees ricostruisce questi valori dal problema
originale prima di dichiarare verificato il risultato.

Questa e' ottimizzazione robusta su un elenco finito, non previsione
probabilistica. La garanzia copre solo scenari e vincoli forniti.
