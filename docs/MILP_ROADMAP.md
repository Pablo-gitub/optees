# MILP Roadmap

Questo documento fotografa lo stato della feature MILP e separa cio' che e'
gia' implementato da cio' che resta da completare.

## Fatto

- [x] Modello di dominio MILP:
  - `MILPVariable`;
  - `MILPModel`;
  - `MILPSolution`;
  - `Integrality` con variabili continue, intere e binarie/booleane.
- [x] Regola matematica per variabili binarie:
  - una variabile binaria e' sempre `x in {0, 1}`;
  - nel codice viene normalizzata a bounds `[0, 1]`.
- [x] Application layer:
  - `MILPSolverPort`;
  - `SolveMILPUseCase`;
  - `MILPSolverAdapter`.
- [x] Solver MILP:
  - backend OR-Tools CP-SAT/CBC;
  - stato `Feasible` separato da `NotSolved`;
  - extras con backend, best bound e gap relativo quando disponibili;
  - supporto `time_limit` e `mip_gap`.
- [x] Import/export JSON MILP:
  - schema con `variables[].integrality`;
  - opzioni solver opzionali;
  - esempio `examples/milp_assignment_2x2.json`.
- [x] Prima UI di formulazione MILP:
  - variabili continue/intere/binarie;
  - bounds;
  - obiettivo;
  - vincoli;
  - opzioni solver;
  - import JSON;
  - pulsanti informativi.
- [x] Flusso solve dalla GUI:
  - composizione controller/use case/adapter;
  - navigazione verso pagina risultati;
  - riuso temporaneo della solution view LP.
- [x] Pagine informative:
  - `Esempio`;
  - `Descrizione problema`;
  - esempi su variabili booleane, assignment, apertura impianto e scarti produttivi a scaglioni.
- [x] Test:
  - utility solver;
  - JSON;
  - use case;
  - flusso presentation MILP.

## Parzialmente fatto

- [ ] Solution view MILP dedicata.

  Oggi la pagina risultati riusa `LPSolutionView`. Funziona per stato, valore
  obiettivo, tabella base e grafico, ma non mostra ancora in modo esplicito:
  tipo variabile, integrality residual, best bound, MIP gap, nodi, branch,
  conflicts e messaggi solver MILP.

- [ ] Visualizzazione grafica MILP.

  La vista attuale eredita la rappresentazione LP. Per MILP serve una grafica
  didattica specifica: rilassata LP, punti interi ammissibili e incumbent/ottimo.

- [ ] Dataset scientifici MIPLIB come feature applicativa.

  I dataset e il test E2E sono presenti, ma l'adapter MPS vive ancora nel test.
  Va estratto in un adapter riusabile prima di esporre import MPS nella GUI.

## Da fare

- [ ] `MILPSolutionView` dedicata:
  - status card con `Optimal` vs `Feasible`;
  - backend;
  - best bound;
  - MIP gap;
  - tempo;
  - nodi/branch/conflicts se disponibili;
  - tabella con tipo variabile e bounds.
- [ ] Wizard per modelli a soglie:
  - costo fisso di attivazione;
  - variabile semi-continua;
  - lotto minimo;
  - costo a scaglioni/piecewise lineare;
  - vincoli either-or.
- [ ] Import MPS:
  - estrarre adapter MPS dal test MIPLIB;
  - validare bounds, integrality e objective sense;
  - aggiungere import opzionale nella GUI.
- [ ] Test presentation aggiuntivi:
  - import JSON dalla GUI;
  - infeasible MILP;
  - stato `Feasible` con gap;
  - navigazione pagine info MILP.
- [ ] Documentazione utente:
  - schema JSON MILP completo;
  - esempi pronti da copiare;
  - note sui limiti dei solver open source.

## Soglie e variabili booleane

La MILP e' lo strumento giusto quando una variabile cambia regime oltre una
soglia, ma la GUI attuale non genera ancora automaticamente le variabili
ausiliarie. Per ora l'utente puo' modellare manualmente questi casi usando:

```text
0 <= x <= M y
y in {0, 1}
```

oppure dividendo la variabile in segmenti:

```text
x = x_low + x_high
0 <= x_low <= soglia
0 <= x_high <= M y
y in {0, 1}
```

La roadmap corretta e' aggiungere un wizard che crei queste variabili e vincoli
in modo guidato, lasciando comunque visibile il modello lineare generato.
