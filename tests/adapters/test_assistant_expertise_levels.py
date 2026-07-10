"""Assistant robustness across user expertise levels.

The prompts below are ordered from the most trained user (formal operations
research notation) to the least trained one (vague, colloquial wording with no
numbers at all). Only the families that Optees implements today are covered:
LP, MILP and Knapsack.

A prompt without enough data must still yield the right recommendation and then
ask for the missing information, rather than silently drafting a wrong model.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from optees.data.adapters.assistant import RuleBasedAssistantAdapter


@dataclass(frozen=True)
class Scenario:
    level: int  # 1 = most trained, 5 = least trained
    name: str
    prompt_en: str
    prompt_it: str
    family: str
    variant: str
    loadable: bool


SCENARIOS: tuple[Scenario, ...] = (
    # ---- Level 1: operations research practitioner, formal notation --------
    Scenario(
        1,
        "expert_lp_formal",
        "Maximize 4x1 + 3x2 subject to 2x1 + x2 <= 10; x1 + x2 <= 8.",
        "Massimizza 4x1 + 3x2 soggetto a 2x1 + x2 <= 10; x1 + x2 <= 8.",
        "lp",
        "standard_lp",
        True,
    ),
    Scenario(
        1,
        "expert_milp_formal",
        "Minimize 5y + 2x subject to x - 60y <= 0; x >= 30, y binary.",
        "Minimizza 5y + 2x soggetto a x - 60y <= 0; x >= 30, y binaria.",
        "milp",
        "standard_milp",
        True,
    ),
    Scenario(
        1,
        "expert_knapsack_instance",
        "0-1 knapsack instance: capacity 15; item i1 value 12 weight 7; item i2 value 9 weight 5.",
        "Istanza di knapsack 0-1: capacita 15; oggetto i1 valore 12 peso 7; oggetto i2 valore 9 peso 5.",
        "knapsack",
        "zero_one",
        True,
    ),
    # ---- Level 2: technical user, no OR notation ---------------------------
    Scenario(
        2,
        "practitioner_milp_activate_lines",
        "For each production line I must decide whether to activate it, a yes or no "
        "choice, and then how many units to produce on the active lines, minimizing "
        "total cost.",
        "Per ogni linea di produzione devo decidere se attivarla, una scelta si o no, "
        "e poi quante unita produrre sulle linee attive, minimizzando il costo totale.",
        "milp",
        "standard_milp",
        False,
    ),
    Scenario(
        2,
        "practitioner_lp_continuous_blend",
        "I want to allocate continuous amounts of three raw materials to maximize "
        "profit, respecting the available labor hours.",
        "Voglio allocare quantita continue di tre materie prime per massimizzare il "
        "profitto, rispettando le ore di lavoro disponibili.",
        "lp",
        "standard_lp",
        False,
    ),
    # ---- Level 3: business analyst, domain wording only --------------------
    Scenario(
        3,
        "analyst_project_portfolio",
        "I have a budget of 100000 and five projects, each with a cost and an expected "
        "return. I can either fund a project in full or not fund it at all. I want to "
        "maximize the total return.",
        "Ho un budget di 100000 euro e cinque progetti, ognuno con un costo e un "
        "ritorno atteso. Posso finanziare un progetto per intero oppure non "
        "finanziarlo affatto. Voglio massimizzare il ritorno totale.",
        "knapsack",
        "zero_one",
        False,
    ),
    Scenario(
        3,
        "analyst_truck_two_limits",
        "I need to load a delivery truck. Every package uses both weight and volume, "
        "and the chosen packages must respect both limits at the same time.",
        "Devo caricare un camion per le consegne. Ogni pacco usa sia peso sia volume "
        "e i pacchi scelti devono rispettare entrambi i limiti.",
        "knapsack",
        "multi_dimensional",
        False,
    ),
    # ---- Level 4: layperson describing a concrete situation ----------------
    Scenario(
        4,
        "layperson_camping_no_numbers",
        "I am going camping and my backpack can carry at most 12 kg. The tent is "
        "essential, the stove is useful, the book is not important. What should I take?",
        "Vado in campeggio e il mio zaino regge al massimo 12 kg. La tenda e' "
        "essenziale, il fornello e' utile, il libro non e' importante. Cosa porto?",
        "knapsack",
        "zero_one",
        False,
    ),
    Scenario(
        4,
        "layperson_repeat_pieces_unbounded",
        "I keep filling a box with the same kind of piece, and I can put in as many as "
        "I want until there is no space left.",
        "Riempio una scatola con lo stesso tipo di pezzo e posso metterne quanti ne "
        "voglio finche' c'e' spazio.",
        "knapsack",
        "unbounded",
        False,
    ),
    # ---- Level 5: untrained user, vague and colloquial ---------------------
    Scenario(
        5,
        "novice_suitcase",
        "I have to pack my suitcase but not everything fits. What should I bring?",
        "Devo fare la valigia ma non ci sta tutto quello che vorrei portare. Cosa metto dentro?",
        "knapsack",
        "zero_one",
        False,
    ),
    Scenario(
        5,
        "novice_grocery_budget",
        "I have 50 euros for groceries and I want to buy the most useful things "
        "without going over.",
        "Ho 50 euro per la spesa e vorrei comprare le cose piu' utili senza sforare.",
        "knapsack",
        "zero_one",
        False,
    ),
    Scenario(
        5,
        "novice_bulk_fractional",
        "I am loading a truck with sand and gravel in bulk, and I can take just a part "
        "of each.",
        "Sto caricando un camion con sabbia e ghiaia sfuse e posso caricarne anche solo "
        "una parte di ciascuna.",
        "knapsack",
        "fractional",
        False,
    ),
)


_CASES = [
    pytest.param(scenario, language, id=f"L{scenario.level}-{scenario.name}-{language}")
    for scenario in SCENARIOS
    for language in ("en", "it")
]


@pytest.fixture()
def assistant() -> RuleBasedAssistantAdapter:
    return RuleBasedAssistantAdapter()


def _prompt(scenario: Scenario, language: str) -> str:
    return scenario.prompt_en if language == "en" else scenario.prompt_it


@pytest.mark.parametrize(("scenario", "language"), _CASES)
def test_assistant_recommends_the_right_family_for_every_expertise_level(
    assistant: RuleBasedAssistantAdapter,
    scenario: Scenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language))

    assert analysis.family == scenario.family
    assert analysis.variant == scenario.variant
    assert analysis.implemented is True
    assert analysis.confidence > 0
    assert analysis.reasons


@pytest.mark.parametrize(("scenario", "language"), _CASES)
def test_assistant_only_drafts_a_model_when_the_prompt_carries_the_data(
    assistant: RuleBasedAssistantAdapter,
    scenario: Scenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language))

    if scenario.loadable:
        assert analysis.is_loadable
        assert analysis.model_json is not None
        assert analysis.validation_errors == ()
    else:
        # A vague prompt must never be turned into a silently wrong model.
        assert not analysis.is_loadable
        assert analysis.model_json is None
        assert analysis.needs_clarification
