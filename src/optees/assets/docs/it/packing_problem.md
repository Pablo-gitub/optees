# Descrizione matematica del packing 3D ortogonale

Il packing 3D in singolo container determina se e dove unita' rettangolari e indivisibili possono essere posizionate in un container rettangolare. Optees implementa il **packing ortogonale**: ogni spigolo resta parallelo a un asse del container, quindi le rotazioni sono multiple di 90 gradi e il posizionamento diagonale e' escluso.

## Decisioni

Per ogni unita' `i`, il modello decide:

- se viene caricata, con una variabile binaria `s_i`;
- uno degli orientamenti ammessi;
- le coordinate continue `(x_i, y_i, z_i)` del vertice inferiore;
- per ogni coppia di unita', quale relazione spaziale ne impedisce la sovrapposizione.

Con dimensioni orientate `(l_i, w_i, h_i)` e dimensioni del container `(L, W, H)`, il contenimento richiede:

```text
0 <= x_i <= L - l_i
0 <= y_i <= W - w_i
0 <= z_i <= H - h_i
```

Per due unita' caricate `i` e `j`, deve valere almeno una disgiunzione: `i` si trova a sinistra/destra, davanti/dietro oppure sotto/sopra `j`. Il MILP linearizza queste alternative con variabili binarie e costanti big-M valide ricavate dalle dimensioni del container.

## Obiettivo e capacita'

In modalita' opzionale l'obiettivo e':

```text
massimizza somma(valore_i * s_i)
```

Una risorsa aggiuntiva `r` genera:

```text
somma(consumo_ir * s_i) <= capacita_r
```

Con tutti i colli obbligatori, ogni `s_i = 1`. Se la richiesta esatta e' inammissibile, Optees esegue un secondo calcolo opzionale, chiaramente distinto, per identificare il miglior carico recuperabile.

## Modalita' di gravita'

**Nessuna gravita'** mostra le coordinate restituite dal MILP. **Gravita' semplice** applica un post-processing geometrico deterministico: mantiene fissi X/Y e orientamento e abbassa ogni collo finche' raggiunge il pavimento o il collo piu' alto sottostante con impronta orizzontale sovrapposta. Poiche' i colli si muovono solo verso il basso e conservano la propria impronta, contenimento e non sovrapposizione restano validi.

La gravita' semplice e' paragonabile al compattamento verso il basso di un gioco a blocchi. Qualsiasi sovrapposizione positiva delle impronte viene considerata un appoggio. Non impone area minima di supporto, bilanciamento, baricentro, resistenza dei materiali o limiti di portata.

## Perche' il problema e' difficile

Il numero di decisioni di non sovrapposizione cresce quadraticamente con le unita', mentre orientamenti e selezioni sono discreti. Il tempo di soluzione esatta puo' quindi crescere rapidamente. Una soluzione ammissibile raggiunta al limite di tempo e' utile, ma non prova l'ottimalita'; il gap MIP indica il margine residuo quando disponibile.

## Perimetro geometrico

Il modello implementato assume parallelepipedi, un container rettangolare, posizionamento allineato agli assi e nessuna simulazione fisica. Stabilita', baricentro, superficie di appoggio, ordine di scarico, cilindri e rotazioni libere sono vincoli distinti e non vengono approssimati implicitamente.
