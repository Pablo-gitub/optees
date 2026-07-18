from __future__ import annotations

import pytest

from optees.data.adapters.assistant import RuleBasedAssistantAdapter
from optees.utility.knapsack_json_io import knapsack_problem_from_dict
from optees.utility.lp_json_io import lp_model_from_dict
from optees.utility.milp_json_io import milp_model_from_dict


@pytest.fixture()
def assistant() -> RuleBasedAssistantAdapter:
    return RuleBasedAssistantAdapter()


@pytest.mark.parametrize(
    ("prompt", "family", "variant"),
    [
        (
            "Maximize 3x + 5y subject to 2x + y <= 10; x + 3y <= 12.",
            "lp",
            "standard_lp",
        ),
        (
            "Ho una funzione obiettivo lineare e vincoli lineari con variabili continue.",
            "lp",
            "standard_lp",
        ),
        (
            "Tchebycheff min-max goal programming for balancing deviations from targets.",
            "lp",
            "tchebycheff_goal_programming",
        ),
        (
            "Maximize profit with binary variables x and y, subject to linear constraints.",
            "milp",
            "standard_milp",
        ),
        (
            "Devo minimizzare gli scarti: se la quantita e' sotto 1000 uso un coefficiente, altrimenti un altro.",
            "milp",
            "piecewise_threshold",
        ),
        (
            "We need fixed setup decisions and integer production lots with linear constraints.",
            "milp",
            "standard_milp",
        ),
        (
            "Knapsack capacity 7; item A value 10 weight 4; item B value 7 weight 3.",
            "knapsack",
            "zero_one",
        ),
        (
            "Zaino con capacita 9; oggetto A valore 6 peso 2; oggetto B valore 10 peso 5.",
            "knapsack",
            "zero_one",
        ),
        (
            "Bounded knapsack capacity 10; item A value 6 weight 2 max quantity 3.",
            "knapsack",
            "bounded",
        ),
        (
            "Unbounded knapsack with capacity 12 and reusable items.",
            "knapsack",
            "unbounded",
        ),
        (
            "Fractional knapsack: capacity 7.5; item gold value 10 weight 2.5.",
            "knapsack",
            "fractional",
        ),
        (
            "Multi-dimensional knapsack with weight, volume and budget resources.",
            "knapsack",
            "multi_dimensional",
        ),
        (
            "Minimize the Rosenbrock nonlinear function with derivatives.",
            "nlp",
            "standard_nlp",
        ),
        (
            "Voglio fare minimi quadrati non lineari per stimare i parametri di una curva.",
            "nlp",
            "least_squares",
        ),
        (
            "Nonlinear min max optimization: minimize the maximum of several convex penalties.",
            "nlp",
            "nonlinear_min_max",
        ),
        (
            "Assign jobs to parallel machines and minimize makespan.",
            "scheduling",
            "parallel_machines",
        ),
        (
            "Devo programmare turni su macchine con scadenze e ritardi.",
            "scheduling",
            "scheduling",
        ),
        (
            "Min max regret over demand scenarios with uncertain costs.",
            "robust",
            "min_max_regret",
        ),
        (
            "Newsboy problem: choose an order quantity when demand is uncertain.",
            "robust",
            "newsvendor",
        ),
        (
            "Revenue management with uncertain demand scenarios.",
            "robust",
            "revenue_management",
        ),
        (
            "Maximize my bag, I have 6 objects: a laptop size 6 value 20, "
            "a bottle of water size 2 value 1, earphone size 1 value 5, "
            "my phone size 3 value 10, cigarettes size 2 value 3, "
            "a book size 2 value 2, my bag is only big size 10.",
            "knapsack",
            "zero_one",
        ),
        (
            "I have a vague business problem and I am not sure what to optimize.",
            "unknown",
            "unknown",
        ),
    ],
)
def test_rule_based_assistant_classifies_prompt_family_and_variant(
    assistant: RuleBasedAssistantAdapter,
    prompt: str,
    family: str,
    variant: str,
) -> None:
    analysis = assistant.analyze(prompt)

    assert analysis.family == family
    assert analysis.variant == variant
    assert analysis.confidence > 0
    assert analysis.reasons


@pytest.mark.parametrize(
    ("language", "prompt"),
    [
        (
            "en",
            "I manufacture two products. Product A earns a profit of 30, requires "
            "2 machine hours, and at most 4 units can be produced. Product B earns "
            "a profit of 40, requires 4 machine hours, and at most 5 units can be "
            "produced. I have 18 machine hours available. Quantities may be "
            "fractional and must be non-negative. Use the available Optees tools to "
            "identify and inspect the appropriate solver, formulate the versioned "
            "problem, validate the exact payload before solving, and execute it.",
        ),
        (
            "it",
            "Produco due prodotti. Il prodotto A genera un profitto di 30, richiede "
            "2 ore macchina e se ne possono produrre al massimo 4 unita. Il prodotto "
            "B genera un profitto di 40, richiede 4 ore macchina e se ne possono "
            "produrre al massimo 5 unita. Ho 18 ore macchina disponibili. Le quantita "
            "possono essere frazionarie e devono essere non negative. Usa gli strumenti "
            "Optees disponibili per identificare il solver appropriato, formulare il "
            "problema versionato, validarlo ed eseguirlo.",
        ),
    ],
)
def test_production_mix_with_fractional_quantities_is_lp_not_knapsack(
    assistant: RuleBasedAssistantAdapter,
    language: str,
    prompt: str,
) -> None:
    analysis = assistant.analyze(prompt, language)

    assert analysis.family == "lp"
    assert analysis.variant == "standard_lp"
    assert analysis.reasons


_HUMAN_DESCRIPTION_SCENARIOS = [
    (
        "continuous_production_mix",
        "I manage a small workshop. I need to decide how much of each product to make, "
        "including decimal quantities, using limited labor hours and raw material while "
        "maximizing profit.",
        "Gestisco un piccolo laboratorio. Devo decidere quanto produrre di ogni prodotto, "
        "anche in quantita decimali, usando ore di lavoro e materia prima limitate e "
        "massimizzando il profitto.",
        "lp",
        "standard_lp",
    ),
    (
        "fixed_opening_decisions",
        "I must choose which warehouses to open and then decide how much to ship from each "
        "open warehouse. Opening a warehouse is a yes or no decision, shipping quantities "
        "are continuous, and I want to minimize total cost.",
        "Devo scegliere quali magazzini aprire e poi decidere quanto spedire da ogni "
        "magazzino aperto. Aprire un magazzino e' una decisione si o no, le quantita "
        "spedite sono continue e voglio minimizzare il costo totale.",
        "milp",
        "standard_milp",
    ),
    (
        "threshold_scrap_blocks",
        "Production waste changes by batch size: below 1000 pieces I have one scrap rate, "
        "above that threshold I have another. I need to choose the best production block.",
        "Lo scarto di produzione cambia in base alla dimensione del lotto: sotto 1000 "
        "pezzi ho un tasso di scarto, sopra quella soglia ne ho un altro. Devo scegliere "
        "il blocco produttivo migliore.",
        "milp",
        "piecewise_threshold",
    ),
    (
        "backpack_item_choice",
        "I am preparing a hiking backpack and I want to choose which items to carry. Each "
        "item has a weight and a usefulness score, and the backpack cannot exceed its limit.",
        "Sto preparando uno zaino da trekking e voglio scegliere quali oggetti portare. "
        "Ogni oggetto ha un peso e un punteggio di utilita, e lo zaino non puo superare "
        "il suo limite.",
        "knapsack",
        "zero_one",
    ),
    (
        "bounded_repeated_items",
        "I can take repeated supplies, but every type has a maximum available amount: up "
        "to 3 batteries, up to 2 food packs, and up to 4 water bottles.",
        "Posso portare scorte ripetute, ma ogni tipo ha una quantita massima disponibile: "
        "fino a 3 batterie, fino a 2 pacchi di cibo e fino a 4 bottiglie d'acqua.",
        "knapsack",
        "bounded",
    ),
    (
        "unlimited_repeated_items",
        "I am filling a box with product types that can be reused any number of times. The "
        "only real limit is the box capacity.",
        "Sto riempiendo una scatola con tipi di prodotto che posso riutilizzare quante "
        "volte voglio. L'unico vero limite e' la capacita della scatola.",
        "knapsack",
        "unbounded",
    ),
    (
        "partial_item_choice",
        "I can take portions of divisible goods, such as liquids or powder. I do not need "
        "to take a whole item, only the fraction that fits best.",
        "Posso prendere porzioni di beni divisibili, come liquidi o polveri. Non devo "
        "prendere un oggetto intero, ma solo la frazione che conviene di piu.",
        "knapsack",
        "fractional",
    ),
    (
        "truck_weight_volume",
        "I need to load a delivery truck. Every package consumes both weight and volume, "
        "and the selected packages must satisfy both limits at the same time.",
        "Devo caricare un camion per le consegne. Ogni pacco consuma sia peso sia volume, "
        "e i pacchi scelti devono rispettare entrambi i limiti nello stesso momento.",
        "knapsack",
        "multi_dimensional",
    ),
    (
        "curved_response_model",
        "The response is not straight: doubling the input does not double the output, and "
        "the relationship looks curved. I need to fit parameters of this model.",
        "La risposta non e' lineare: raddoppiare l'input non raddoppia l'output e la "
        "relazione sembra curva. Devo stimare i parametri di questo modello.",
        "nlp",
        "standard_nlp",
    ),
    (
        "machine_job_planning",
        "I have many jobs to assign to machines. Each job takes time, machines work in "
        "parallel, and I want the last machine to finish as early as possible.",
        "Ho molti lavori da assegnare alle macchine. Ogni lavoro richiede tempo, le "
        "macchine lavorano in parallelo e voglio che l'ultima macchina finisca il prima "
        "possibile.",
        "scheduling",
        "parallel_machines",
    ),
    (
        "demand_scenarios_regret",
        "Demand is uncertain and I have several possible scenarios. I want a decision that "
        "does not perform too badly compared with the best choice in each scenario.",
        "La domanda e' incerta e ho diversi scenari possibili. Voglio una decisione che "
        "non vada troppo male rispetto alla scelta migliore in ogni scenario.",
        "robust",
        "min_max_regret",
    ),
    (
        "newspaper_order_quantity",
        "I must decide how many newspapers to order before knowing tomorrow's demand. Too "
        "many copies are wasted, too few copies lose sales.",
        "Devo decidere quanti giornali ordinare prima di conoscere la domanda di domani. "
        "Troppe copie diventano invendute, troppo poche fanno perdere vendite.",
        "robust",
        "newsvendor",
    ),
    (
        "hotel_revenue_management",
        "I manage hotel rooms with uncertain demand. I need to decide how many rooms to "
        "protect for high-paying customers and how many to sell early at lower prices.",
        "Gestisco camere di hotel con domanda incerta. Devo decidere quante camere "
        "proteggere per clienti che pagano di piu e quante venderne prima a prezzi piu "
        "bassi.",
        "robust",
        "revenue_management",
    ),
]


@pytest.mark.parametrize(
    ("scenario", "prompt", "family", "variant"),
    [
        (f"{name}:en", prompt_en, family, variant)
        for name, prompt_en, _prompt_it, family, variant in _HUMAN_DESCRIPTION_SCENARIOS
    ]
    + [
        (f"{name}:it", prompt_it, family, variant)
        for name, _prompt_en, prompt_it, family, variant in _HUMAN_DESCRIPTION_SCENARIOS
    ],
)
def test_rule_based_assistant_classifies_human_descriptions_in_english_and_italian(
    assistant: RuleBasedAssistantAdapter,
    scenario: str,
    prompt: str,
    family: str,
    variant: str,
) -> None:
    analysis = assistant.analyze(prompt)

    assert analysis.family == family, scenario
    assert analysis.variant == variant, scenario
    assert analysis.reasons


def test_rule_based_assistant_drafts_valid_lp_json(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze(
        "Maximize 3x + 5y subject to 2x + y <= 10; x + 3y <= 12."
    )

    assert analysis.family == "lp"
    assert analysis.is_loadable
    assert analysis.model_json is not None
    model = lp_model_from_dict(dict(analysis.model_json))
    assert [v.name for v in model.variables] == ["x", "y"]
    assert model.objective.coefs == (3.0, 5.0)
    assert len(model.constraints) == 2


def test_rule_based_assistant_drafts_valid_milp_json(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze(
        "Maximize 3x + 5y subject to 2x + y <= 10; x + 3y <= 12, x binary y integer."
    )

    assert analysis.family == "milp"
    assert analysis.is_loadable
    assert analysis.model_json is not None
    model = milp_model_from_dict(dict(analysis.model_json))
    assert [v.integrality.value for v in model.variables] == ["B", "I"]
    assert model.variables[0].bounds.lb == 0
    assert model.variables[0].bounds.ub == 1


@pytest.mark.parametrize(
    "prompt",
    [
        "Knapsack capacity 7; item A value 10 weight 4; item B value 7 weight 3.",
        "Zaino con capacita 7; oggetto A valore 10 peso 4; oggetto B valore 7 peso 3.",
    ],
)
def test_rule_based_assistant_drafts_valid_knapsack_json(
    assistant: RuleBasedAssistantAdapter,
    prompt: str,
) -> None:
    analysis = assistant.analyze(prompt)

    assert analysis.family == "knapsack"
    assert analysis.is_loadable
    assert analysis.model_json is not None
    problem = knapsack_problem_from_dict(dict(analysis.model_json))
    assert problem.capacity == 7
    assert [item.name for item in problem.items] == ["A", "B"]
    assert [item.value for item in problem.items] == [10, 7]
    assert [item.weight for item in problem.items] == [4, 3]


def test_rule_based_assistant_drafts_bag_prompt_as_knapsack(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze(
        "maximize my bag, I have 6 objects a laptop size 6 value 20, "
        "a bottle of water size 2 value 1, earphone size 1 value 5, "
        "my phone size 3 value 10, cigarets size 2 value 3, "
        "a book size 2 value 2, my bag is only big size 10"
    )

    assert analysis.family == "knapsack"
    assert analysis.is_loadable
    assert analysis.model_json is not None
    problem = knapsack_problem_from_dict(dict(analysis.model_json))
    assert problem.capacity == 10
    assert [item.name for item in problem.items] == [
        "laptop",
        "bottle of water",
        "earphone",
        "phone",
        "cigarets",
        "book",
    ]
    assert [item.weight for item in problem.items] == [6, 2, 1, 3, 2, 2]
    assert [item.value for item in problem.items] == [20, 1, 5, 10, 3, 2]


def test_rule_based_assistant_asks_for_missing_knapsack_data(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze("I need a knapsack model with many valuable items.")

    assert analysis.family == "knapsack"
    assert not analysis.is_loadable
    assert analysis.model_json is None
    assert analysis.missing_information


def test_rule_based_assistant_keeps_planned_families_non_loadable(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze(
        "Assign jobs to machines and minimize the makespan with deadlines."
    )

    assert analysis.family == "scheduling"
    assert not analysis.implemented
    assert not analysis.is_loadable
    assert analysis.model_json is None


@pytest.mark.parametrize(
    ("prompt", "language"),
    [
        ("Minimize the Rosenbrock nonlinear function from a starting point.", "en"),
        ("Voglio minimizzare una funzione non lineare con bounds e punto iniziale.", "it"),
    ],
)
def test_rule_based_assistant_marks_nlp_form_as_available_but_not_draftable(
    assistant: RuleBasedAssistantAdapter,
    prompt: str,
    language: str,
) -> None:
    analysis = assistant.analyze(prompt, language=language)

    assert analysis.family == "nlp"
    assert analysis.implemented
    assert analysis.load_target is None
    assert not analysis.is_loadable
    assert analysis.model_json is None
    assert analysis.missing_information
