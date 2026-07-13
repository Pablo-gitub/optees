"""The assistant must recognize graph / shortest-path problems.

Shortest path is implemented in the app (graph view, ShortestPathModel, JSON
importer) but the assistant used to ignore it entirely. As with the other
implemented-but-not-drafted families (NLP, regression, classification), the
assistant should classify the family and then ask for the graph data instead of
inventing it.

Prompts are ordered from the most trained user (graph-theory notation) to the
least trained one (no graph vocabulary at all, only "get from A to B fast").
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from optees.data.adapters.assistant import RuleBasedAssistantAdapter


@dataclass(frozen=True)
class GraphScenario:
    level: int
    name: str
    prompt_en: str
    prompt_it: str


SCENARIOS: tuple[GraphScenario, ...] = (
    GraphScenario(
        1,
        "expert_weighted_digraph",
        "Compute the shortest path in a weighted directed graph from node A to node F.",
        "Calcola il cammino minimo in un grafo orientato pesato dal nodo A al nodo F.",
    ),
    GraphScenario(
        2,
        "practitioner_road_network",
        "I have a road network with distances and I need the cheapest route from the "
        "depot to the customer.",
        "Ho una rete stradale con le distanze e mi serve il percorso piu' economico dal "
        "deposito al cliente.",
    ),
    GraphScenario(
        3,
        "analyst_travel_times",
        "Find the fastest way from the warehouse to the store across connected roads "
        "that each take some minutes.",
        "Trova il modo piu' veloce dal magazzino al negozio attraverso strade collegate, "
        "ognuna con dei minuti di percorrenza.",
    ),
    GraphScenario(
        4,
        "layperson_streets",
        "What is the quickest route from my home to the office through these streets?",
        "Qual e' il tragitto piu' rapido da casa mia all'ufficio passando per queste strade?",
    ),
    GraphScenario(
        5,
        "novice_from_a_to_b",
        "How can I get from A to B as fast as possible?",
        "Come faccio ad arrivare da A a B il piu' velocemente possibile?",
    ),
)


_CASES = [
    pytest.param(s, lang, id=f"L{s.level}-{s.name}-{lang}")
    for s in SCENARIOS
    for lang in ("en", "it")
]


@pytest.fixture()
def assistant() -> RuleBasedAssistantAdapter:
    return RuleBasedAssistantAdapter()


def _prompt(s: GraphScenario, lang: str) -> str:
    return s.prompt_en if lang == "en" else s.prompt_it


@pytest.mark.parametrize(("scenario", "language"), _CASES)
def test_assistant_recognizes_shortest_path_problems(
    assistant: RuleBasedAssistantAdapter,
    scenario: GraphScenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language), language=language)

    assert analysis.family == "graph"
    assert analysis.variant == "shortest_path"
    assert analysis.implemented is True
    assert analysis.confidence > 0
    assert analysis.reasons


@pytest.mark.parametrize(("scenario", "language"), _CASES)
def test_assistant_defers_graph_drafting_and_asks_for_data(
    assistant: RuleBasedAssistantAdapter,
    scenario: GraphScenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language), language=language)

    # The assistant recognizes the family but does not invent nodes/edges.
    assert not analysis.is_loadable
    assert analysis.model_json is None
    assert analysis.needs_clarification


def test_graph_reason_is_localized(assistant: RuleBasedAssistantAdapter) -> None:
    it = assistant.analyze("Cammino minimo nel grafo dal nodo A al nodo B.", language="it")
    en = assistant.analyze("Shortest path in the graph from node A to node B.", language="en")

    assert it.language == "it"
    assert en.language == "en"
    assert it.reasons[0] != en.reasons[0]
