# MILP Feature Implementation Plan

Questo documento descrive come implementare la feature MILP in Optees mantenendo
coerenza con l'implementazione LP gia' presente: stessa architettura a layer,
stesso stile di UI a sezioni, stesso flusso formulazione -> solve -> solution
view, ma con le differenze matematiche e algoritmiche richieste dai problemi
mixed-integer.

## Stato attuale

### Gia' presente

- Solver utility: `src/optees/utility/milp_utils.py`
  - API pubblica: `solve_milp(problem, *, time_limit=None)`.
  - Backend OR-Tools CP-SAT per modelli puramente interi/binari con dati
    integer-like.
  - Backend OR-Tools CBC per modelli misti o con coefficienti non interi.
  - Output: `(status, objective, x_dict, extras)`.
- View MILP placeholder: `src/optees/presentation/views/milp_view.py`.
- Test solver base: `tests/utility/test_milp_utils.py`.
- Test E2E MIPLIB: `tests/utility/test_miplib_milp_e2e.py`.
- Parser `.solu` MIPLIB: `src/optees/utility/data_adapters/miplib_solu.py`.
- Dataset MIPLIB gia' scaricato sotto `tests/data/miplib2017/`:
  - `tests/data/miplib2017/miplib2017-v31.solu`
  - `tests/data/miplib2017/instances/`
  - inventario attuale: 242 istanze totali, 2 `.mps` e 240 `.mps.gz`.

### Mancante

- Domain model MILP esplicito.
- `MILPController`, `SolveMILPUseCase`, `MILPSolverPort` e adapter applicativo.
- UI completa di formulazione MILP.
- UI completa di visualizzazione soluzione MILP.
- Import/export MILP JSON.
- Adapter MPS riusabile fuori dai test.
- Test presentation per flusso MILP.
- Gestione esplicita dello stato "Feasible incumbent" quando il solver trova
  una soluzione ammissibile ma non prova l'ottimalita' entro il time limit.

## Modello matematico

La MILP generalizza la LP aggiungendo vincoli di integrita' su un sottoinsieme
delle variabili:

```text
optimize    c^T x + alpha
subject to  A_ub x <= b_ub
            A_eq x  = b_eq
            l <= x <= u
            x_j in R        per variabili continue
            x_j in Z        per variabili intere
            x_j in {0, 1}   per variabili binarie
```

La regione ammissibile non e' piu' solo un politopo continuo: e' l'intersezione
del politopo della rilassata LP con una griglia discreta sulle variabili intere.
Di conseguenza l'ottimo non si trova semplicemente su un vertice della rilassata;
il solver deve esplorare o escludere combinazioni discrete.

Algoritmicamente Optees dovrebbe presentare la MILP come:

- rilassata LP: modello ottenuto ignorando temporaneamente l'integrita';
- incumbent: migliore soluzione intera trovata;
- best bound: limite teorico corrente sul valore ottimo;
- MIP gap: distanza relativa tra incumbent e best bound;
- stato finale: optimal, feasible, infeasible, unbounded, not solved.

## Architettura proposta

### Domain

Creare un modello MILP dedicato senza rompere il dominio LP esistente:

```text
src/optees/domain/models/milp/milp_model.py
src/optees/domain/entities/milp/variable.py
src/optees/domain/value_objects/milp/integrality.py
```

La variabile MILP dovrebbe contenere:

```python
name: str
label: str
bounds: Bounds
integrality: CONTINUOUS | INTEGER | BINARY
```

Il resto del modello puo' rimanere simile a LP: objective, constraints,
coefficienti, offset. Questa duplicazione limitata e' accettabile nella prima
iterazione per non introdurre un refactor prematuro di LP. In una fase successiva
si puo' valutare un modello condiviso `LinearModel`.

### Application

Seguire il pattern LP:

```text
src/optees/application/ports/milp_solver_port.py
src/optees/application/usecases/solve_milp_usecase.py
src/optees/data/adapters/milp/milp_solver_adapter.py
```

Il use case converte `MILPModel` nel dizionario canonico gia' accettato da
`solve_milp`:

```python
problem = {
    "sense": "min" | "max",
    "c": [...],
    "A_ub": [[...], ...] | None,
    "b_ub": [...] | None,
    "A_eq": [[...], ...] | None,
    "b_eq": [...] | None,
    "bounds": [(lb, ub), ...],
    "integrality": ["C" | "I" | "B", ...],
    "var_names": [...],
    "obj_offset": 0.0,
}
```

Il risultato dovrebbe normalizzare anche i dati MILP-specifici:

```python
{
    "status": "Optimal" | "Feasible" | "Infeasible" | "Unbounded" | "NotSolved",
    "objective": float | None,
    "values": dict[str, float],
    "extras": {
        "backend": "cp-sat" | "cbc",
        "best_bound": float | None,
        "relative_gap": float | None,
        "wall_time": float | None,
        "nodes": int | None,
        "branches": int | None,
        "conflicts": int | None,
        "message": str | None,
    },
}
```

Prima di costruire la UI completa conviene estendere `milp_utils.py` per
esporre lo stato "Feasible" e l'incumbent quando disponibili. Per MILP e' una
informazione importante: una soluzione buona entro time limit non deve sembrare
uguale a un fallimento.

## UI di formulazione

La pagina MILP dovrebbe riusare la composizione visiva di `LPView`:

```text
IntroSection
VariablesSection
BoundsSection
ObjectiveSection
ObjectiveConstraintsSection
SolverOptionsSection
Optimize button
```

### Intro

Come LP, ma con pulsanti:

- `Esempio`
- `Descrizione problema`
- `Import JSON`
- opzionale: `Import MPS`

L'import MPS e' utile per MIPLIB, ma puo' arrivare dopo l'import JSON per non
mescolare subito UI e parsing di formati scientifici.

### Variabili

Estendere la sezione variabili con una colonna `Tipo`:

```text
Nome | Descrizione | Tipo | Azioni
```

Tipi disponibili:

- continua
- intera
- binaria

Comportamento UI:

- se `Tipo = binaria`, bloccare o normalizzare i bounds a `[0, 1]`;
- se `Tipo = intera`, consentire bounds numerici ma segnalare valori non
  interi come warning;
- se `Tipo = continua`, comportamento identico alla LP.

### Bounds

Si puo' riusare quasi tutto `BoundsSection`, aggiungendo consapevolezza del tipo
variabile:

- binaria: bounds readonly `[0, 1]`;
- intera: campi editabili ma preferibilmente con validatore integer;
- continua: validatore float come LP.

### Obiettivo e vincoli

La UI puo' riusare `ObjectiveSection` e `ObjectiveConstraintsSection`.
Differenze:

- mostrare il tipo variabile accanto a ogni colonna dei coefficienti;
- evidenziare variabili binarie/intere con badge compatto;
- mantenere la stessa gestione di `<=`, `=`, `>=`.

### Opzioni solver

Nuova sezione dedicata:

```text
Backend: Auto | CP-SAT | CBC
Time limit: seconds
MIP gap: percent
Workers: auto / numeric
```

Per la prima iterazione bastano:

- backend `Auto`;
- `time_limit`;
- campo `mip_gap` preparato in UI ma cablato solo quando supportato dal backend.

## UI di visualizzazione soluzione

La solution view MILP dovrebbe partire da `LPSolutionView`, ma non essere una
copia cieca. Le componenti riusabili sono:

- status card;
- tabella variabili;
- pulsanti back/copy/export;
- layout scrollabile.

### Status card MILP

Campi da mostrare:

- stato;
- valore obiettivo;
- backend usato;
- best bound;
- MIP gap;
- tempo;
- nodi/branch/conflicts se disponibili;
- messaggio solver.

Per `Feasible`, la UI deve spiegare che la soluzione e' ammissibile ma non
provata ottima. Per `Optimal`, deve mostrare gap zero o entro tolleranza.

### Tabella variabili

Colonne consigliate:

```text
Variabile | Label | Tipo | Bound inferiore | Bound superiore | Valore
```

Per variabili intere e binarie:

- arrotondare visualmente vicino all'intero se lo scarto numerico e' sotto
  tolleranza;
- mostrare un warning se `abs(x - round(x))` supera la tolleranza.

### Grafici

Regola pragmatica:

- 2 variabili: mostrare rilassata LP, punti interi ammissibili e ottimo MILP;
- 3 variabili: opzionale, solo se gia' robusto nella LP;
- piu' di 3 variabili: nessun grafico, mostrare tabella e diagnostiche.

Per MILP il grafico piu' didattico e' 2D:

- area continua = rilassata LP;
- punti discreti = soluzioni intere ammissibili;
- marker evidenziato = incumbent/ottimo.

## Import/export MILP JSON

Schema consigliato, allineato a LP JSON ma con `integrality`:

```json
{
  "version": "1",
  "variables": [
    { "name": "x1", "label": "open plant A", "lb": 0, "ub": 1, "integrality": "B" },
    { "name": "x2", "label": "units shipped", "lb": 0, "ub": null, "integrality": "I" },
    { "name": "x3", "label": "continuous flow", "lb": 0, "ub": null, "integrality": "C" }
  ],
  "objective": {
    "sense": "min",
    "coefficients": [1000, 5, 1.2],
    "offset": 0
  },
  "constraints": [
    { "coefficients": [1, 0, 0], "relation": "<=", "rhs": 1 },
    { "coefficients": [0, 1, 1], "relation": ">=", "rhs": 10 }
  ],
  "solver": {
    "time_limit": 10.0,
    "mip_gap": 0.01
  }
}
```

Regole:

- `integrality = "B"` implica bounds `[0, 1]`;
- `integrality = "I"` richiede valori interi per la soluzione;
- `integrality = "C"` o assente indica variabile continua;
- `null` continua a rappresentare bound illimitato.

## MPS e MIPLIB

I dataset MIPLIB sono gia' presenti nel repository:

```text
tests/data/miplib2017/
  miplib2017-v31.solu
  instances/
    2 file .mps
    240 file .mps.gz
```

Il test `tests/utility/test_miplib_milp_e2e.py` legge MPS tramite PuLP e poi
converte verso il dizionario canonico MILP. Questo codice oggi vive nel test;
per renderlo feature applicativa va estratto in un adapter:

```text
src/optees/utility/data_adapters/miplib_mps.py
```

oppure, meglio a regime:

```text
src/optees/data/adapters/milp/mps_adapter.py
```

Dipendenze operative:

- `ortools` per risolvere MILP;
- `pulp` per leggere MPS, almeno nella prima iterazione;
- `pytest-timeout` per test E2E MIPLIB stabili.

I dataset non vanno inclusi nel bundle dell'app. Restano materiale di test.
Per la UI e gli esempi bastano 2-3 JSON piccoli sotto `examples/`.

## Test plan

### Utility

- `tests/utility/test_milp_utils.py`
  - assignment binario;
  - knapsack;
  - infeasible;
  - modello mixed con una variabile continua per forzare CBC;
  - time limit con stato `Feasible` quando supportato.

### Adapter

- `tests/utility/test_milp_json_io.py`
  - parse schema JSON;
  - default integrality;
  - bounds binari normalizzati;
  - errori su coefficienti di lunghezza errata;
  - round trip.
- `tests/utility/test_mps_adapter.py`
  - caricare una istanza piccola MIPLIB;
  - verificare dimensioni, bounds, integrality e objective sense.

### Application

- `tests/application/usecases/test_solve_milp_usecase.py`
  - mapping domain -> canonical dict;
  - mapping result -> DTO UI;
  - propagazione extras.

### Presentation

Seguire lo stile dei test LP:

- apertura pagina MILP;
- aggiunta variabili continue/intere/binarie;
- import JSON;
- solve happy path;
- stato infeasible;
- visualizzazione `Feasible` con best bound/gap;
- export JSON/CSV se implementato.

### MIPLIB E2E

Il test esiste gia'. Va mantenuto come smoke test opzionale:

- skip se `pulp` manca;
- skip se `ortools` manca;
- cap sul numero di istanze;
- time limit breve;
- confronto con `.solu` solo quando lo status e' `Optimal`.

## Ordine consigliato

1. Estendere `milp_utils.py` per esporre backend, incumbent, best bound e gap.
2. Aggiungere domain model MILP minimale.
3. Aggiungere port, adapter e use case MILP.
4. Aggiungere `milp_json_io.py` e 2 esempi JSON piccoli.
5. Estrarre adapter MPS dal test MIPLIB.
6. Implementare `MILPView` copiando la struttura di LP ma aggiungendo tipo
   variabile e opzioni solver.
7. Implementare `MILPSolutionView` riusando i componenti LP dove sensato.
8. Aggiungere pagine `Esempio` e `Descrizione problema` MILP.
9. Coprire con test utility, application e presentation.
10. Aggiornare `docs/DATASETS.md` e `docs/TESTING.md` con MILP/MIPLIB.

## Decisioni aperte

- Se mantenere un domain MILP dedicato o introdurre un modello lineare
  condiviso LP/MILP.
- Se supportare import MPS gia' nella prima release MILP o partire da JSON.
- Se mostrare soluzioni `Feasible` come stato separato nel contratto pubblico.
- Se aggiungere un solver commerciale opzionale in futuro (Gurobi/SCIP/CPLEX)
  tramite adapter, senza cambiare la UI.
