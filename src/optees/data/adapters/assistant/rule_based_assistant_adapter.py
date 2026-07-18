from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

from optees.domain.entities.assistant import AssistantAnalysis
from optees.utility.classification_json_io import classification_model_from_dict
from optees.utility.knapsack_json_io import knapsack_problem_from_dict
from optees.utility.lp_json_io import lp_model_from_dict
from optees.utility.milp_json_io import milp_model_from_dict
from optees.utility.regression_json_io import regression_model_from_dict


_FAMILY_LP = "lp"
_FAMILY_MILP = "milp"
_FAMILY_KNAPSACK = "knapsack"
_FAMILY_NLP = "nlp"
_FAMILY_REGRESSION = "regression"
_FAMILY_CLASSIFICATION = "classification"
_FAMILY_GRAPH = "graph"
_FAMILY_SCHEDULING = "scheduling"
_FAMILY_ROBUST = "robust"
_FAMILY_UNKNOWN = "unknown"


@dataclass(frozen=True)
class _KeywordRule:
    family: str
    weight: int
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class _LinearDraft:
    data: dict[str, Any]
    warnings: tuple[str, ...] = ()


class RuleBasedAssistantAdapter:
    """Deterministic local assistant for the first modeling-assistant phase.

    This adapter deliberately uses transparent rules instead of an LLM. It is
    useful for solver recommendation, conservative JSON drafting, and regression
    tests because the same prompt always produces the same explanation.
    """

    _rules = (
        _KeywordRule(
            _FAMILY_KNAPSACK,
            5,
            (
                "knapsack",
                "zaino",
                "backpack",
                "bag",
                "capacita",
                "capacity",
                "capienza",
                "peso",
                "weight",
                "size",
                "dimensione",
                "oggetto",
                "oggetti",
                "item",
                "items",
                "object",
                "objects",
                "supplies",
                "scorte",
                "box",
                "scatola",
                "usefulness",
                "utilita",
                "package",
                "packages",
                "pacco",
                "pacchi",
            ),
        ),
        _KeywordRule(
            _FAMILY_MILP,
            4,
            (
                "milp",
                "mixed integer",
                "mixed-integer",
                "intero",
                "interi",
                "integer",
                "binaria",
                "binary",
                "boolean",
                "bool",
                "0/1",
                "scaglione",
                "scaglioni",
                "soglia",
                "threshold",
                "fixed cost",
                "setup",
                "yes or no",
                "si o no",
                "whether",
                "warehouse",
                "warehouses",
                "magazzino",
                "magazzini",
                "open warehouse",
                "aprire",
            ),
        ),
        _KeywordRule(
            _FAMILY_SCHEDULING,
            4,
            (
                "scheduling",
                "schedul",
                "macchine",
                "machines",
                "machine",
                "job",
                "jobs",
                "turni",
                "turno",
                "sequenza",
                "sequence",
                "makespan",
                "deadline",
                "ritardo",
                "lateness",
            ),
        ),
        _KeywordRule(
            _FAMILY_ROBUST,
            4,
            (
                "robust",
                "robusto",
                "incertezza",
                "uncertainty",
                "scenario",
                "scenari",
                "regret",
                "rimpianto",
                "worst case",
                "caso peggiore",
                "newsboy",
                "newsvendor",
                "revenue management",
                "demand",
                "domanda",
                "newspaper",
                "newspapers",
                "giornale",
                "giornali",
                "hotel",
                "rooms",
                "camere",
            ),
        ),
        _KeywordRule(
            _FAMILY_REGRESSION,
            5,
            (
                "linear regression",
                "regressione lineare",
                "ridge regression",
                "regressione ridge",
                "ordinary least squares",
                "minimi quadrati ordinari",
                "ols",
            ),
        ),
        _KeywordRule(
            _FAMILY_CLASSIFICATION,
            5,
            (
                "binary classification",
                "classificazione binaria",
                "logistic regression",
                "regressione logistica",
                "binary classifier",
                "classificatore binario",
                "class label",
                "etichetta di classe",
                "spam detection",
                "rilevamento spam",
                "fraud detection",
                "rilevamento frodi",
            ),
        ),
        _KeywordRule(
            _FAMILY_GRAPH,
            5,
            (
                "shortest path",
                "shortest-path",
                "cammino minimo",
                "percorso minimo",
                "percorso piu breve",
                "graph",
                "grafo",
                "grafi",
                "network",
                "rete",
                "rete stradale",
                "node",
                "nodo",
                "nodi",
                "vertex",
                "vertices",
                "vertice",
                "vertici",
                "edge",
                "edges",
                "arco",
                "archi",
                "route",
                "percorso",
                "tragitto",
                "itinerario",
                "road",
                "roads",
                "strada",
                "strade",
                "street",
                "streets",
                "dijkstra",
            ),
        ),
        _KeywordRule(
            _FAMILY_NLP,
            4,
            (
                "nonlinear",
                "non lineare",
                "non-lineare",
                "quadratic",
                "quadratico",
                "curva",
                "curve",
                "derivata",
                "derivative",
                "prodotto tra variabili",
                "product of variables",
                "least squares",
                "minimi quadrati",
                "rosenbrock",
            ),
        ),
        _KeywordRule(
            _FAMILY_LP,
            3,
            (
                "lp",
                "linear programming",
                "programmazione lineare",
                "vincoli lineari",
                "linear constraints",
                "variabili continue",
                "continuous variables",
                "funzione obiettivo",
                "objective function",
                "tchebycheff",
                "chebyshev",
                "goal programming",
                "continuous",
                "continue",
                "decimal quantities",
                "quantita decimali",
                "labor hours",
                "ore di lavoro",
                "raw material",
                "materia prima",
                "profit",
                "profitto",
                "cost",
                "costo",
                "produce",
                "produrre",
                "production",
                "produzione",
                "product",
                "prodotto",
            ),
        ),
    )

    def analyze(self, prompt: str, language: str = "en") -> AssistantAnalysis:
        original = prompt or ""
        normalized = _normalize(original)
        language = _supported_language(language)
        if not normalized.strip():
            return AssistantAnalysis(
                family=_FAMILY_UNKNOWN,
                variant="unknown",
                confidence=0.0,
                implemented=False,
                reasons=(_msg(language, "empty_prompt"),),
                missing_information=(_msg(language, "problem_description"),),
                language=language,
            )

        family, score = self._classify(normalized)
        variant = self._variant_for(family, normalized)
        implemented = family in {
            _FAMILY_LP,
            _FAMILY_MILP,
            _FAMILY_KNAPSACK,
            _FAMILY_NLP,
            _FAMILY_REGRESSION,
            _FAMILY_CLASSIFICATION,
            _FAMILY_GRAPH,
        }
        load_target = (
            family
            if implemented and family in {_FAMILY_LP, _FAMILY_MILP, _FAMILY_KNAPSACK}
            else None
        )
        if family == _FAMILY_KNAPSACK:
            load_target = "knapsack"

        reasons = self._reasons_for(family, variant, normalized, language)
        missing: list[str] = []
        model_json: dict[str, Any] | None = None
        validation_errors: list[str] = []

        if family == _FAMILY_KNAPSACK:
            model_json, missing = self._draft_knapsack(normalized, language)
            if model_json is not None:
                model_json["variant"] = variant
                if variant == "multi_dimensional":
                    model_json.setdefault("domain", "zero_one")
        elif family == _FAMILY_LP:
            draft, missing = self._draft_lp(normalized, language)
            model_json = draft.data if draft else None
            if draft is not None:
                missing.extend(draft.warnings)
        elif family == _FAMILY_MILP:
            draft, missing = self._draft_milp(normalized, language)
            model_json = draft.data if draft else None
            if draft is not None:
                missing.extend(draft.warnings)
        elif family == _FAMILY_NLP:
            missing.append(_msg(language, "nlp_drafting_deferred"))
        elif family == _FAMILY_REGRESSION:
            model_json, missing = self._draft_regression(original, language)
            if model_json is not None:
                load_target = _FAMILY_REGRESSION
        elif family == _FAMILY_CLASSIFICATION:
            model_json, missing = self._draft_classification(original, language)
            if model_json is not None:
                load_target = _FAMILY_CLASSIFICATION
        elif family == _FAMILY_GRAPH:
            missing.append(_msg(language, "graph_drafting_deferred"))
        elif family in {_FAMILY_SCHEDULING, _FAMILY_ROBUST}:
            missing.append(_msg(language, "planned_family"))
        else:
            missing.append(_msg(language, "problem_family"))

        if model_json is not None:
            validation_errors = self._validate_model_json(family, model_json)
            if validation_errors:
                model_json = None
                load_target = None

        confidence = _confidence(score, bool(model_json), family != _FAMILY_UNKNOWN)
        return AssistantAnalysis(
            family=family,
            variant=variant,
            confidence=confidence,
            implemented=implemented,
            load_target=load_target,
            reasons=reasons,
            missing_information=tuple(dict.fromkeys(missing)),
            model_json=model_json,
            validation_errors=tuple(validation_errors),
            language=language,
        )

    def _classify(self, text: str) -> tuple[str, int]:
        scores = {
            _FAMILY_LP: 0,
            _FAMILY_MILP: 0,
            _FAMILY_KNAPSACK: 0,
            _FAMILY_NLP: 0,
            _FAMILY_REGRESSION: 0,
            _FAMILY_CLASSIFICATION: 0,
            _FAMILY_GRAPH: 0,
            _FAMILY_SCHEDULING: 0,
            _FAMILY_ROBUST: 0,
        }
        for rule in self._rules:
            for keyword in rule.keywords:
                if keyword in text:
                    scores[rule.family] += rule.weight

        # A text with item/value/weight/capacity is usually a knapsack model even
        # if the user does not know the name of the algorithm.
        if _has_any(text, ("valore", "value")) and _has_any(
            text,
            ("peso", "weight", "size", "dimensione"),
        ):
            scores[_FAMILY_KNAPSACK] += 8
        if _has_any(text, ("capacita", "capacity", "bag", "zaino", "backpack")) and _has_any(
            text,
            ("oggetto", "item", "object", "objects"),
        ):
            scores[_FAMILY_KNAPSACK] += 6
        if _has_any(text, ("bag", "zaino", "backpack")) and _has_any(
            text,
            ("laptop", "bottle", "phone", "book", "oggetto", "objects", "items"),
        ):
            scores[_FAMILY_KNAPSACK] += 8
        if _has_any(text, ("take", "carry", "portare", "prendere", "filling", "riempiendo")) and _has_any(
            text,
            ("capacity", "capacita", "limit", "limite", "weight", "peso", "volume"),
        ):
            scores[_FAMILY_KNAPSACK] += 6
        if _has_any(text, ("up to", "fino a", "maximum available", "quantita massima")) and _has_any(
            text,
            ("batteries", "batterie", "food", "cibo", "water", "acqua", "supplies", "scorte"),
        ):
            scores[_FAMILY_KNAPSACK] += 7
        if _has_fractional_knapsack_markers(text) and _has_any(
            text,
            (
                "take",
                "prendere",
                "carry",
                "portare",
                "goods",
                "beni",
                "item",
                "oggetto",
                "load",
                "caric",
                "materials",
                "materiali",
            ),
        ):
            scores[_FAMILY_KNAPSACK] += 10

        # Untrained users never say "item/value/weight": they describe the shape
        # of the decision, i.e. picking a subset that fits a single limit
        # ("what do I put in my suitcase", "which projects fit my budget").
        if _has_container_limit_markers(text) and _has_selection_markers(text):
            scores[_FAMILY_KNAPSACK] += 12

        # "Fund a project in full or not at all" is the textbook definition of a
        # 0/1 selection.
        if _has_all_or_nothing_markers(text) and _has_selection_markers(text):
            scores[_FAMILY_KNAPSACK] += 8

        if _has_any(text, ("decimal quantities", "quantita decimali", "continuous", "continue")) and _has_any(
            text,
            ("profit", "profitto", "cost", "costo", "labor", "lavoro", "material", "materia"),
        ):
            scores[_FAMILY_LP] += 9

        # Divisible production quantities do not make a problem fractional
        # knapsack. Products sharing manufacturing resources, with profit per
        # unit and continuous quantities, form a continuous production-mix LP.
        if _has_continuous_production_mix_markers(text):
            scores[_FAMILY_LP] += 14

        # Classification predicts a named outcome rather than a continuous
        # quantity. Requiring a prediction and binary-outcome signal avoids
        # interpreting ordinary yes/no optimization decisions as a dataset task.
        if _has_any(
            text,
            (
                "predict",
                "prediction",
                "classify",
                "classification",
                "prevedere",
                "previsione",
                "classificare",
                "classificazione",
                "tell me if",
                "can the app tell",
                "dirmi se",
                "probabilmente",
                "logistic regression",
                "regressione logistica",
            ),
        ) and _has_any(
            text,
            (
                "binary",
                "binaria",
                "two labels",
                "due classi",
                "yes/no",
                "si/no",
                "approved",
                "approval",
                "approv",
                "accepted",
                "accept",
                "accett",
                "rejected",
                "rifiutat",
                "spam",
                "fraud",
                "frode",
                "churn",
                "renew",
                "rinnov",
                "abbandon",
                "positive",
                "negative",
                "positivo",
                "negativo",
            ),
        ):
            scores[_FAMILY_CLASSIFICATION] += 12

        # Regression is recognized from a prediction/estimation task grounded
        # in previous numerical observations. Requiring both parts avoids
        # mistaking generic forecasts or nonlinear curve fitting for OLS/Ridge.
        if (
            not _has_any(
                text,
                (
                    "classification",
                    "classificazione",
                    "logistic regression",
                    "regressione logistica",
                    "classifier",
                    "classificatore",
                    "nonlinear",
                    "non lineare",
                    "non-lineare",
                    "quadratic",
                    "quadratico",
                    "curva",
                    "curve",
                    "derivata",
                    "derivative",
                ),
            )
            and _has_any(
                text,
                (
                    "predict",
                    "prediction",
                    "forecast",
                    "prevedere",
                    "previsione",
                    "stimare",
                    "estimate",
                    "estimating",
                    "stima",
                    "regression",
                    "regressione",
                    "fit a line",
                    "adattare una retta",
                ),
            )
            and _has_any(
                text,
                (
                    "historical data",
                    "past data",
                    "past months",
                    "previous sales",
                    "training data",
                    "dataset",
                    "data set",
                    "observations",
                    "observation",
                    "records",
                    "record",
                    "samples",
                    "dati storici",
                    "dati di addestramento",
                    "mesi passati",
                    "vendite precedenti",
                    "appartamenti simili",
                    "osservazioni",
                    "campioni",
                    "feature",
                    "features",
                    "target",
                    "prezzo",
                    "price",
                    "sales",
                    "vendite",
                    "rent",
                    "rental",
                    "affitti",
                    "affitto",
                    "consumption",
                    "consumi",
                    "consumo",
                ),
            )
        ):
            scores[_FAMILY_REGRESSION] += 12

        if _has_any(text, ("yes or no", "si o no", "whether", "aprire", "open")) and _has_any(
            text,
            ("warehouse", "warehouses", "magazzino", "magazzini", "ship", "spedire"),
        ):
            scores[_FAMILY_MILP] += 9
        if (
            not _has_fractional_knapsack_markers(text)
            and not _has_all_or_nothing_markers(text)
            and _has_any(
                text,
                (
                    "binary",
                    "binaria",
                    "integer",
                    "intero",
                    "interi",
                    "setup",
                    "fixed setup",
                    "fixed cost",
                    "0/1",
                ),
            )
        ):
            scores[_FAMILY_MILP] += 9

        # A yes/no activation paired with a quantity decision is the classic
        # fixed-charge structure. It must outweigh the plain LP vocabulary
        # ("production", "cost") that such prompts are always full of.
        if _has_yes_no_decision(text) and _has_quantity_decision(text):
            scores[_FAMILY_MILP] += 12

        if _has_any(text, ("uncertain", "incerta", "incerto", "incertezza", "scenario", "scenari")) and _has_any(
            text,
            ("demand", "domanda", "cost", "costi", "choice", "scelta", "decisione"),
        ):
            scores[_FAMILY_ROBUST] += 8
        if _has_any(text, ("newspaper", "newspapers", "giornale", "giornali", "copies", "copie")) and _has_any(
            text,
            ("demand", "domanda", "order", "ordinare", "wasted", "invendute", "sales", "vendite"),
        ):
            scores[_FAMILY_ROBUST] += 9
        if _has_any(text, ("hotel", "rooms", "camere")) and _has_any(
            text,
            ("demand", "domanda", "prices", "prezzi", "sell", "vendere", "venderne"),
        ):
            scores[_FAMILY_ROBUST] += 9

        # Discrete conditions move otherwise-linear models into MILP.
        if _has_conditional_markers(text):
            scores[_FAMILY_MILP] += 5

        objective_part, constraints_part = _split_linear_prompt(text)
        if objective_part and constraints_part:
            scores[_FAMILY_LP] += 8
            if _has_any(
                text,
                (
                    "intero",
                    "interi",
                    "integer",
                    "binaria",
                    "binary",
                    "boolean",
                    "bool",
                    "0/1",
                ),
            ):
                scores[_FAMILY_MILP] += 8

        # "Get from X to Y as fast/cheap as possible" is a shortest-path (graph)
        # problem, even when the user never says "graph", "node" or "edge".
        _speed = ("shortest", "quickest", "quick", "fastest", "fast", "cheapest",
                  "piu breve", "piu corto", "piu economico", "veloc", "rapid")
        _route = ("path", "route", "way", "get from", "go from", "percorso",
                  "tragitto", "cammino", "itinerario", "strada", "strade", "street",
                  "streets", "road", "roads", "arrivare", "andare", "raggiungere")
        if _has_any(text, _speed) and _has_any(text, _route):
            scores[_FAMILY_GRAPH] += 10
        if _has_any(text, ("from ", "da ")) and _has_any(text, ("network", "rete", "node", "nodo", "grafo", "graph", "edges", "archi")):
            scores[_FAMILY_GRAPH] += 6

        best_family = max(
            scores,
            key=lambda f: (scores[f], _priority(f)),
        )
        best_score = scores[best_family]
        if best_score <= 0:
            return _FAMILY_UNKNOWN, 0
        return best_family, best_score

    def _variant_for(self, family: str, text: str) -> str:
        if family == _FAMILY_KNAPSACK:
            if _has_multi_resource_markers(text):
                return "multi_dimensional"
            if _has_fractional_knapsack_markers(text):
                return "fractional"
            if _has_repeatable_markers(text):
                return "unbounded"
            if _has_bounded_markers(text):
                return "bounded"
            return "zero_one"
        if family == _FAMILY_LP:
            if _has_any(text, ("tchebycheff", "chebyshev", "goal programming")):
                return "tchebycheff_goal_programming"
            if _has_any(text, ("min max", "minimax", "max min", "maximin")):
                return "linear_min_max"
            return "standard_lp"
        if family == _FAMILY_MILP:
            if _has_any(text, ("scaglione", "scaglioni", "soglia", "threshold", "piecewise")):
                return "piecewise_threshold"
            if _has_any(text, ("sotto ", "superiore", "altrimenti", "below", "above")):
                return "piecewise_threshold"
            if _has_any(text, ("assignment", "assegn", "matching")):
                return "assignment"
            if _has_any(text, ("scheduling", "macchine", "machines", "makespan")):
                return "scheduling_milp"
            return "standard_milp"
        if family == _FAMILY_NLP:
            if _has_any(text, ("min max", "minimax", "max min", "maximin")):
                return "nonlinear_min_max"
            if _has_any(text, ("least squares", "minimi quadrati")):
                return "least_squares"
            return "standard_nlp"
        if family == _FAMILY_GRAPH:
            return "shortest_path"
        if family == _FAMILY_REGRESSION:
            return "linear_regression"
        if family == _FAMILY_CLASSIFICATION:
            return "binary_logistic_regression"
        if family == _FAMILY_SCHEDULING:
            if _has_any(text, ("macchine parallele", "parallel machines")):
                return "parallel_machines"
            if _has_any(text, ("parallel", "in parallelo")) and _has_any(text, ("machine", "machines", "macchina", "macchine")):
                return "parallel_machines"
            return "scheduling"
        if family == _FAMILY_ROBUST:
            if _has_any(text, ("regret", "rimpianto", "too badly", "troppo male", "best choice", "scelta migliore")):
                return "min_max_regret"
            if _has_any(text, ("newsboy", "newsvendor", "newspaper", "newspapers", "giornale", "giornali", "copies", "copie")):
                return "newsvendor"
            if _has_any(text, ("revenue management", "hotel", "rooms", "camere", "high-paying", "prezzi")):
                return "revenue_management"
            return "robust_optimization"
        return "unknown"

    def _reasons_for(
        self,
        family: str,
        variant: str,
        text: str,
        language: str,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if family == _FAMILY_KNAPSACK:
            reasons.append(_msg(language, "reason_knapsack"))
            if variant != "zero_one":
                reasons.append(_msg(language, f"reason_knapsack_{variant}"))
        elif family == _FAMILY_MILP:
            reasons.append(_msg(language, "reason_milp"))
            if variant == "piecewise_threshold":
                reasons.append(_msg(language, "reason_threshold"))
        elif family == _FAMILY_LP:
            reasons.append(_msg(language, "reason_lp"))
        elif family == _FAMILY_NLP:
            reasons.append(_msg(language, "reason_nlp"))
        elif family == _FAMILY_REGRESSION:
            reasons.append(_msg(language, "reason_regression"))
        elif family == _FAMILY_CLASSIFICATION:
            reasons.append(_msg(language, "reason_classification"))
        elif family == _FAMILY_GRAPH:
            reasons.append(_msg(language, "reason_graph"))
        elif family == _FAMILY_SCHEDULING:
            reasons.append(_msg(language, "reason_scheduling"))
        elif family == _FAMILY_ROBUST:
            reasons.append(_msg(language, "reason_robust"))
        else:
            reasons.append(_msg(language, "reason_unknown"))
        if _has_any(text, ("json", "schema")):
            reasons.append(_msg(language, "reason_json"))
        return tuple(reasons)

    def _draft_knapsack(
        self,
        text: str,
        language: str,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        missing: list[str] = []
        capacity = _extract_knapsack_capacity(text)
        if capacity is None:
            missing.append(_msg(language, "capacity"))

        items = _extract_knapsack_items(text)
        if not items:
            missing.append(_msg(language, "items_with_value_weight"))

        if capacity is None or not items:
            return None, missing

        return (
            {
                "version": "1",
                "problem_type": "knapsack",
                "variant": "zero_one",
                "capacity": capacity,
                "items": items,
            },
            missing,
        )

    def _draft_lp(
        self,
        text: str,
        language: str,
    ) -> tuple[_LinearDraft | None, list[str]]:
        missing: list[str] = []
        draft = _parse_linear_problem(text, include_integrality=False)
        if draft is None:
            missing.extend(
                [
                    _msg(language, "linear_objective"),
                    _msg(language, "linear_constraints"),
                ]
            )
            return None, missing
        return draft, missing

    def _draft_milp(
        self,
        text: str,
        language: str,
    ) -> tuple[_LinearDraft | None, list[str]]:
        missing: list[str] = []
        draft = _parse_linear_problem(text, include_integrality=True)
        if draft is None:
            missing.extend(
                [
                    _msg(language, "linear_objective"),
                    _msg(language, "linear_constraints"),
                ]
            )
            return None, missing
        if not any(v.get("integrality") in {"I", "B"} for v in draft.data["variables"]):
            missing.append(_msg(language, "integrality"))
            return None, missing
        return draft, missing

    def _draft_regression(
        self,
        source: str,
        language: str,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        draft = _parse_supervised_dataset(source, problem_type="regression")
        if draft is None:
            return None, [_msg(language, "supervised_dataset_format")]
        return draft, []

    def _draft_classification(
        self,
        source: str,
        language: str,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        draft = _parse_supervised_dataset(source, problem_type="binary_classification")
        if draft is None:
            return None, [_msg(language, "supervised_dataset_format")]
        return draft, []

    def _validate_model_json(self, family: str, data: dict[str, Any]) -> list[str]:
        try:
            if family == _FAMILY_LP:
                lp_model_from_dict(data)
            elif family == _FAMILY_MILP:
                milp_model_from_dict(data)
            elif family == _FAMILY_KNAPSACK:
                knapsack_problem_from_dict(data)
            elif family == _FAMILY_REGRESSION:
                regression_model_from_dict(data)
            elif family == _FAMILY_CLASSIFICATION:
                classification_model_from_dict(data)
            else:
                return ["No importer is available for this family."]
        except Exception as exc:
            return [str(exc)]
        return []


def _normalize(text: str) -> str:
    text = text.replace("≤", "<=").replace("≥", ">=")
    text = text.replace("−", "-").replace("–", "-")
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", ascii_text.casefold()).strip()


def _supported_language(language: str | None) -> str:
    """Fall back to English for any language Optees does not translate.

    The language comes from Settings, never from guessing the prompt: colloquial
    Italian carries none of the markers a heuristic would look for.
    """
    return language if language in _MESSAGES else "en"


def _has_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def _has_conditional_markers(text: str) -> bool:
    return bool(
        re.search(r"\b(if|se|soglia|threshold|scaglione|sotto|superiore|altrimenti)\b", text)
    )


def _has_fractional_knapsack_markers(text: str) -> bool:
    return _has_any(
        text,
        (
            "fractional",
            "frazion",
            "fraction",
            "partially",
            "parziale",
            "portions",
            "porzion",
            "divisible",
            "divisibil",
            # Untrained wording for divisible goods.
            "in bulk",
            "sfus",
            "just a part",
            "part of each",
            "una parte di",
            "parte di ciascun",
        ),
    )


def _has_continuous_production_mix_markers(text: str) -> bool:
    return (
        _has_any(
            text,
            (
                "manufacture",
                "manufacturing",
                "produce",
                "produced",
                "production",
                "produrre",
                "prodotto",
                "prodotti",
                "produzione",
            ),
        )
        and _has_any(text, ("profit", "profitto", "margine", "margin"))
        and _has_any(
            text,
            (
                "machine hour",
                "machine hours",
                "labor hour",
                "labor hours",
                "ore macchina",
                "ora macchina",
                "ore di lavoro",
                "materia prima",
                "raw material",
            ),
        )
        and _has_any(
            text,
            (
                "fractional",
                "continuous",
                "decimal quantities",
                "quantita frazionarie",
                "quantita continue",
                "quantita decimali",
            ),
        )
    )


# ---------------------------------------------------------------------------
# Decision-structure signals
#
# Keyword lists only capture the vocabulary of a domain. Untrained users
# describe the *shape* of the decision instead ("I must choose what fits in my
# suitcase"), so these predicates look for that shape.
# ---------------------------------------------------------------------------

_CONTAINER_LIMIT_MARKERS = (
    "suitcase",
    "valigia",
    "backpack",
    "zaino",
    "bag",
    "borsa",
    "box",
    "scatola",
    "trunk",
    "baule",
    "budget",
    "not everything fits",
    "does not fit",
    "doesn't fit",
    "non ci sta",
    "non ci stanno",
    "without going over",
    "senza sforare",
)

_SELECTION_MARKERS = (
    "choose",
    "pick",
    "select",
    "buy",
    "fund",
    "what should i take",
    "what should i bring",
    "what should i put",
    "which items",
    "which projects",
    "scegliere",
    "scelgo",
    "comprare",
    "finanziare",
    "cosa porto",
    "cosa metto",
    "cosa prendo",
    "quali progetti",
)

_REPEATABLE_MARKERS = (
    "unbounded",
    "illimitat",
    "unlimited",
    "senza limite",
    "any number of times",
    "any number",
    "reused any number",
    "quante volte voglio",
    "quanti ne voglio",
    "quante ne voglio",
    "riutilizzare",
    "riusare",
    "as many as i want",
    "as many as you want",
    "same kind",
    "same type",
    "stesso tipo",
)

_BOUNDED_MARKERS = (
    "bounded",
    "limitata",
    "limite massimo",
    "max quantity",
    "quantita max",
    "quantita massima",
    "maximum available amount",
    "up to",
    "fino a",
)

_ALL_OR_NOTHING_MARKERS = (
    "per intero oppure",
    "per intero o non",
    "in full or not",
    "fully or not",
    "all or nothing",
    "tutto o niente",
)

_MULTI_RESOURCE_MARKERS = (
    "multi dimensional",
    "multidimensional",
    "multi-dimensional",
    "multi-dimensionale",
    "multi dimensionale",
    "risorse",
    "resources",
    "both limits",
    "entrambi i limiti",
    "more than one resource",
    "multiple resources",
    "piu risorse",
)


def _has_container_limit_markers(text: str) -> bool:
    return _has_any(text, _CONTAINER_LIMIT_MARKERS)


def _has_selection_markers(text: str) -> bool:
    return _has_any(text, _SELECTION_MARKERS)


def _has_repeatable_markers(text: str) -> bool:
    return _has_any(text, _REPEATABLE_MARKERS)


def _has_all_or_nothing_markers(text: str) -> bool:
    """True for "take it in full or not at all" wording.

    Italian "per intero" means "the whole item", not "integer variable": without
    this guard the MILP integrality keyword ``intero`` fires on a plain 0/1
    selection.
    """
    return _has_any(text, _ALL_OR_NOTHING_MARKERS)


def _has_bounded_markers(text: str) -> bool:
    return _has_any(text, _BOUNDED_MARKERS)


def _has_multi_resource_markers(text: str) -> bool:
    """True when the prompt constrains two or more distinct resources.

    A single ``budget`` (or a single weight limit) is an ordinary knapsack; only
    two simultaneous limits make the model multi-dimensional.
    """
    if _has_any(text, _MULTI_RESOURCE_MARKERS):
        return True
    dimensions = (
        _has_any(text, ("weight", "peso")),
        "volume" in text,
        "budget" in text,
    )
    return sum(dimensions) >= 2


def _has_yes_no_decision(text: str) -> bool:
    return _has_any(text, ("yes or no", "si o no", "whether", "aprire o no", "attivare o no"))


def _has_quantity_decision(text: str) -> bool:
    return _has_any(text, ("how many", "how much", "quante", "quanti", "quanto", "units", "unita"))


def _priority(family: str) -> int:
    return {
        _FAMILY_KNAPSACK: 6,
        _FAMILY_SCHEDULING: 5,
        _FAMILY_ROBUST: 4,
        _FAMILY_MILP: 3,
        _FAMILY_REGRESSION: 3,
        _FAMILY_CLASSIFICATION: 4,
        _FAMILY_GRAPH: 5,
        _FAMILY_NLP: 2,
        _FAMILY_LP: 1,
        _FAMILY_UNKNOWN: 0,
    }.get(family, 0)


def _confidence(score: int, has_draft: bool, known_family: bool) -> float:
    if not known_family:
        return 0.15
    base = min(0.35 + score / 24.0, 0.9)
    if has_draft:
        base += 0.08
    return round(min(base, 0.98), 2)


def _extract_named_number(text: str, labels: tuple[str, ...]) -> float | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    patterns = (
        rf"(?:{label_pattern})\s*(?:=|:|massima|max)?\s*({_NUM})",
        rf"({_NUM})\s*(?:di\s+)?(?:{label_pattern})",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _to_number(match.group(1))
    return None


def _extract_knapsack_capacity(text: str) -> float | None:
    capacity = _extract_named_number(text, ("capacity", "capacita", "capienza"))
    if capacity is not None:
        return capacity

    patterns = (
        rf"(?:my\s+)?(?:bag|backpack|zaino|borsa).{{0,20}}(?:big|grande|only|solo).{{0,15}}(?:size|dimensione|capacity|capacita|capienza)\s*({_NUM})",
        rf"(?:bag|backpack|zaino|borsa)\s*(?:is|e|è|only|solo|big|grande|capacity|capacita|capienza|size|dimensione|max|massima).{{0,30}}?(?:capacity|capacita|capienza|big size|size|dimensione)?\s*({_NUM})",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _to_number(match.group(1))
    return None


def _extract_knapsack_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    chunks = re.split(r"[;\n,]|(?:\s+-\s+)", text)
    for chunk in chunks:
        if not _has_any(chunk, ("value", "valore")) or not _has_any(
            chunk,
            ("weight", "peso", "size", "dimensione"),
        ):
            continue

        value = _extract_named_number(chunk, ("value", "valore"))
        weight = _extract_named_number(chunk, ("weight", "peso", "size", "dimensione"))
        if value is None or weight is None:
            continue

        name = _extract_item_name(chunk) or f"Item {len(items) + 1}"
        item: dict[str, Any] = {"name": name, "value": value, "weight": weight}
        max_quantity = _extract_named_number(
            chunk,
            ("max_quantity", "max quantity", "quantita max", "quantita massima", "limite"),
        )
        if max_quantity is not None:
            item["max_quantity"] = max_quantity
        items.append(item)
    return items


def _extract_item_name(chunk: str) -> str | None:
    patterns = (
        r"(?:item|oggetto)\s+([a-z][a-z0-9_-]*)",
        r"(?:a|an|un|una|uno|my|il|la|lo|l')\s+([a-z][a-z0-9_-]*(?:\s+of\s+[a-z][a-z0-9_-]*)?)\s+(?:size|dimensione|weight|peso|value|valore)\b",
        r"\b([a-z][a-z0-9_-]*(?:\s+of\s+[a-z][a-z0-9_-]*)?)\s+(?:size|dimensione|weight|peso)\b",
        r"\b([a-z][a-z0-9_-]*)\s+(?:value|valore)\b",
    )
    ignored = {
        "with",
        "con",
        "capacity",
        "capacita",
        "item",
        "oggetto",
        "value",
        "valore",
        "weight",
        "peso",
        "size",
        "dimensione",
        "my",
    }
    for pattern in patterns:
        match = re.search(pattern, chunk)
        if match:
            candidate = match.group(1)
            if candidate not in ignored:
                return candidate.upper() if len(candidate) == 1 else candidate
    return None


def _parse_linear_problem(text: str, *, include_integrality: bool) -> _LinearDraft | None:
    sense = "min" if _has_any(text, ("minimize", "minimizza", "min ")) else "max"
    objective_part, constraints_part = _split_linear_prompt(text)
    if not objective_part or not constraints_part:
        return None

    objective_coefs = _parse_linear_expression(objective_part)
    constraints = _parse_constraints(constraints_part)
    if not objective_coefs or not constraints:
        return None

    variable_names = _ordered_variables([objective_coefs, *[c[0] for c in constraints]])
    if not variable_names:
        return None

    variables: list[dict[str, Any]] = []
    for name in variable_names:
        variable = {"name": name, "label": "", "lb": 0, "ub": None}
        if include_integrality:
            integrality = _integrality_for_variable(text, name)
            variable["integrality"] = integrality
            if integrality == "B":
                variable["ub"] = 1
        variables.append(variable)

    warnings = ("Assumed non-negative variables.",)
    data: dict[str, Any] = {
        "version": "1",
        "variables": variables,
        "objective": {
            "sense": sense,
            "coefficients": [_coef_for(objective_coefs, name) for name in variable_names],
            "offset": 0,
        },
        "constraints": [
            {
                "coefficients": [_coef_for(coefs, name) for name in variable_names],
                "relation": relation,
                "rhs": rhs,
            }
            for coefs, relation, rhs in constraints
        ],
    }
    return _LinearDraft(data=data, warnings=warnings)


def _split_linear_prompt(text: str) -> tuple[str | None, str | None]:
    objective_match = re.search(
        r"(?:maximize|maximise|max|massimizza|massimizzare|minimize|minimise|min|minimizza|minimizzare)\s+(.+?)\s+(?:subject to|s\.t\.|such that|vincoli|con vincoli|soggetto a)\s+(.+)",
        text,
    )
    if objective_match:
        return objective_match.group(1), objective_match.group(2)
    return None, None


def _parse_constraints(text: str) -> list[tuple[dict[str, float], str, float]]:
    constraints: list[tuple[dict[str, float], str, float]] = []
    for raw in re.split(r";|\band\b|\be\b", text):
        raw = raw.strip(" ,.")
        if not raw:
            continue
        match = re.search(rf"(.+?)(<=|>=|=)\s*({_NUM})", raw)
        if not match:
            continue
        coefs = _parse_linear_expression(match.group(1))
        if not coefs:
            continue
        constraints.append((coefs, match.group(2), _to_number(match.group(3))))
    return constraints


def _parse_linear_expression(expr: str) -> dict[str, float]:
    # Add an explicit separator before signs that introduce a new term, while
    # leaving relation operators untouched because constraints are split first.
    normalized = re.sub(r"(?<![<>=])([+-])", r" \1", expr)
    coefs: dict[str, float] = {}
    for match in re.finditer(rf"([+-]?\s*(?:{_NUM})?)\s*\*?\s*([a-z]\w*)", normalized):
        raw_coef = match.group(1).replace(" ", "")
        variable = match.group(2)
        if variable in _STOP_WORDS:
            continue
        coef = _coefficient(raw_coef)
        coefs[variable] = coefs.get(variable, 0.0) + coef
    return coefs


def _ordered_variables(expressions: Iterable[dict[str, float]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for expr in expressions:
        for name in expr:
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def _integrality_for_variable(text: str, name: str) -> str:
    variable_window = rf"{re.escape(name)}\s*(?:is|e|è|:)?\s*(binary|binaria|bool|boolean|integer|intera|intero)"
    match = re.search(variable_window, text)
    if match:
        token = match.group(1)
        if token in {"binary", "binaria", "bool", "boolean"}:
            return "B"
        return "I"
    if _has_any(text, ("binary variables", "variabili binarie", "booleane", "boolean variables")):
        return "B"
    if _has_any(text, ("integer variables", "variabili intere")):
        return "I"
    return "C"


def _coef_for(coefs: dict[str, float], variable: str) -> float:
    return float(coefs.get(variable, 0.0))


def _coefficient(raw: str) -> float:
    if raw in {"", "+"}:
        return 1.0
    if raw == "-":
        return -1.0
    return _to_number(raw)


def _to_number(raw: str) -> float:
    return float(str(raw).replace(",", "."))


_SUPERVISED_FEATURE_FIELDS = (
    "feature",
    "features",
    "caratteristica",
    "caratteristiche",
    "variabile",
    "variabili",
)
_SUPERVISED_TARGET_FIELDS = (
    "target",
    "outcome",
    "label",
    "bersaglio",
    "esito",
    "classe",
)
_SUPERVISED_ROW_FIELDS = (
    "rows",
    "data",
    "observations",
    "records",
    "righe",
    "dati",
    "osservazioni",
)


def _parse_supervised_dataset(source: str, *, problem_type: str) -> dict[str, Any] | None:
    """Parse an intentionally small, unambiguous local table notation.

    Natural language is sufficient for a solver recommendation, but it cannot
    reliably encode a dataset. Drafting therefore requires named columns and
    pipe-separated cells, for example::

        features: area, rooms; target: price;
        rows: 50 | 2 | 120; 60 | 2 | 140; 70 | 3 | 170; 80 | 3 | 200

    Pipes make commas safe as decimal separators in Italian prompts. The model
    importer remains the authority for row counts, label cardinality, and all
    numerical validation.
    """
    feature_field = _extract_supervised_field(source, _SUPERVISED_FEATURE_FIELDS)
    target_field = _extract_supervised_field(source, _SUPERVISED_TARGET_FIELDS)
    rows_field = _extract_supervised_rows(source)
    if feature_field is None or target_field is None or rows_field is None:
        return None

    feature_names = _split_supervised_feature_names(feature_field)
    target_name = _clean_supervised_cell(target_field)
    if not feature_names or not target_name:
        return None

    rows: list[dict[str, object]] = []
    expected_width = len(feature_names) + 1
    for raw_row in re.split(r"[;\n]+", rows_field):
        row = raw_row.strip()
        if not row:
            continue
        cells = [_clean_supervised_cell(cell) for cell in row.strip("|").split("|")]
        if len(cells) != expected_width or any(not cell for cell in cells):
            return None
        try:
            features = [_to_number(cell) for cell in cells[:-1]]
            target: object = (
                _to_number(cells[-1])
                if problem_type == "regression"
                else cells[-1]
            )
        except ValueError:
            return None
        rows.append({"features": features, "target": target})

    if not rows:
        return None

    return {
        "version": "1",
        "problem_type": problem_type,
        "dataset": {
            "feature_names": feature_names,
            "target_name": target_name,
            "rows": rows,
        },
        "training_options": {},
    }


def _extract_supervised_field(source: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"\b(?:{label_pattern})\b\s*:\s*([^;\n]+)",
        source,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else None


def _extract_supervised_rows(source: str) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in _SUPERVISED_ROW_FIELDS)
    match = re.search(
        rf"\b(?:{label_pattern})\b\s*:\s*(.+)$",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else None


def _split_supervised_feature_names(raw: str) -> list[str]:
    separator = "|" if "|" in raw else ","
    values = [_clean_supervised_cell(value) for value in raw.split(separator)]
    return values if values and all(values) else []


def _clean_supervised_cell(value: str) -> str:
    return value.strip().strip("`*_ ")


_NUM = r"[-+]?\d+(?:[\.,]\d+)?"
_STOP_WORDS = {
    "and",
    "e",
    "subject",
    "to",
    "soggetto",
    "vincoli",
    "con",
    "constraint",
    "constraints",
    "max",
    "min",
    "maximize",
    "minimize",
    "massimizza",
    "minimizza",
}


_MESSAGES = {
    "en": {
        "empty_prompt": "Describe the optimization problem to get a recommendation.",
        "problem_description": "problem description",
        "planned_family": "This family is recognized but its dedicated Optees form is not implemented yet.",
        "nlp_drafting_deferred": "The NLP form is available, but rule-based NLP JSON drafting is not implemented yet.",
        "supervised_dataset_format": "an explicit dataset table: features: f1, f2; target: y; rows: 1 | 2 | label_or_value; ...",
        "graph_drafting_deferred": "The Shortest Path graph form is available, but rule-based graph JSON drafting is not implemented yet.",
        "problem_family": "problem family",
        "capacity": "capacity",
        "items_with_value_weight": "items with value and weight",
        "linear_objective": "linear objective function",
        "linear_constraints": "linear constraints",
        "integrality": "which variables are continuous, integer, or binary",
        "reason_knapsack": "The prompt mentions items, values, weights, or capacity, which are the core data of a knapsack model.",
        "reason_knapsack_bounded": "The prompt includes explicit quantity limits, so bounded knapsack is the closest variant.",
        "reason_knapsack_unbounded": "The prompt allows repeated use without an explicit item limit, so unbounded knapsack is appropriate.",
        "reason_knapsack_fractional": "The prompt allows partial items, so the fractional variant is appropriate.",
        "reason_knapsack_multi_dimensional": "The prompt contains multiple resources, so a multi-dimensional knapsack model is appropriate.",
        "reason_milp": "The prompt contains integer, binary, threshold, setup, or conditional decisions.",
        "reason_threshold": "Threshold or block choices require binary variables to activate the selected segment.",
        "reason_lp": "The prompt describes a linear objective with linear constraints and continuous decisions.",
        "reason_nlp": "The prompt mentions nonlinear expressions, curves, products of variables, or derivatives.",
        "reason_regression": "The prompt asks to estimate or predict a continuous outcome from previous numerical observations.",
        "reason_classification": "The prompt asks to predict one of two named outcomes from previous observations.",
        "reason_graph": "The prompt asks for the shortest or cheapest route between two points across a network of connections.",
        "reason_scheduling": "The prompt mentions jobs, machines, sequences, deadlines, or makespan.",
        "reason_robust": "The prompt mentions uncertainty, scenarios, regret, or worst-case decisions.",
        "reason_unknown": "The prompt is too generic for a reliable solver recommendation.",
        "reason_json": "The generated draft is validated against Optees JSON importers when enough data is present.",
    },
    "it": {
        "empty_prompt": "Descrivi il problema di ottimizzazione per ottenere un suggerimento.",
        "problem_description": "descrizione del problema",
        "planned_family": "Questa famiglia e' riconosciuta ma la schermata dedicata in Optees non e' ancora implementata.",
        "nlp_drafting_deferred": "La schermata NLP e' disponibile, ma la generazione rule-based di JSON NLP non e' ancora implementata.",
        "supervised_dataset_format": "una tabella dati esplicita: caratteristiche: f1, f2; bersaglio: y; righe: 1 | 2 | etichetta_o_valore; ...",
        "graph_drafting_deferred": "La schermata del grafo (cammino minimo) e' disponibile, ma la generazione rule-based di JSON per i grafi non e' ancora implementata.",
        "problem_family": "famiglia del problema",
        "capacity": "capacita'",
        "items_with_value_weight": "oggetti con valore e peso",
        "linear_objective": "funzione obiettivo lineare",
        "linear_constraints": "vincoli lineari",
        "integrality": "quali variabili sono continue, intere o binarie",
        "reason_knapsack": "Il testo parla di oggetti, valori, pesi o capacita': sono i dati centrali di un modello knapsack.",
        "reason_knapsack_bounded": "Il testo contiene limiti espliciti sulle quantita', quindi la variante bounded e' la piu' vicina.",
        "reason_knapsack_unbounded": "Il testo consente di riusare gli oggetti senza limite esplicito, quindi serve un knapsack unbounded.",
        "reason_knapsack_fractional": "Il testo consente di scegliere parti di oggetto, quindi serve la variante fractional.",
        "reason_knapsack_multi_dimensional": "Il testo contiene piu' risorse, quindi serve un knapsack multi-dimensionale.",
        "reason_milp": "Il testo contiene decisioni intere, binarie, a soglia, di setup o condizionali.",
        "reason_threshold": "Scelte a soglia o per blocchi richiedono variabili binarie per attivare il segmento scelto.",
        "reason_lp": "Il testo descrive un obiettivo lineare con vincoli lineari e decisioni continue.",
        "reason_nlp": "Il testo cita espressioni non lineari, curve, prodotti tra variabili o derivate.",
        "reason_regression": "Il testo chiede di stimare o prevedere un risultato continuo a partire da osservazioni numeriche precedenti.",
        "reason_classification": "Il testo chiede di prevedere uno di due esiti nominati a partire da osservazioni precedenti.",
        "reason_graph": "Il testo chiede il percorso piu' breve o economico tra due punti in una rete di collegamenti.",
        "reason_scheduling": "Il testo cita lavori, macchine, sequenze, scadenze o makespan.",
        "reason_robust": "Il testo cita incertezza, scenari, regret o decisioni worst-case.",
        "reason_unknown": "Il testo e' troppo generico per consigliare un solver in modo affidabile.",
        "reason_json": "La bozza generata viene validata contro gli importer JSON di Optees quando ci sono dati sufficienti.",
    },
}


def _msg(language: str, key: str) -> str:
    return _MESSAGES.get(language, _MESSAGES["en"]).get(key, key)
