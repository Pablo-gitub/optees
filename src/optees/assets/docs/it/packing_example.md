# Packing 3D in singolo container: esempio svolto

Un magazzino deve caricare un container con dimensioni interne utili **10 x 8 x 6**. Sono disponibili tre tipi di colli indivisibili:

| Collo | Dimensioni | Quantita' | Valore | Rotazione |
|---|---:|---:|---:|---|
| Parte macchina | 6 x 4 x 3 | 1 | 12 | Mantieni verticale |
| Scatola forniture | 4 x 4 x 2 | 2 | 6 | Qualsiasi ortogonale |
| Cassa lunga | 8 x 2 x 2 | 1 | 8 | Ruota attorno a Z |

Il container ha anche un peso massimo di **30**. I consumi unitari sono rispettivamente 16, 6 e 8.

## Inserimento del modello

1. Inserisci le tre dimensioni interne del container.
2. Aggiungi una capacita' chiamata `peso` con limite `30`.
3. Aggiungi una riga per ogni tipo di collo. La quantita' genera unita' indivisibili distinte.
4. Scegli la politica di rotazione. Optees considera solo rotazioni allineate agli assi e multiple di 90 gradi.
5. Scegli **Massimizza valore caricato** se e' ammesso escludere colli, oppure **Richiedi tutti i colli** per verificare il carico completo.
6. Mantieni **Gravita' semplice** per abbassare ogni collo fino al primo appoggio geometrico; scegli **Nessuna gravita'** per osservare le coordinate restituite direttamente dal MILP.

## Lettura della soluzione

Ogni unita' caricata riceve coordinate `(x, y, z)`, dimensioni orientate e un codice di orientamento. Le coordinate identificano il suo vertice inferiore-sinistro-posteriore. Ogni parallelepipedo resta nel container e ogni coppia di colli e' separata su almeno un asse.

Se il carico completo e' impossibile, Optees lo indica come **inammissibile** e calcola separatamente un recupero ammissibile di valore massimo. Il recupero non rende ammissibile la richiesta originale con tutti i colli obbligatori.

## JSON equivalente

Il formato usa `problem_type: packing`, `variant: single_container_3d`, `gravity_mode: simple`, un oggetto `container`, l'array `items` e le `solver_options`. Il pulsante informativo accanto all'importazione riassume i campi richiesti.
