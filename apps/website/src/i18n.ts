export type Language = "en" | "it";
export type AlgorithmId = "lp" | "milp" | "knapsack" | "nlp" | "regression" | "classification" | "graph";
export type PreviewId =
  | "home"
  | "assistant"
  | "lpSolution"
  | "knapsack"
  | "knapsackSolution"
  | "nlpSolution"
  | "regressionSolution"
  | "classificationSolution"
  | "graphSolution";
export type FeatureId =
  | "assistant"
  | "educational"
  | "variants"
  | "benchmarks"
  | "local"
  | "openSource";

export const supportedLanguages: Language[] = ["en", "it"];

export function detectLanguage(value: string | undefined): Language {
  const normalized = (value ?? "").toLowerCase();
  return normalized.startsWith("it") ? "it" : "en";
}

export function formatMessage(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => values[key] ?? "");
}

type AlgorithmCopy = {
  id: AlgorithmId;
  label: string;
  short: string;
  status: string;
  formula: string;
  description: string;
  details: string[];
  preview: PreviewId;
};

type PreviewCopy = {
  id: PreviewId;
  window: string;
  title: string;
  body: string;
  alt: string;
};

type FeatureCopy = {
  id: FeatureId;
  title: string;
  body: string;
};

type WorkflowStepCopy = {
  number: string;
  title: string;
  body: string;
};

type FaqCopy = {
  q: string;
  a: string;
};

type SiteCopy = {
  meta: {
    title: string;
    description: string;
    ogDescription: string;
  };
  nav: {
    aria: string;
    brandAria: string;
    sectionsAria: string;
    features: string;
    algorithms: string;
    machineLearning: string;
    previews: string;
    faq: string;
    download: string;
    github: string;
    getApp: string;
  };
  language: {
    aria: string;
    label: string;
    options: Record<Language, string>;
  };
  hero: {
    badge: string;
    title: string;
    titleAccent: string;
    copy: string;
    source: string;
    stackLabel: string;
    stack: string[];
    metricsAria: string;
    metrics: Array<{
      value: string;
      label: string;
    }>;
    shotCaption: string;
    floatStatus: string;
    floatObjective: string;
  };
  features: {
    eyebrow: string;
    title: string;
    body: string;
    items: FeatureCopy[];
  };
  algorithms: {
    eyebrow: string;
    title: string;
    body: string;
    tabsAria: string;
    modelLabel: string;
    capabilitiesLabel: string;
    items: AlgorithmCopy[];
  };
  machineLearning: {
    eyebrow: string;
    title: string;
    body: string;
    assistant: {
      title: string;
      body: string;
    };
    workflows: Array<{
      title: string;
      body: string;
      points: string[];
      preview: PreviewId;
    }>;
  };
  previews: {
    eyebrow: string;
    title: string;
    body: string;
    items: PreviewCopy[];
  };
  workflow: {
    eyebrow: string;
    title: string;
    body: string;
    steps: WorkflowStepCopy[];
  };
  download: {
    eyebrow: string;
    title: string;
    body: string;
    latestRelease: string;
    fallbackRelease: string;
    checkingRelease: string;
    downloadFor: string;
    downloadGeneric: string;
    otherVersions: string;
    allReleases: string;
    menuAria: string;
    yourSystem: string;
    platformNames: { mac: string; windows: string; linux: string };
    assetsButton: string;
    platformsLabel: string;
    platforms: string[];
    gatekeeperNote: string;
  };
  faq: {
    eyebrow: string;
    title: string;
    body: string;
    items: FaqCopy[];
  };
  footer: {
    product: string;
    claim: string;
    tagline: string;
    columns: Array<{
      title: string;
      links: Array<{ label: string; key: string }>;
    }>;
    socialAria: string;
    madeBy: string;
    copyright: string;
    license: string;
  };
};

export const copy: Record<Language, SiteCopy> = {
  en: {
    meta: {
      title: "Optees — Open-Source Operations Research Software",
      description:
        "Free, open-source desktop app for Linear Programming, Mixed-Integer Programming, Knapsack, continuous Nonlinear Programming, educational Linear Regression, Binary Classification and Dijkstra shortest paths. Model and solve locally with a guided assistant and educational solution views.",
      ogDescription:
        "Model, solve and understand LP, MILP, Knapsack, continuous NLP, Linear Regression, Binary Classification and Dijkstra shortest paths in a private local desktop app.",
    },
    nav: {
      aria: "Primary navigation",
      brandAria: "Optees home",
      sectionsAria: "Page sections",
      features: "Why Optees",
      algorithms: "Algorithms",
      machineLearning: "AI & Machine Learning",
      previews: "Screens",
      faq: "FAQ",
      download: "Download",
      github: "GitHub",
      getApp: "Get the app",
    },
    language: {
      aria: "Language selection",
      label: "Language",
      options: {
        en: "EN",
        it: "IT",
      },
    },
    hero: {
      badge: "Open source · Cross-platform · Runs 100% locally",
      title: "Operations research,",
      titleAccent: "made effortless.",
      copy:
        "Optees turns operations-research methods into a desktop app anyone can use. Model LP, MILP and five Knapsack variants, explore continuous nonlinear objectives, fit transparent regression and binary classification, or find a Dijkstra shortest path — then understand every result without scripting.",
      source: "Star on GitHub",
      stackLabel: "Powered by",
      stack: ["SciPy", "HiGHS", "OR-Tools", "CP-SAT", "Dijkstra", "Netlib"],
      metricsAria: "Project highlights",
      metrics: [
        { value: "7", label: "Algorithm workflows, ready to use" },
        { value: "5", label: "Knapsack variants in one flow" },
        { value: "100%", label: "Local & private, no cloud" },
      { value: "Apache 2.0", label: "Free and open source" },
      ],
      shotCaption: "Linear Programming solution — objective, ranges and feasible region",
      floatStatus: "Optimal",
      floatObjective: "z = 2·x₁ + 8·x₂ = 10",
    },
    features: {
      eyebrow: "Why Optees",
      title: "Optimization that explains itself",
      body:
        "Most solvers hand you a number. Optees hands you the model, the solution and the reasoning behind it — built for teams, students and analysts alike.",
      items: [
        {
          id: "assistant",
          title: "Local modeling assistant",
          body:
            "A deterministic pattern-matching algorithm works entirely on your device. It does not use an AI model, LLM, or cloud service: it recommends a workflow and can validate explicit structured drafts before loading them.",
        },
        {
          id: "educational",
          title: "Educational solution views",
          body:
            "Read statuses, objective behaviour, optimal ranges, routes, charts and plain-language notes. NLP results explicitly distinguish a local numerical candidate from a proven optimum.",
        },
        {
          id: "variants",
          title: "Five Knapsack variants",
          body:
            "Switch between 0/1, bounded, unbounded, fractional and multi-dimensional models in a single, consistent workflow.",
        },
        {
          id: "benchmarks",
          title: "Benchmark-backed",
          body:
            "LP and MILP regressions use Netlib and MIPLIB. Knapsack includes Burkardt and OR-Library cases; NLP, regression, classification, and graph workflows use documented analytic or deterministic reference cases.",
        },
        {
          id: "local",
          title: "Private by design",
          body:
            "Everything runs on your machine. No accounts, no uploads, no cloud — your data never leaves your desktop.",
        },
        {
          id: "openSource",
          title: "Open source",
          body:
            "Released under an open license. Read the code, file issues, follow the roadmap and shape where Optees goes next.",
        },
      ],
    },
    algorithms: {
      eyebrow: "Algorithms",
      title: "A focused optimization workbench",
      body:
        "Every algorithm family follows the same path: formulate the model, solve it with a proven engine, then inspect the numerical and mathematical behaviour of the result.",
      tabsAria: "Algorithm families",
      modelLabel: "Model",
      capabilitiesLabel: "In this build",
      items: [
        {
          id: "lp",
          label: "Linear Programming",
          short: "LP",
          status: "Available",
          formula: "max cᵀx  s.t.  Ax ≤ b,  x ≥ 0",
          description:
            "Continuous optimization with bounds, constraints, JSON import and optimal-range analysis for alternate optima.",
          details: ["HiGHS backend", "Multiple optima ranges", "Netlib-tested"],
          preview: "lpSolution",
        },
        {
          id: "milp",
          label: "Mixed-Integer Linear Programming",
          short: "MILP",
          status: "Available",
          formula: "max cᵀx  s.t.  Ax ≤ b,  xⱼ ∈ ℤ",
          description:
            "Integer, binary and continuous variables together, with solver controls for time limits and MIP gap.",
          details: ["CP-SAT / CBC", "Feasible status", "MIPLIB dataset"],
          preview: "home",
        },
        {
          id: "knapsack",
          label: "Knapsack",
          short: "KP",
          status: "Available",
          formula: "max Σ vᵢ·xᵢ  s.t.  Σ wᵢ·xᵢ ≤ W",
          description:
            "0/1, bounded, unbounded, fractional and multi-dimensional variants unified in one workflow with JSON import.",
          details: ["JSON import", "Capacity charts", "Variant switch"],
          preview: "knapsackSolution",
        },
        {
          id: "nlp",
          label: "Nonlinear Programming",
          short: "NLP",
          status: "Available",
          formula: "min f(x)  s.t.  gᵢ(x) ≤ 0",
          description:
            "Continuous scalar optimization with safe expressions, an initial point and optional box bounds. The result is an honest local numerical candidate, not a proof of global optimality.",
          details: ["BFGS / Nelder-Mead / L-BFGS-B", "Safe expression parser", "2D and 3D objective views"],
          preview: "nlpSolution",
        },
        {
          id: "regression",
          label: "Linear Regression",
          short: "REG",
          status: "Available",
          formula: "y_hat = beta_0 + Σ beta_j x_j",
          description:
            "Educational OLS and Ridge regression for continuous targets, with a deterministic train/test split, learned coefficients, residuals, and held-out metrics.",
          details: ["OLS and Ridge", "MAE / MSE / RMSE / R-squared", "Local numeric training"],
          preview: "regressionSolution",
        },
        {
          id: "classification",
          label: "Binary Classification",
          short: "CLS",
          status: "Available",
          formula: "P(y = 1 | x) = 1 / (1 + e^(-beta_0 - beta^T x))",
          description:
            "Educational local logistic regression for two named classes, with stratified held-out evaluation, confusion matrices, predicted probabilities, and an optional 2D decision boundary.",
          details: ["Logistic Regression", "Accuracy / Precision / Recall / F1", "Training-only scaling"],
          preview: "classificationSolution",
        },
        {
          id: "graph",
          label: "Graph Theory: Dijkstra",
          short: "DSP",
          status: "Available",
          formula: "min Σ w(u, v) along a path s → t,  w(u, v) ≥ 0",
          description:
            "Find the shortest route in directed or undirected weighted graphs with a source and destination, then inspect the highlighted route, total cost and settled-node trace.",
          details: ["Deterministic local Dijkstra", "JSON import/export", "Route visualization"],
          preview: "graphSolution",
        },
      ],
    },
    machineLearning: {
      eyebrow: "AI & Machine Learning",
      title: "Learn from data without hiding the method",
      body:
        "Optees treats educational machine learning as a transparent local workflow: define a numeric table, keep the train/test split reproducible, inspect the held-out result, and keep predictive claims separate from causal conclusions.",
      assistant: {
        title: "Draft structured data locally",
        body:
          "The Modeling Assistant is a deterministic pattern-matching algorithm, not a generative AI or cloud service. It can recommend Regression or Binary Classification from normal prose, then prepares a loadable dataset only after you explicitly name columns and provide pipe-separated rows; the same importer used by the form validates the draft before it can replace your work.",
      },
      workflows: [
        {
          title: "Linear Regression",
          body:
            "Fit OLS or Ridge models for a continuous numeric target, then compare training and held-out errors instead of trusting a single fitted line.",
          points: ["OLS and Ridge", "MAE, MSE, RMSE, R-squared", "Coefficients and residuals"],
          preview: "regressionSolution",
        },
        {
          title: "Binary Classification",
          body:
            "Train local logistic regression for exactly two named outcomes and inspect the errors each class receives before treating the model as useful.",
          points: ["Stratified split", "Precision, recall, F1", "Confusion matrix and 2D boundary"],
          preview: "classificationSolution",
        },
      ],
    },
    previews: {
      eyebrow: "Explore the app",
      title: "Follow each step of the method",
      body:
        "Each workspace focuses on one part of the learning process: formulate a model, run a local method, then inspect how the result was obtained.",
      items: [
        {
          id: "assistant",
          window: "Optees — Modeling Assistant",
          title: "Describe the decision in your own words",
          body: "The assistant uses deterministic language patterns locally to recommend a solver family. It does not call an AI model or send your description outside Optees; explicit data can become an importer-validated JSON draft.",
          alt: "Optees local modeling assistant recommending the Knapsack workflow and generating validated JSON",
        },
        {
          id: "lpSolution",
          window: "Optees — LP solution",
          title: "Inspect solution behaviour",
          body: "LP solutions include objective checks, optimal ranges and a feasible-region plot with the optimal point.",
          alt: "Optees linear programming solution view with charts and feasible region",
        },
        {
          id: "knapsack",
          window: "Optees — Knapsack setup",
          title: "Model Knapsack visually",
          body: "Pick a variant, set the capacity and describe items in a structured table — no formulas to hand-write.",
          alt: "Optees Knapsack problem setup view with items and capacity",
        },
        {
          id: "knapsackSolution",
          window: "Optees — Knapsack solution",
          title: "Read the result at a glance",
          body: "Capacity usage, selected items and value-to-weight charts sit right next to the decision table.",
          alt: "Optees Knapsack solution view with capacity usage and value charts",
        },
        {
          id: "nlpSolution",
          window: "Optees — NLP solution",
          title: "Inspect local numerical behaviour",
          body: "See the candidate point, termination status and objective landscape. The view makes the local nature of numerical optimization explicit.",
          alt: "Optees nonlinear-programming solution view with candidate details and objective plot",
        },
        {
          id: "regressionSolution",
          window: "Optees — Regression result",
          title: "Evaluate a transparent predictive fit",
          body: "Inspect coefficients, split-aware error metrics, residuals, and the fitted line without treating a small dataset as a causal conclusion.",
          alt: "Optees linear regression solution view with learned coefficients, metrics, residuals, and fitted line",
        },
        {
          id: "classificationSolution",
          window: "Optees — Classification result",
          title: "Inspect a binary decision boundary",
          body: "Review class labels, held-out metrics, confusion matrices, probabilities, and a 2D boundary without confusing a small local model with a production decision system.",
          alt: "Optees binary-classification solution view with coefficients, confusion matrix, metrics, and decision boundary",
        },
        {
          id: "graphSolution",
          window: "Optees — Dijkstra solution",
          title: "Follow the shortest route",
          body: "The selected path is drawn over the graph with its total distance and the deterministic Dijkstra settlement trace.",
          alt: "Optees Dijkstra shortest-path solution view with a highlighted route",
        },
      ],
    },
    workflow: {
      eyebrow: "How it works",
      title: "From model to explanation in three steps",
      body: "The same intuitive loop, whatever you are optimizing.",
      steps: [
        {
          number: "01",
          title: "Formulate",
          body: "Enter variables, bounds, objectives, constraints, Knapsack items or a weighted graph — or import a versioned JSON model.",
        },
        {
          number: "02",
          title: "Solve",
          body: "Run the appropriate local engine: SciPy/HiGHS, OR-Tools, a dedicated Knapsack solver, a SciPy numerical method, or Dijkstra.",
        },
        {
          number: "03",
          title: "Inspect",
          body: "Read the exact or numerical status, objective, selected variables, routes, charts and educational notes that explain the result.",
        },
      ],
    },
    download: {
      eyebrow: "Download",
      title: "Get Optees on your desktop",
      body:
        "Packaged builds are published on GitHub Releases. Install once and the app can check for updates and guide you to the newest installer.",
      latestRelease: "Latest release: {version}",
      fallbackRelease: "Open GitHub to see the latest release",
      checkingRelease: "Checking the latest release…",
      downloadFor: "Download for {platform}",
      downloadGeneric: "Download for desktop",
      otherVersions: "Other platforms",
      allReleases: "All releases on GitHub",
      menuAria: "Choose your platform",
      yourSystem: "detected",
      platformNames: { mac: "macOS", windows: "Windows", linux: "Linux" },
      assetsButton: "All platforms & assets",
      platformsLabel: "Available for",
      platforms: ["macOS", "Windows", "Linux"],
      gatekeeperNote:
        "Builds are unsigned: macOS may ask for a standard Gatekeeper confirmation, and Windows/Linux for the usual first-run approval.",
    },
    faq: {
      eyebrow: "FAQ",
      title: "Questions, answered",
      body: "Everything you need to know before your first optimization.",
      items: [
        {
          q: "What is Optees?",
          a: "Optees is a free, open-source desktop app for operations research and educational machine learning. You can model, solve and inspect LP, MILP, five Knapsack variants, continuous Nonlinear Programming, Linear Regression, Binary Classification and Dijkstra shortest-path problems without writing code.",
        },
        {
          q: "Who is it for?",
          a: "Analysts and businesses who need to make better resource, scheduling and logistics decisions, and students or teachers who want to see the mathematics behind each solution.",
        },
        {
          q: "Is it really free?",
          a: "Yes. Optees is completely free and released under an open-source license. Desktop builds are available on GitHub Releases.",
        },
        {
          q: "Which platforms are supported?",
          a: "Optees is cross-platform and runs on macOS, Windows and Linux.",
        },
        {
          q: "Do I need to know how to code?",
          a: "No. A guided assistant helps you choose the right algorithm and fill in structured inputs, so you can optimize without scripting.",
        },
        {
          q: "What is coming next?",
          a: "The roadmap next adds transparent clustering to the educational AI and machine-learning section, then heuristics and metaheuristics, while benchmark hardening continues across the released families.",
        },
      ],
    },
    footer: {
      product: "Optees",
      claim: "Open-source optimization toolkit",
      tagline: "Model, solve and understand optimization problems — locally and for free.",
      columns: [
        {
          title: "Product",
          links: [
            { label: "Why Optees", key: "#features" },
            { label: "Algorithms", key: "#algorithms" },
            { label: "Screens", key: "#previews" },
            { label: "Download", key: "#download" },
          ],
        },
        {
          title: "Project",
          links: [
            { label: "GitHub repository", key: "repo" },
            { label: "Releases", key: "releases" },
            { label: "Roadmap", key: "roadmap" },
            { label: "Issues", key: "issues" },
          ],
        },
      ],
      socialAria: "Social links",
      madeBy: "Personal website of Paolo Pietrelli",
      copyright: "© {year} Paolo Pietrelli · All rights reserved",
      license: "Apache License 2.0",
    },
  },
  it: {
    meta: {
      title: "Optees — Software Open Source per Ricerca Operativa",
      description:
        "App desktop gratuita e open source per Programmazione Lineare, Intera Mista, Knapsack, Programmazione Non Lineare continua, Regressione Lineare didattica, Classificazione Binaria e cammini minimi di Dijkstra. Modella e risolvi in locale con assistente guidato e viste didattiche.",
      ogDescription:
        "Modella, risolvi e comprendi LP, MILP, Knapsack, NLP continua, Regressione Lineare, Classificazione Binaria e cammini minimi di Dijkstra in un'app desktop privata e locale.",
    },
    nav: {
      aria: "Navigazione principale",
      brandAria: "Home di Optees",
      sectionsAria: "Sezioni della pagina",
      features: "Perché Optees",
      algorithms: "Algoritmi",
      machineLearning: "AI e Machine Learning",
      previews: "Schermate",
      faq: "FAQ",
      download: "Download",
      github: "GitHub",
      getApp: "Scarica l'app",
    },
    language: {
      aria: "Selezione lingua",
      label: "Lingua",
      options: {
        en: "EN",
        it: "IT",
      },
    },
    hero: {
      badge: "Open source · Multipiattaforma · Gira 100% in locale",
      title: "La ricerca operativa,",
      titleAccent: "resa semplice.",
      copy:
        "Optees trasforma metodi di ricerca operativa in un'app desktop alla portata di tutti. Modella LP, MILP e cinque varianti Knapsack, esplora obiettivi non lineari continui, adatta regressione e classificazione binaria trasparenti o trova un cammino minimo con Dijkstra, poi comprendi ogni risultato senza scrivere codice.",
      source: "Metti una stella su GitHub",
      stackLabel: "Basato su",
      stack: ["SciPy", "HiGHS", "OR-Tools", "CP-SAT", "Dijkstra", "Netlib"],
      metricsAria: "Punti chiave del progetto",
      metrics: [
        { value: "7", label: "Flussi algoritmici pronti all'uso" },
        { value: "5", label: "Varianti Knapsack in un solo flusso" },
        { value: "100%", label: "Locale e privato, nessun cloud" },
      { value: "Apache 2.0", label: "Gratuito e open source" },
      ],
      shotCaption: "Soluzione di Programmazione Lineare — obiettivo, range e regione ammissibile",
      floatStatus: "Ottimo",
      floatObjective: "z = 2·x₁ + 8·x₂ = 10",
    },
    features: {
      eyebrow: "Perché Optees",
      title: "Un'ottimizzazione che si spiega da sola",
      body:
        "La maggior parte dei solver ti restituisce un numero. Optees ti restituisce il modello, la soluzione e il ragionamento dietro di essa — pensato per team, studenti e analisti.",
      items: [
        {
          id: "assistant",
          title: "Assistente di modellazione locale",
          body:
            "Un algoritmo deterministico di riconoscimento di pattern lavora interamente sul dispositivo. Non usa modelli AI, LLM o servizi cloud: raccomanda un flusso e puo' validare bozze strutturate esplicite prima del caricamento.",
        },
        {
          id: "educational",
          title: "Viste didattiche della soluzione",
          body:
            "Leggi stati, comportamento dell'obiettivo, range ottimi, percorsi, grafici e note in linguaggio semplice. I risultati NLP distinguono esplicitamente un candidato numerico locale da un ottimo provato.",
        },
        {
          id: "variants",
          title: "Cinque varianti Knapsack",
          body:
            "Passa tra modelli 0/1, bounded, unbounded, fractional e multi-dimensional in un unico flusso di lavoro coerente.",
        },
        {
          id: "benchmarks",
          title: "Validato su benchmark",
          body:
            "LP e MILP usano regressioni Netlib e MIPLIB. Knapsack include casi Burkardt e OR-Library; NLP, regressione, classificazione e grafi usano casi analitici o deterministici documentati.",
        },
        {
          id: "local",
          title: "Privato per definizione",
          body:
            "Tutto gira sul tuo computer. Nessun account, nessun upload, nessun cloud: i tuoi dati non lasciano mai il desktop.",
        },
        {
          id: "openSource",
          title: "Open source",
          body:
            "Rilasciato con licenza aperta. Leggi il codice, apri issue, segui la roadmap e contribuisci a decidere il futuro di Optees.",
        },
      ],
    },
    algorithms: {
      eyebrow: "Algoritmi",
      title: "Un ambiente mirato per l'ottimizzazione",
      body:
        "Ogni famiglia di algoritmi segue lo stesso percorso: formulare il modello, risolverlo con un motore affidabile e poi ispezionare il comportamento numerico e matematico del risultato.",
      tabsAria: "Famiglie di algoritmi",
      modelLabel: "Modello",
      capabilitiesLabel: "In questa build",
      items: [
        {
          id: "lp",
          label: "Programmazione Lineare",
          short: "LP",
          status: "Disponibile",
          formula: "max cᵀx  s.t.  Ax ≤ b,  x ≥ 0",
          description:
            "Ottimizzazione continua con limiti, vincoli, import JSON e analisi dei range per gli ottimi alternativi.",
          details: ["Backend HiGHS", "Range di ottimi multipli", "Testato su Netlib"],
          preview: "lpSolution",
        },
        {
          id: "milp",
          label: "Programmazione Lineare Intera Mista",
          short: "MILP",
          status: "Disponibile",
          formula: "max cᵀx  s.t.  Ax ≤ b,  xⱼ ∈ ℤ",
          description:
            "Variabili intere, binarie e continue insieme, con controlli del solver per limite di tempo e MIP gap.",
          details: ["CP-SAT / CBC", "Stato ammissibile", "Dataset MIPLIB"],
          preview: "home",
        },
        {
          id: "knapsack",
          label: "Knapsack",
          short: "KP",
          status: "Disponibile",
          formula: "max Σ vᵢ·xᵢ  s.t.  Σ wᵢ·xᵢ ≤ W",
          description:
            "Varianti 0/1, bounded, unbounded, fractional e multi-dimensional unificate in un unico flusso con import JSON.",
          details: ["Import JSON", "Grafici di capacità", "Switch variante"],
          preview: "knapsackSolution",
        },
        {
          id: "nlp",
          label: "Programmazione Non Lineare",
          short: "NLP",
          status: "Disponibile",
          formula: "min f(x)  s.t.  gᵢ(x) ≤ 0",
          description:
            "Ottimizzazione scalare continua con espressioni sicure, punto iniziale e bounds opzionali. Il risultato e' un candidato numerico locale onesto, non una prova di ottimo globale.",
          details: ["BFGS / Nelder-Mead / L-BFGS-B", "Parser di espressioni sicuro", "Viste obiettivo 2D e 3D"],
          preview: "nlpSolution",
        },
        {
          id: "regression",
          label: "Regressione Lineare",
          short: "REG",
          status: "Disponibile",
          formula: "y_hat = beta_0 + Σ beta_j x_j",
          description:
            "Regressione OLS e Ridge didattica per target continui, con divisione training/test deterministica, coefficienti appresi, residui e metriche sulle righe lasciate fuori.",
          details: ["OLS e Ridge", "MAE / MSE / RMSE / R-quadrato", "Addestramento numerico locale"],
          preview: "regressionSolution",
        },
        {
          id: "classification",
          label: "Classificazione binaria",
          short: "CLS",
          status: "Disponibile",
          formula: "P(y = 1 | x) = 1 / (1 + e^(-beta_0 - beta^T x))",
          description:
            "Regressione logistica locale didattica per due classi nominate, con valutazione separata stratificata, matrici di confusione, probabilita' previste e un confine decisionale 2D opzionale.",
          details: ["Regressione logistica", "Accuracy / Precision / Recall / F1", "Standardizzazione solo training"],
          preview: "classificationSolution",
        },
        {
          id: "graph",
          label: "Teoria dei Grafi: Dijkstra",
          short: "DSP",
          status: "Disponibile",
          formula: "min Σ w(u, v) lungo un cammino s → t,  w(u, v) ≥ 0",
          description:
            "Trova il percorso minimo in grafi pesati diretti o non diretti con sorgente e destinazione, poi ispeziona il percorso evidenziato, il costo totale e la traccia dei nodi stabilizzati.",
          details: ["Dijkstra locale deterministico", "Import/export JSON", "Visualizzazione del percorso"],
          preview: "graphSolution",
        },
      ],
    },
    machineLearning: {
      eyebrow: "AI e Machine Learning",
      title: "Impara dai dati senza nascondere il metodo",
      body:
        "Optees tratta il machine learning didattico come un flusso locale e trasparente: definisci una tabella numerica, mantieni riproducibile la divisione training/test, ispeziona il risultato lasciato fuori e separa le previsioni dalle conclusioni causali.",
      assistant: {
        title: "Prepara dati strutturati in locale",
        body:
          "L'Assistente di modellazione e' un algoritmo deterministico di riconoscimento di pattern, non un'AI generativa né un servizio cloud. Puo' raccomandare Regressione o Classificazione binaria da testo libero, poi prepara un dataset caricabile solo dopo che dichiari esplicitamente le colonne e fornisci righe separate da |; lo stesso importer della form valida la bozza prima che possa sostituire il tuo lavoro.",
      },
      workflows: [
        {
          title: "Regressione Lineare",
          body:
            "Adatta modelli OLS o Ridge per un target numerico continuo, poi confronta errori di training e su righe lasciate fuori invece di fidarti di una sola retta stimata.",
          points: ["OLS e Ridge", "MAE, MSE, RMSE, R-quadrato", "Coefficienti e residui"],
          preview: "regressionSolution",
        },
        {
          title: "Classificazione Binaria",
          body:
            "Addestra regressione logistica locale per esattamente due esiti nominati e ispeziona gli errori ricevuti da ciascuna classe prima di trattare il modello come utile.",
          points: ["Split stratificato", "Precision, recall, F1", "Matrice di confusione e confine 2D"],
          preview: "classificationSolution",
        },
      ],
    },
    previews: {
      eyebrow: "Esplora l'app",
      title: "Segui ogni passaggio del metodo",
      body:
        "Ogni ambiente si concentra su una parte del percorso di apprendimento: formula il modello, esegui un metodo locale e ispeziona come e' stato ottenuto il risultato.",
      items: [
        {
          id: "assistant",
          window: "Optees — Assistente di modellazione",
          title: "Descrivi la decisione con parole tue",
          body: "L'assistente usa pattern linguistici deterministici in locale per raccomandare una famiglia di solver. Non chiama modelli AI e non invia la descrizione fuori da Optees; dati espliciti possono diventare una bozza JSON validata dall'importer.",
          alt: "Assistente di modellazione locale di Optees che raccomanda Knapsack e genera JSON validato",
        },
        {
          id: "lpSolution",
          window: "Optees — Soluzione LP",
          title: "Analizza il comportamento della soluzione",
          body: "Le soluzioni LP includono controlli sull'obiettivo, range ottimi e il grafico della regione ammissibile con il punto ottimo.",
          alt: "Vista soluzione di programmazione lineare in Optees con grafici e regione ammissibile",
        },
        {
          id: "knapsack",
          window: "Optees — Setup Knapsack",
          title: "Modella Knapsack in modo visivo",
          body: "Scegli una variante, imposta la capacità e descrivi gli oggetti in una tabella strutturata — nessuna formula da scrivere a mano.",
          alt: "Vista di impostazione del problema Knapsack in Optees con oggetti e capacità",
        },
        {
          id: "knapsackSolution",
          window: "Optees — Soluzione Knapsack",
          title: "Leggi il risultato a colpo d'occhio",
          body: "Uso della capacità, oggetti selezionati e grafici valore/peso sono accanto alla tabella delle decisioni.",
          alt: "Vista soluzione Knapsack in Optees con uso della capacità e grafici dei valori",
        },
        {
          id: "nlpSolution",
          window: "Optees — Soluzione NLP",
          title: "Ispeziona il comportamento numerico locale",
          body: "Visualizza il punto candidato, lo stato di arresto e il paesaggio dell'obiettivo. La vista rende esplicita la natura locale dell'ottimizzazione numerica.",
          alt: "Vista soluzione di programmazione non lineare in Optees con dettagli del candidato e grafico dell'obiettivo",
        },
        {
          id: "regressionSolution",
          window: "Optees — Risultato regressione",
          title: "Valuta una previsione trasparente",
          body: "Ispeziona coefficienti, metriche per partizione, residui e retta stimata senza trattare un piccolo dataset come una conclusione causale.",
          alt: "Vista soluzione di regressione lineare in Optees con coefficienti appresi, metriche, residui e retta stimata",
        },
        {
          id: "classificationSolution",
          window: "Optees — Risultato classificazione",
          title: "Ispeziona un confine decisionale binario",
          body: "Controlla classi, metriche sulle righe lasciate fuori, matrici di confusione, probabilita' e un confine 2D senza confondere un piccolo modello locale con un sistema decisionale di produzione.",
          alt: "Vista soluzione di classificazione binaria in Optees con coefficienti, matrice di confusione, metriche e confine decisionale",
        },
        {
          id: "graphSolution",
          window: "Optees — Soluzione Dijkstra",
          title: "Segui il percorso minimo",
          body: "Il cammino scelto e' disegnato sul grafo con la distanza totale e la traccia deterministica dei nodi stabilizzati da Dijkstra.",
          alt: "Vista soluzione di cammino minimo Dijkstra in Optees con percorso evidenziato",
        },
      ],
    },
    workflow: {
      eyebrow: "Come funziona",
      title: "Dal modello alla spiegazione in tre passi",
      body: "Lo stesso ciclo intuitivo, qualunque cosa tu stia ottimizzando.",
      steps: [
        {
          number: "01",
          title: "Formula",
          body: "Inserisci variabili, bounds, obiettivi, vincoli, oggetti Knapsack o un grafo pesato — oppure importa un modello JSON versionato.",
        },
        {
          number: "02",
          title: "Risolvi",
          body: "Esegui il motore locale adatto: SciPy/HiGHS, OR-Tools, un solver Knapsack dedicato, un metodo numerico SciPy o Dijkstra.",
        },
        {
          number: "03",
          title: "Ispeziona",
          body: "Leggi stato esatto o numerico, valore obiettivo, variabili selezionate, percorsi, grafici e note didattiche che spiegano il risultato.",
        },
      ],
    },
    download: {
      eyebrow: "Download",
      title: "Porta Optees sul tuo desktop",
      body:
        "Le build pacchettizzate sono pubblicate su GitHub Releases. Installa una volta e l'app può controllare gli aggiornamenti e guidarti al nuovo installer.",
      latestRelease: "Ultima release: {version}",
      fallbackRelease: "Apri GitHub per vedere l'ultima release",
      checkingRelease: "Controllo dell'ultima release…",
      downloadFor: "Scarica per {platform}",
      downloadGeneric: "Scarica per desktop",
      otherVersions: "Altre piattaforme",
      allReleases: "Tutte le release su GitHub",
      menuAria: "Scegli la tua piattaforma",
      yourSystem: "rilevato",
      platformNames: { mac: "macOS", windows: "Windows", linux: "Linux" },
      assetsButton: "Tutte le piattaforme e gli asset",
      platformsLabel: "Disponibile per",
      platforms: ["macOS", "Windows", "Linux"],
      gatekeeperNote:
        "Le build non sono firmate: macOS può chiedere la conferma standard di Gatekeeper, mentre Windows/Linux la consueta approvazione al primo avvio.",
    },
    faq: {
      eyebrow: "FAQ",
      title: "Le risposte alle tue domande",
      body: "Tutto ciò che ti serve sapere prima della tua prima ottimizzazione.",
      items: [
        {
          q: "Cos'è Optees?",
          a: "Optees e' un'app desktop gratuita e open source per ricerca operativa e machine learning didattico. Puoi modellare, risolvere e ispezionare LP, MILP, cinque varianti Knapsack, Programmazione Non Lineare continua, Regressione Lineare, Classificazione Binaria e cammini minimi di Dijkstra senza scrivere codice.",
        },
        {
          q: "A chi è rivolto?",
          a: "Ad analisti e aziende che devono prendere decisioni migliori su risorse, scheduling e logistica, e a studenti o docenti che vogliono vedere la matematica dietro ogni soluzione.",
        },
        {
          q: "È davvero gratuito?",
          a: "Sì. Optees è completamente gratuito e rilasciato con licenza open source. Le build desktop sono disponibili su GitHub Releases.",
        },
        {
          q: "Quali piattaforme sono supportate?",
          a: "Optees è multipiattaforma e gira su macOS, Windows e Linux.",
        },
        {
          q: "Devo saper programmare?",
          a: "No. Un assistente guidato ti aiuta a scegliere l'algoritmo giusto e a inserire input strutturati, così ottimizzi senza scrivere codice.",
        },
        {
          q: "Cosa arriverà in futuro?",
          a: "La roadmap aggiunge ora clustering trasparente alla sezione didattica di AI e machine learning, poi euristiche e metaeuristiche, mentre il rafforzamento dei benchmark prosegue sulle famiglie gia' rilasciate.",
        },
      ],
    },
    footer: {
      product: "Optees",
      claim: "Toolkit open source per l'ottimizzazione",
      tagline: "Modella, risolvi e comprendi problemi di ottimizzazione — in locale e gratis.",
      columns: [
        {
          title: "Prodotto",
          links: [
            { label: "Perché Optees", key: "#features" },
            { label: "Algoritmi", key: "#algorithms" },
            { label: "Schermate", key: "#previews" },
            { label: "Download", key: "#download" },
          ],
        },
        {
          title: "Progetto",
          links: [
            { label: "Repository GitHub", key: "repo" },
            { label: "Release", key: "releases" },
            { label: "Roadmap", key: "roadmap" },
            { label: "Issue", key: "issues" },
          ],
        },
      ],
      socialAria: "Link social",
      madeBy: "Sito personale di Paolo Pietrelli",
      copyright: "© {year} Paolo Pietrelli · Tutti i diritti riservati",
      license: "Licenza Apache 2.0",
    },
  },
};
