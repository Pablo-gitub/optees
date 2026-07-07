export type Language = "en" | "it";
export type AlgorithmId = "lp" | "milp" | "knapsack" | "nlp";
export type PreviewId = "home" | "lpSolution" | "knapsack" | "knapsackSolution";
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
      title: "Optees — Open-Source Optimization Software for LP, MILP & Knapsack",
      description:
        "Free, open-source desktop app that makes operations research accessible. Model, solve and visualize Linear Programming, Mixed-Integer and Knapsack problems locally, with a guided assistant and educational solution views.",
      ogDescription:
        "Model, solve and visualize LP, MILP and Knapsack problems from a private, local desktop app. Free and open source.",
    },
    nav: {
      aria: "Primary navigation",
      brandAria: "Optees home",
      sectionsAria: "Page sections",
      features: "Why Optees",
      algorithms: "Algorithms",
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
        "Optees turns powerful optimization algorithms into a desktop app anyone can use. Model Linear Programming, Mixed-Integer and Knapsack problems, solve them with industry-grade engines, and understand every result — no scripting required.",
      source: "Star on GitHub",
      stackLabel: "Powered by",
      stack: ["SciPy", "HiGHS", "OR-Tools", "CP-SAT", "Netlib", "MIPLIB"],
      metricsAria: "Project highlights",
      metrics: [
        { value: "3", label: "Solver families, ready to use" },
        { value: "5", label: "Knapsack variants in one flow" },
        { value: "100%", label: "Local & private, no cloud" },
        { value: "MIT", label: "Free and open source" },
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
          title: "Guided assistant",
          body:
            "A built-in chatbot helps you pick the right algorithm for your problem and set up the model — even without an operations-research background.",
        },
        {
          id: "educational",
          title: "Educational solution views",
          body:
            "Every result comes with status, objective breakdown, optimal ranges, charts and plain-language notes, so you learn while you solve.",
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
            "Solvers are validated against scientific datasets like Netlib and MIPLIB, so you can trust the numbers you ship.",
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
          status: "On the roadmap",
          formula: "min f(x)  s.t.  gᵢ(x) ≤ 0",
          description:
            "Unconstrained, bounded, constrained, least-squares and minimax optimization — coming in a future release.",
          details: ["SciPy minimize", "Curve fitting", "Global methods later"],
          preview: "home",
        },
      ],
    },
    previews: {
      eyebrow: "Product tour",
      title: "Real screens, not abstract mockups",
      body:
        "These are actual views from the desktop app, so you know exactly what you get before you download.",
      items: [
        {
          id: "home",
          window: "Optees — Home",
          title: "Choose your method",
          body: "Build LP, MILP and Knapsack problems from a clear catalogue of methods instead of ad-hoc scripts.",
          alt: "Optees desktop home view listing optimization algorithms",
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
          body: "Enter variables, bounds, objective functions, constraints or Knapsack items — or import them from JSON.",
        },
        {
          number: "02",
          title: "Solve",
          body: "Run proven engines: SciPy/HiGHS for LP, OR-Tools for MILP, and dedicated dynamic-programming solvers for Knapsack.",
        },
        {
          number: "03",
          title: "Inspect",
          body: "Read the status, objective value, selected variables, charts and educational notes that explain the result.",
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
      downloadGeneric: "Download the app",
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
          a: "Optees is a free, open-source desktop app that makes operations research approachable. You can model, solve and inspect Linear Programming, Mixed-Integer Linear Programming and Knapsack problems without writing code.",
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
          a: "The roadmap focuses on stronger Knapsack benchmarks and a first Nonlinear Programming workflow, followed by graph and machine-learning methods.",
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
      license: "MIT-style license",
    },
  },
  it: {
    meta: {
      title: "Optees — Software di Ottimizzazione Open Source per LP, MILP e Knapsack",
      description:
        "App desktop gratuita e open source che rende accessibile la ricerca operativa. Modella, risolvi e visualizza problemi di Programmazione Lineare, Intera Mista e Knapsack in locale, con un assistente guidato e viste didattiche della soluzione.",
      ogDescription:
        "Modella, risolvi e visualizza problemi LP, MILP e Knapsack da un'app desktop locale e privata. Gratuita e open source.",
    },
    nav: {
      aria: "Navigazione principale",
      brandAria: "Home di Optees",
      sectionsAria: "Sezioni della pagina",
      features: "Perché Optees",
      algorithms: "Algoritmi",
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
        "Optees trasforma potenti algoritmi di ottimizzazione in un'app desktop alla portata di tutti. Modella problemi di Programmazione Lineare, Intera Mista e Knapsack, risolvili con motori di livello professionale e comprendi ogni risultato — senza scrivere codice.",
      source: "Metti una stella su GitHub",
      stackLabel: "Basato su",
      stack: ["SciPy", "HiGHS", "OR-Tools", "CP-SAT", "Netlib", "MIPLIB"],
      metricsAria: "Punti chiave del progetto",
      metrics: [
        { value: "3", label: "Famiglie di solver pronte all'uso" },
        { value: "5", label: "Varianti Knapsack in un solo flusso" },
        { value: "100%", label: "Locale e privato, nessun cloud" },
        { value: "MIT", label: "Gratuito e open source" },
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
          title: "Assistente guidato",
          body:
            "Un chatbot integrato ti aiuta a scegliere l'algoritmo giusto per il tuo problema e a impostare il modello — anche senza basi di ricerca operativa.",
        },
        {
          id: "educational",
          title: "Viste didattiche della soluzione",
          body:
            "Ogni risultato mostra stato, scomposizione dell'obiettivo, range ottimi, grafici e note in linguaggio semplice: impari mentre risolvi.",
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
            "I solver sono verificati su dataset scientifici come Netlib e MIPLIB, così puoi fidarti dei numeri che ottieni.",
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
          status: "In roadmap",
          formula: "min f(x)  s.t.  gᵢ(x) ≤ 0",
          description:
            "Ottimizzazione non vincolata, con bounds, vincolata, least-squares e minimax — in arrivo in una release futura.",
          details: ["SciPy minimize", "Curve fitting", "Metodi globali futuri"],
          preview: "home",
        },
      ],
    },
    previews: {
      eyebrow: "Tour del prodotto",
      title: "Schermate reali, non mockup astratti",
      body:
        "Queste sono viste effettive dell'app desktop, così sai esattamente cosa ottieni prima di scaricarla.",
      items: [
        {
          id: "home",
          window: "Optees — Home",
          title: "Scegli il tuo metodo",
          body: "Costruisci problemi LP, MILP e Knapsack da un catalogo chiaro di metodi, invece di script improvvisati.",
          alt: "Vista home desktop di Optees con l'elenco degli algoritmi di ottimizzazione",
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
          body: "Inserisci variabili, bounds, funzione obiettivo, vincoli o oggetti Knapsack — oppure importali da JSON.",
        },
        {
          number: "02",
          title: "Risolvi",
          body: "Esegui motori affidabili: SciPy/HiGHS per LP, OR-Tools per MILP e solver di programmazione dinamica dedicati per Knapsack.",
        },
        {
          number: "03",
          title: "Ispeziona",
          body: "Leggi stato, valore obiettivo, variabili selezionate, grafici e note didattiche che spiegano il risultato.",
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
      downloadGeneric: "Scarica l'app",
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
          a: "Optees è un'app desktop gratuita e open source che rende accessibile la ricerca operativa. Puoi modellare, risolvere e ispezionare problemi di Programmazione Lineare, Intera Mista e Knapsack senza scrivere codice.",
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
          a: "La roadmap punta su benchmark Knapsack più solidi e su un primo flusso di Programmazione Non Lineare, seguiti da metodi su grafi e machine learning.",
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
      license: "Licenza in stile MIT",
    },
  },
};
