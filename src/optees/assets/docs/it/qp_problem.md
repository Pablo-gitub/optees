# Programmazione Quadratica Convessa

## Che cosa risolve questo metodo

Un programma quadratico mantiene lineari i vincoli ma lascia curvare
l'obiettivo. Questo singolo cambiamento copre un'ampia famiglia di domande
reali che la programmazione lineare non riesce a esprimere: minimizzare il
rischio, minimizzare l'errore quadratico, minimizzare lo scostamento da un
target oppure lisciare un piano in modo che periodi consecutivi non oscillino
in modo brusco.

Optees scrive il problema come

```
minimizza   f(x) = ½ xᵀ Q x + cᵀ x + α
soggetto a  A x  (≤, =, ≥)  b
            l ≤ x ≤ u
```

dove `x` è il vettore delle variabili decisionali continue, `Q` una matrice
quadrata simmetrica, `c` un vettore e `α` una costante.

## Perché l'obiettivo porta un ½

`Q` viene letta come **Hessiana** dell'obiettivo, cioè come la matrice delle
sue derivate seconde. Con questa convenzione le derivate restano pulite:

- il gradiente è `∇f(x) = Q x + c`;
- l'Hessiana è `∇²f(x) = Q`.

Il prezzo di derivate pulite è il ½ esplicito nella formula. Un elemento
diagonale `Qᵢᵢ` contribuisce quindi con `½ Qᵢᵢ xᵢ²`, mentre una coppia
simmetrica fuori diagonale `Qᵢⱼ = Qⱼᵢ` contribuisce complessivamente con
`Qᵢⱼ xᵢ xⱼ`, perché viene conteggiata due volte.

Se vuoi il termine `3 x₁²`, inserisci quindi `Q₁₁ = 6`. Se vuoi il termine
misto `2 x₁ x₂`, inserisci `Q₁₂ = Q₂₁ = 1`.

## Simmetria

Solo la parte simmetrica di `Q` può influenzare il valore dell'obiettivo:
`xᵀ Q x` e `xᵀ Qᵀ x` sono lo stesso numero. Optees richiede comunque che la
matrice inviata sia simmetrica entro una tolleranza stretta e non modifica mai
in silenzio la matrice fornita. Rendere esplicito il cambiamento è proprio il
punto: una matrice che non intendevi scrivere è un errore di modellazione che
vale la pena vedere, non un dettaglio di arrotondamento da assorbire.

Nell'editor desktop ogni cella viene rispecchiata nella posizione trasposta
mentre scrivi, quindi una matrice inserita a mano è simmetrica per costruzione.

## Convessa, concava e tutto ciò che viene rifiutato

Gli **autovalori** di `Q` descrivono la curvatura dell'obiettivo in ogni
direzione.

- Autovalori tutti nulli o positivi: `Q` è *semidefinita positiva*. La
  superficie è una conca e ogni minimo locale è il minimo globale. È il caso
  che Optees risolve quando il verso è **minimizza**.
- Autovalori tutti nulli o negativi: `Q` è *semidefinita negativa*. La
  superficie è una cupola, immagine speculare della precedente, e Optees la
  risolve quando il verso è **massimizza**.
- Segni misti: `Q` è *indefinita*. La superficie è una sella, curva verso
  l'alto in una direzione e verso il basso in un'altra, e possono esistere
  molti ottimi locali senza un modo affidabile per stabilire quale sia il
  migliore.

Optees rifiuta il caso indefinito prima di risolvere, anziché restituire un
numero di cui non può rispondere. Un rifiuto su cui puoi agire è più utile di
una risposta di cui non ti puoi fidare.

## Ammissibile e ottimo

Sono due domande distinte e restano distinte anche nella schermata dei
risultati.

- **Ammissibile** chiede se un punto soddisfa tutti i vincoli e tutti i limiti.
  L'insieme di questi punti è la regione ammissibile.
- **Ottimo** chiede se, tra i punti ammissibili, quello ha il miglior valore
  dell'obiettivo.

Un problema può essere ammissibile ma illimitato: l'obiettivo migliora
indefinitamente all'interno della regione ammissibile e non esiste un ottimo
finito. Può essere non ammissibile, senza alcun punto che soddisfi tutto
contemporaneamente. E un'esecuzione fermata da un limite di iterazioni o di
tempo può conservare un candidato ammissibile mai dimostrato ottimo. Optees
riporta ciascuno di questi come esito a sé, invece di ridurli a "risolto" e
"non risolto".

## Duali e condizioni KKT

Quando il backend li fornisce, ogni vincolo e ogni limite riceve un
**moltiplicatore duale**. Leggilo come un prezzo: di quanto cambierebbe
l'obiettivo per una variazione unitaria di quel termine noto o di quel limite.
Un moltiplicatore nullo indica che il vincolo al momento non ti sta limitando.

Le **condizioni KKT** sono il test del primo ordine per l'ottimalità nei
problemi vincolati. Combinano la stazionarietà (il gradiente dell'obiettivo è
bilanciato dai vincoli attivi), la complementarità (un vincolo con scarto ha
moltiplicatore nullo) e le condizioni di segno sui duali. Per un problema
convesso soddisfarle è sufficiente per l'ottimalità: ed è esattamente per
questo che vale la pena insistere sulla convessità.

## Validazione indipendente

Optees non si fida della parola del backend. Dopo l'esecuzione il candidato
viene ricontrollato rispetto al problema originale: forma del vettore, limiti,
ogni riga di vincolo, l'obiettivo ricalcolato da `Q`, `c` e `α` e, quando i
moltiplicatori sono completi, le condizioni KKT.

Il rapporto dichiara onestamente che cosa ha stabilito e che cosa no. Se i
duali mancavano, la verifica KKT viene riportata come non disponibile anziché
data per scontata. Superare questi controlli conferma le proprietà registrate:
non è una seconda dimostrazione di ottimalità globale e non dice nulla sul
fatto che la tua formulazione corrisponda alla domanda che volevi davvero
porre.

## Limiti di questa versione

- Variabili e vincoli sono continui; gli interi arriveranno con una capability
  successiva.
- Fino a 500 variabili e 1000 vincoli.
- In questa versione dello schema la matrice è densa.
- OSQP è l'unico backend, quindi il suo comportamento numerico è quello che
  ottieni. Optees non sostituisce in silenzio un altro solver.
