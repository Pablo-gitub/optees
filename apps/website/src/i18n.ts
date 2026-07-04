export type Language = "en" | "it";
export type AlgorithmId = "lp" | "milp" | "knapsack" | "nlp";
export type PreviewId = "home" | "lpSolution" | "knapsack" | "knapsackSolution";

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
  status: string;
  description: string;
  details: string[];
};

type PreviewCopy = {
  id: PreviewId;
  title: string;
  body: string;
  alt: string;
};

type WorkflowStepCopy = {
  number: string;
  title: string;
  body: string;
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
    algorithms: string;
    previews: string;
    download: string;
    roadmap: string;
    github: string;
  };
  language: {
    aria: string;
    label: string;
    options: Record<Language, string>;
  };
  hero: {
    eyebrow: string;
    title: string;
    copy: string;
    download: string;
    source: string;
    metricsAria: string;
    metrics: Array<{
      value: string;
      label: string;
    }>;
  };
  algorithms: {
    eyebrow: string;
    title: string;
    body: string;
    tabsAria: string;
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
    steps: WorkflowStepCopy[];
  };
  download: {
    eyebrow: string;
    title: string;
    body: string;
    latestRelease: string;
    fallbackRelease: string;
    checkingRelease: string;
    macButton: string;
    assetsButton: string;
    gatekeeperNote: string;
  };
  roadmap: {
    eyebrow: string;
    title: string;
    body: string;
    project: string;
    issues: string;
    releases: string;
  };
  footer: {
    product: string;
    claim: string;
    repository: string;
  };
};

export const copy: Record<Language, SiteCopy> = {
  en: {
    meta: {
      title: "Optees - Desktop Optimization Toolkit",
      description:
        "Open-source desktop app for LP, MILP and Knapsack optimization with educational solution views, JSON import and scientific benchmark tests.",
      ogDescription:
        "Model, solve and inspect LP, MILP and Knapsack problems from a local desktop app.",
    },
    nav: {
      aria: "Primary navigation",
      brandAria: "Optees home",
      sectionsAria: "Page sections",
      algorithms: "Algorithms",
      previews: "Previews",
      download: "Download",
      roadmap: "Roadmap",
      github: "GitHub",
    },
    language: {
      aria: "Language selection",
      label: "Language",
      options: {
        en: "English",
        it: "Italiano",
      },
    },
    hero: {
      eyebrow: "Open-source desktop optimization toolkit",
      title: "Model, solve and inspect optimization problems locally.",
      copy:
        "Optees brings Linear Programming, Mixed-Integer Linear Programming and Knapsack workflows into a desktop interface with educational explanations, JSON import and benchmark-backed tests.",
      download: "Download latest release",
      source: "View source",
      metricsAria: "Project highlights",
      metrics: [
        { value: "LP", label: "optimal ranges" },
        { value: "MILP", label: "integer models" },
        { value: "5", label: "knapsack variants" },
      ],
    },
    algorithms: {
      eyebrow: "Algorithms",
      title: "A focused optimization workbench",
      body:
        "Each algorithm family is built around the same path: formulate the model, solve it, then inspect the numerical and mathematical behavior of the result.",
      tabsAria: "Algorithm families",
      items: [
        {
          id: "lp",
          label: "Linear Programming",
          status: "Implemented",
          description:
            "Continuous optimization with bounds, constraints, JSON import and optimal-range analysis.",
          details: ["HiGHS backend", "Multiple optima ranges", "Netlib-tested"],
        },
        {
          id: "milp",
          label: "Mixed-Integer Linear Programming",
          status: "Implemented",
          description:
            "Integer, binary and continuous variables with solver controls for time limits and MIP gap.",
          details: ["CP-SAT/CBC", "Feasible status", "MIPLIB dataset"],
        },
        {
          id: "knapsack",
          label: "Knapsack",
          status: "Implemented",
          description:
            "0/1, bounded, unbounded, fractional and multi-dimensional variants in one workflow.",
          details: ["JSON import", "Capacity charts", "Variant switch"],
        },
        {
          id: "nlp",
          label: "Nonlinear Programming",
          status: "Roadmap",
          description:
            "Unconstrained, bounded, constrained, least-squares and minimax optimization.",
          details: ["SciPy minimize", "Curve fitting", "Global methods later"],
        },
      ],
    },
    previews: {
      eyebrow: "Result previews",
      title: "Use real views, not abstract diagrams",
      body:
        "The landing page uses screenshots from the desktop app so users immediately see the actual modeling and solution surfaces they will download.",
      items: [
        {
          id: "home",
          title: "Formulate optimization models",
          body: "Build LP, MILP and Knapsack problems with structured inputs instead of ad-hoc scripts.",
          alt: "Optees desktop home view with optimization algorithms",
        },
        {
          id: "lpSolution",
          title: "Inspect solution behavior",
          body: "LP solutions include objective checks and ranges for alternate optima when available.",
          alt: "Optees linear programming solution view",
        },
        {
          id: "knapsack",
          title: "Compare Knapsack variants",
          body: "Switch between 0/1, bounded, unbounded, fractional and multi-dimensional models.",
          alt: "Optees Knapsack formulation view",
        },
        {
          id: "knapsackSolution",
          title: "Read the result visually",
          body: "Capacity usage, selected objects and value-density charts are shown next to the table.",
          alt: "Optees Knapsack solution view with charts",
        },
      ],
    },
    workflow: {
      eyebrow: "Workflow",
      title: "From model to explanation",
      steps: [
        {
          number: "01",
          title: "Formulate",
          body: "Enter variables, bounds, objective functions, constraints or Knapsack items.",
        },
        {
          number: "02",
          title: "Solve",
          body: "Use SciPy/HiGHS, OR-Tools or dedicated dynamic programming adapters.",
        },
        {
          number: "03",
          title: "Inspect",
          body: "Read status, objective value, selected variables, charts and educational notes.",
        },
      ],
    },
    download: {
      eyebrow: "Download",
      title: "Install the latest desktop build",
      body:
        "Releases are published on GitHub. Packaged builds can check for updates and guide the user to the newest installer when one is available.",
      latestRelease: "Latest release: {version}",
      fallbackRelease: "Latest release: open GitHub to check",
      checkingRelease: "Checking latest release...",
      macButton: "Download for macOS",
      assetsButton: "All release assets",
      gatekeeperNote:
        "Unsigned macOS builds may require the standard Gatekeeper manual confirmation from System Settings.",
    },
    roadmap: {
      eyebrow: "Roadmap",
      title: "Next: stronger benchmarks and nonlinear programming",
      body:
        "The next phase focuses on scientific Knapsack benchmarks, a first Nonlinear Programming workflow and a dedicated public website deployment pipeline.",
      project: "Project roadmap",
      issues: "Issues and planning",
      releases: "Release history",
    },
    footer: {
      product: "Optees",
      claim: "Open-source optimization toolkit",
      repository: "GitHub repository",
    },
  },
  it: {
    meta: {
      title: "Optees - Toolkit Desktop per l'Ottimizzazione",
      description:
        "Applicazione desktop open source per ottimizzazione LP, MILP e Knapsack con viste didattiche della soluzione, import JSON e test su benchmark scientifici.",
      ogDescription:
        "Modella, risolvi e analizza problemi LP, MILP e Knapsack da un'app desktop locale.",
    },
    nav: {
      aria: "Navigazione principale",
      brandAria: "Home di Optees",
      sectionsAria: "Sezioni della pagina",
      algorithms: "Algoritmi",
      previews: "Anteprime",
      download: "Download",
      roadmap: "Roadmap",
      github: "GitHub",
    },
    language: {
      aria: "Selezione lingua",
      label: "Lingua",
      options: {
        en: "English",
        it: "Italiano",
      },
    },
    hero: {
      eyebrow: "Toolkit desktop open source per l'ottimizzazione",
      title: "Modella, risolvi e analizza problemi di ottimizzazione in locale.",
      copy:
        "Optees porta Programmazione Lineare, Programmazione Lineare Intera Mista e Knapsack dentro un'interfaccia desktop con spiegazioni didattiche, import JSON e test basati su benchmark.",
      download: "Scarica l'ultima release",
      source: "Vedi sorgente",
      metricsAria: "Punti chiave del progetto",
      metrics: [
        { value: "LP", label: "range ottimi" },
        { value: "MILP", label: "modelli interi" },
        { value: "5", label: "varianti knapsack" },
      ],
    },
    algorithms: {
      eyebrow: "Algoritmi",
      title: "Un ambiente mirato per l'ottimizzazione",
      body:
        "Ogni famiglia di algoritmi segue lo stesso percorso: formulare il modello, risolverlo e poi ispezionare il comportamento numerico e matematico del risultato.",
      tabsAria: "Famiglie di algoritmi",
      items: [
        {
          id: "lp",
          label: "Programmazione Lineare",
          status: "Implementato",
          description:
            "Ottimizzazione continua con limiti, vincoli, import JSON e analisi dei range di soluzioni ottime.",
          details: ["Backend HiGHS", "Range di ottimi multipli", "Test Netlib"],
        },
        {
          id: "milp",
          label: "Programmazione Lineare Intera Mista",
          status: "Implementato",
          description:
            "Variabili intere, binarie e continue con opzioni solver per limite di tempo e MIP gap.",
          details: ["CP-SAT/CBC", "Stato ammissibile", "Dataset MIPLIB"],
        },
        {
          id: "knapsack",
          label: "Knapsack",
          status: "Implementato",
          description:
            "Varianti 0/1, bounded, unbounded, fractional e multi-dimensional in un unico flusso.",
          details: ["Import JSON", "Grafici di capacita'", "Switch variante"],
        },
        {
          id: "nlp",
          label: "Programmazione Non Lineare",
          status: "Roadmap",
          description:
            "Ottimizzazione non vincolata, con bounds, vincolata, least-squares e minimax.",
          details: ["SciPy minimize", "Curve fitting", "Metodi globali futuri"],
        },
      ],
    },
    previews: {
      eyebrow: "Anteprime risultati",
      title: "Viste reali, non diagrammi astratti",
      body:
        "La landing usa screenshot dell'app desktop, cosi' chi visita il sito vede subito le superfici reali di modellazione e soluzione che andra' a scaricare.",
      items: [
        {
          id: "home",
          title: "Formula modelli di ottimizzazione",
          body: "Costruisci problemi LP, MILP e Knapsack con input strutturati invece di script ad hoc.",
          alt: "Home desktop di Optees con gli algoritmi di ottimizzazione",
        },
        {
          id: "lpSolution",
          title: "Analizza il comportamento della soluzione",
          body: "Le soluzioni LP includono controlli sull'obiettivo e range degli ottimi alternativi quando disponibili.",
          alt: "Vista soluzione di programmazione lineare in Optees",
        },
        {
          id: "knapsack",
          title: "Confronta le varianti Knapsack",
          body: "Passa tra modelli 0/1, bounded, unbounded, fractional e multi-dimensional.",
          alt: "Vista di formulazione Knapsack in Optees",
        },
        {
          id: "knapsackSolution",
          title: "Leggi il risultato in modo visivo",
          body: "Uso della capacita', oggetti selezionati e grafici valore/peso sono mostrati accanto alla tabella.",
          alt: "Vista soluzione Knapsack in Optees con grafici",
        },
      ],
    },
    workflow: {
      eyebrow: "Flusso",
      title: "Dal modello alla spiegazione",
      steps: [
        {
          number: "01",
          title: "Formula",
          body: "Inserisci variabili, bounds, funzione obiettivo, vincoli o oggetti Knapsack.",
        },
        {
          number: "02",
          title: "Risolvi",
          body: "Usa SciPy/HiGHS, OR-Tools o adattatori dedicati di programmazione dinamica.",
        },
        {
          number: "03",
          title: "Ispeziona",
          body: "Leggi stato, valore obiettivo, variabili selezionate, grafici e note didattiche.",
        },
      ],
    },
    download: {
      eyebrow: "Download",
      title: "Installa l'ultima build desktop",
      body:
        "Le release sono pubblicate su GitHub. Le build pacchettizzate possono controllare gli aggiornamenti e guidare l'utente verso il nuovo installer quando disponibile.",
      latestRelease: "Ultima release: {version}",
      fallbackRelease: "Ultima release: apri GitHub per controllare",
      checkingRelease: "Controllo ultima release...",
      macButton: "Scarica per macOS",
      assetsButton: "Tutti gli asset della release",
      gatekeeperNote:
        "Le build macOS non firmate possono richiedere la conferma manuale standard di Gatekeeper dalle Impostazioni di Sistema.",
    },
    roadmap: {
      eyebrow: "Roadmap",
      title: "Prossimo passo: benchmark piu' forti e programmazione non lineare",
      body:
        "La prossima fase si concentra su benchmark scientifici Knapsack, un primo flusso di Programmazione Non Lineare e una pipeline dedicata per il sito pubblico.",
      project: "Roadmap progetto",
      issues: "Issue e pianificazione",
      releases: "Storico release",
    },
    footer: {
      product: "Optees",
      claim: "Toolkit open source per l'ottimizzazione",
      repository: "Repository GitHub",
    },
  },
};
