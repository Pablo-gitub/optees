# Features Roadmap

---

## Feature: Import JSON Problem

**Stato:** pianificato  
**Priorità:** alta  
**Complessità:** media

### Descrizione

Aggiungere un pulsante **"Import JSON"** nella barra del titolo della scheda LP
(lato opposto rispetto alla label "Linear Programming (LP)"), che permette
all'utente di selezionare un file `.json` dal filesystem e popolare
automaticamente tutte le sezioni dell'interfaccia: variabili, bounds, funzione
obiettivo e vincoli.

---

### Schema JSON (contratto pubblico)

Il formato importabile/esportabile è volutamente leggibile a occhio nudo.
`null` rappresenta l'infinito (bound illimitato).

```json
{
  "version": "1",
  "variables": [
    { "name": "X1", "label": "chairs/day", "lb": 0,    "ub": null },
    { "name": "X2", "label": "tables/day", "lb": 0,    "ub": null }
  ],
  "objective": {
    "sense": "max",
    "coefficients": [30, 50],
    "offset": 0
  },
  "constraints": [
    { "coefficients": [2, 4], "relation": "<=", "rhs": 80 },
    { "coefficients": [1, 1], "relation": "<=", "rhs": 30 }
  ]
}
```

**Regole di validazione:**

| Campo | Tipo | Note |
|---|---|---|
| `version` | `"1"` | obbligatorio, per futura compatibilità |
| `variables[].name` | string | opzionale, generato automaticamente se assente |
| `variables[].label` | string | opzionale, default `""` |
| `variables[].lb` | number \| null | null = −∞ |
| `variables[].ub` | number \| null | null = +∞ |
| `objective.sense` | `"min"` \| `"max"` | obbligatorio |
| `objective.coefficients` | array[number] | lunghezza deve coincidere con `variables` |
| `objective.offset` | number | opzionale, default `0` |
| `constraints[].coefficients` | array[number] | stessa lunghezza di `variables` |
| `constraints[].relation` | `"<="` \| `"="` \| `">="` | obbligatorio |
| `constraints[].rhs` | number | obbligatorio |

---

### Passi di implementazione

#### Step 1 — Parser e validatore JSON (domain / utility layer)

**File da creare:** `src/optees/utility/lp_json_io.py`

Funzione pubblica:

```python
def lp_model_from_dict(data: dict) -> LPModel:
    """
    Converte un dict conforme allo schema v1 in un LPModel immutabile.
    Solleva ValueError con messaggio leggibile se il dict è malformato.
    """
```

Logica interna:
- Verificare `data["version"] == "1"`
- Costruire la lista di `Variable` da `data["variables"]`
  - `name` → `Variable.name`; se assente usare `f"X{i+1}"`
  - `label` → `Variable.label`
  - `lb`, `ub` → `Bounds(lb, ub)` (None rimane None)
- Costruire `Objective`:
  - `sense` → `ObjectiveSense.from_str()`
  - `coefficients` → tupla di float (None se mancante per quella posizione)
  - `offset` → float, default 0
- Costruire la lista di `Constraint`:
  - `coefficients` → tupla
  - `relation` → `Relation.from_symbol()`
  - `rhs` → float
- Restituire `LPModel(variables=..., objective=..., constraints=...)`

**File da creare:** `tests/utility/test_lp_json_io.py`

Test da coprire:
- Modello completo: parse corretto di tutti i campi
- `lb`/`ub` null → `None` in `Bounds`
- `version` mancante o errata → `ValueError`
- `coefficients` di lunghezza sbagliata → `ValueError`
- `relation` non riconosciuta → `ValueError`
- Variabili senza `name`/`label` → default corretti

---

#### Step 2 — Metodo `load_model` sul controller

**File da modificare:** `src/optees/presentation/controllers/lp_controller.py`

Aggiungere il metodo pubblico:

```python
def load_model(self, model: LPModel) -> None:
    """
    Sostituisce l'intero modello corrente.
    Emette tutti i segnali bulk necessari ad aggiornare la UI.
    """
    self._model = model
    self.variables_changed.emit(self.variables())
    self.bounds_changed.emit(...)
    self.objective_changed.emit(self.objective())
    self.constraints_changed.emit(self.constraints())
```

Questo metodo riusa i segnali già esistenti, quindi la UI si aggiorna
esattamente come farebbe con le modifiche manuali dell'utente.

---

#### Step 3 — Slot di import nella LPView

**File da modificare:** `src/optees/presentation/views/lp_view/lp_view.py`

Aggiungere il metodo:

```python
def _on_import_json(self) -> None:
    path, _ = QFileDialog.getOpenFileName(
        self,
        caption=S.t("lp.import.dialog_title"),
        filter="JSON files (*.json);;All files (*)",
    )
    if not path:
        return
    try:
        import json
        from optees.utility.lp_json_io import lp_model_from_dict
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        model = lp_model_from_dict(data)
        self._controller.load_model(model)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        QMessageBox.warning(
            self,
            S.t("lp.import.error_title"),
            S.t("lp.import.error_body", detail=str(exc)),
        )
```

---

#### Step 4 — Pulsante nell'IntroSection (UI)

**File da modificare:** `src/optees/presentation/views/lp_view/intro_section.py`

Il titolo della sezione è nella header row del widget `Section` (classe base).
Il pulsante "Import JSON" va aggiunto sul lato destro di quella stessa riga.

Due opzioni architetturali:

**Opzione A (più semplice):** aggiungere un `header_action` slot nella classe
`Section` base — un widget opzionale che viene inserito a destra del titolo.

```python
# In Section.__init__
self._header_right = QHBoxLayout()
hdr.addLayout(self._header_right)          # hdr = la riga con il titolo

# Metodo pubblico
def set_header_action(self, widget: QWidget) -> None:
    self._header_right.addWidget(widget)
```

Poi in `IntroSection.__init__`:

```python
self.btn_import = QPushButton()
self.btn_import.setObjectName("btnImportJson")
self.btn_import.setIcon(QIcon.fromTheme("document-open"))  # o icona custom
self.set_header_action(self.btn_import)

# Segnale
import_clicked = Signal()
self.btn_import.clicked.connect(self.import_clicked.emit)
```

**Opzione B (nessuna modifica a Section):** aggiungere il pulsante direttamente
all'interno di `IntroSection`, nella riga dei bottoni esistenti (`btns`
layout), con `insertWidget(0, self.btn_import)` prima dello `addStretch`.

> **Raccomandazione:** Opzione A, perché mantiene la separazione tra layout
> strutturale (`Section`) e contenuto (`IntroSection`) e permette il riuso su
> altre sezioni in futuro.

---

#### Step 5 — Cablaggio segnali in LPView

**File da modificare:** `src/optees/presentation/views/lp_view/lp_view.py`

Collegare il segnale del pulsante allo slot di import:

```python
# In LPView.set_controller() o in __init__ dopo aver creato intro
self.intro.import_clicked.connect(self._on_import_json)
```

---

#### Step 6 — Stringhe i18n

**File da modificare:**
- `src/optees/assets/i18n/en.json`
- `src/optees/assets/i18n/it.json`

Chiavi da aggiungere sotto `"lp"`:

```json
"import": {
  "button":       "Import JSON",
  "dialog_title": "Open LP problem",
  "error_title":  "Import error",
  "error_body":   "Could not load the file:\n{detail}"
}
```

```json
"import": {
  "button":       "Importa JSON",
  "dialog_title": "Apri problema LP",
  "error_title":  "Errore di importazione",
  "error_body":   "Impossibile caricare il file:\n{detail}"
}
```

---

#### Step 7 — (Bonus) Completare l'export JSON nella solution view

La solution view ha già il pulsante "Export JSON" e il metodo `_export_json()`
come stub. Conviene completarlo in questa stessa iterazione, perché il formato
esportato sarà identico allo schema importabile — chiudendo il ciclo
import → modifica → solve → export.

**File da modificare:**
`src/optees/presentation/views/lp_solution_view/lp_solution_view.py`

```python
def _export_json(self) -> None:
    from optees.utility.lp_json_io import lp_model_to_dict
    import json
    path, _ = QFileDialog.getSaveFileName(
        self, filter="JSON files (*.json)"
    )
    if path:
        data = lp_model_to_dict(self._model)   # nuovo helper in lp_json_io
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
```

---

### Dipendenze tra step

```
Step 1 (parser)
    └── Step 2 (controller.load_model)
            └── Step 5 (cablaggio segnali)
Step 3 (slot _on_import_json)   ──────────────────┐
Step 4 (pulsante UI)  ──────────────────────────── Step 5
Step 6 (i18n)  ── può procedere in parallelo a tutti gli altri
Step 7 (export) ── dipende solo da Step 1 (helper lp_model_to_dict)
```

---

### Stima effort

| Step | Effort stimato |
|---|---|
| 1 — Parser + test | 2–3 h |
| 2 — `load_model` sul controller | 30 min |
| 3 — Slot `_on_import_json` | 30 min |
| 4 — Pulsante UI (Opzione A) | 1 h |
| 5 — Cablaggio segnali | 15 min |
| 6 — Stringhe i18n | 15 min |
| 7 — Export JSON (bonus) | 45 min |
| **Totale** | **≈ 5–6 h** |
