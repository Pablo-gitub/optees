import { useEffect, useMemo, useState } from "react";
import {
  copy,
  detectLanguage,
  formatMessage,
  supportedLanguages,
  type PreviewId,
  type Language,
} from "./i18n";

const repositoryUrl = "https://github.com/Pablo-gitub/optees";
const releasesUrl = `${repositoryUrl}/releases`;
const latestReleaseApi = "https://api.github.com/repos/Pablo-gitub/optees/releases/latest";
const assetUrl = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\//, "")}`;

type ReleaseAsset = {
  name: string;
  browser_download_url: string;
};

type ReleaseInfo = {
  tag_name: string;
  html_url: string;
  assets: ReleaseAsset[];
};

const languageStorageKey = "optees.website.language";

const previewAssets: Record<PreviewId, string> = {
  home: "screenshots/optees-home.png",
  lpSolution: "screenshots/optees-lp-solution.png",
  knapsack: "screenshots/optees-knapsack.png",
  knapsackSolution: "screenshots/optees-knapsack-solution.png",
};

function getInitialLanguage(): Language {
  const stored = window.localStorage.getItem(languageStorageKey);
  if (stored === "en" || stored === "it") {
    return stored;
  }
  return detectLanguage(window.navigator.language);
}

function setMetaContent(selector: string, value: string): void {
  const element = document.querySelector<HTMLMetaElement>(selector);
  if (element) {
    element.content = value;
  }
}

function App() {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const t = copy[language];
  const [activeAlgorithm, setActiveAlgorithm] = useState(t.algorithms.items[0].id);
  const [release, setRelease] = useState<ReleaseInfo | null>(null);
  const [releaseError, setReleaseError] = useState(false);

  useEffect(() => {
    window.localStorage.setItem(languageStorageKey, language);
    document.documentElement.lang = language;
    document.title = t.meta.title;
    setMetaContent('meta[name="description"]', t.meta.description);
    setMetaContent('meta[property="og:title"]', t.meta.title);
    setMetaContent('meta[property="og:description"]', t.meta.ogDescription);
  }, [language, t]);

  useEffect(() => {
    let cancelled = false;
    fetch(latestReleaseApi, { headers: { Accept: "application/vnd.github+json" } })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`GitHub returned ${response.status}`);
        }
        return response.json() as Promise<ReleaseInfo>;
      })
      .then((data) => {
        if (!cancelled) {
          setRelease(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setReleaseError(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const algorithms = t.algorithms.items;

  const selectedAlgorithm = useMemo(
    () => algorithms.find((algorithm) => algorithm.id === activeAlgorithm) ?? algorithms[0],
    [activeAlgorithm],
  );

  const screenshots = t.previews.items.map((shot) => ({
    ...shot,
    src: assetUrl(previewAssets[shot.id]),
  }));

  const macAsset = release?.assets.find((asset) =>
    /\.(dmg|pkg|zip)$/i.test(asset.name) && /mac|darwin|osx|optees/i.test(asset.name),
  );

  const releaseLabel = release
    ? formatMessage(t.download.latestRelease, { version: release.tag_name })
    : releaseError
      ? t.download.fallbackRelease
      : t.download.checkingRelease;

  return (
    <div className="site-shell">
      <header className="topbar" aria-label={t.nav.aria}>
        <a className="brand" href="#top" aria-label={t.nav.brandAria}>
          <span className="brand-mark" aria-hidden="true">
            O
          </span>
          <span>{t.footer.product}</span>
        </a>
        <nav className="nav-links" aria-label={t.nav.sectionsAria}>
          <a href="#algorithms">{t.nav.algorithms}</a>
          <a href="#previews">{t.nav.previews}</a>
          <a href="#download">{t.nav.download}</a>
          <a href="#roadmap">{t.nav.roadmap}</a>
        </nav>
        <div className="language-switch" aria-label={t.language.aria}>
          <span>{t.language.label}</span>
          {supportedLanguages.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={language === option}
              className={language === option ? "active" : ""}
              onClick={() => setLanguage(option)}
            >
              {t.language.options[option]}
            </button>
          ))}
        </div>
        <a className="nav-cta" href={repositoryUrl}>
          {t.nav.github}
        </a>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-inner">
            <div className="hero-visual" aria-hidden="true">
              <img src={assetUrl("logo/optees-appicon.png")} alt="" />
            </div>
            <div className="hero-content">
              <p className="eyebrow">{t.hero.eyebrow}</p>
              <h1 id="hero-title">{t.hero.title}</h1>
              <p className="hero-copy">{t.hero.copy}</p>
              <div className="hero-actions">
                <a className="button primary" href={macAsset?.browser_download_url ?? releasesUrl}>
                  {t.hero.download}
                </a>
                <a className="button secondary" href={repositoryUrl}>
                  {t.hero.source}
                </a>
              </div>
              <div className="hero-metrics" aria-label={t.hero.metricsAria}>
                {t.hero.metrics.map((metric) => (
                  <div key={`${metric.value}-${metric.label}`}>
                    <strong>{metric.value}</strong>
                    <span>{metric.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="algorithms" className="section algorithms-section" aria-labelledby="algorithms-title">
          <div className="section-heading">
            <p className="eyebrow">{t.algorithms.eyebrow}</p>
            <h2 id="algorithms-title">{t.algorithms.title}</h2>
            <p>{t.algorithms.body}</p>
          </div>

          <div className="algorithm-layout">
            <div className="algorithm-tabs" role="tablist" aria-label={t.algorithms.tabsAria}>
              {algorithms.map((algorithm) => (
                <button
                  key={algorithm.id}
                  type="button"
                  role="tab"
                  aria-selected={activeAlgorithm === algorithm.id}
                  className={activeAlgorithm === algorithm.id ? "algorithm-tab active" : "algorithm-tab"}
                  onClick={() => setActiveAlgorithm(algorithm.id)}
                >
                  <span>{algorithm.label}</span>
                  <em>{algorithm.status}</em>
                </button>
              ))}
            </div>
            <article className="algorithm-panel">
              <span className="status-pill">{selectedAlgorithm.status}</span>
              <h3>{selectedAlgorithm.label}</h3>
              <p>{selectedAlgorithm.description}</p>
              <ul>
                {selectedAlgorithm.details.map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        <section id="previews" className="section previews-section" aria-labelledby="previews-title">
          <div className="section-heading compact">
            <p className="eyebrow">{t.previews.eyebrow}</p>
            <h2 id="previews-title">{t.previews.title}</h2>
            <p>{t.previews.body}</p>
          </div>
          <div className="preview-grid">
            {screenshots.map((shot) => (
              <figure className="preview-item" key={shot.src}>
                <img src={shot.src} alt={shot.alt} loading="lazy" />
                <figcaption>
                  <strong>{shot.title}</strong>
                  <span>{shot.body}</span>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        <section className="section workflow-section" aria-labelledby="workflow-title">
          <div className="section-heading compact">
            <p className="eyebrow">{t.workflow.eyebrow}</p>
            <h2 id="workflow-title">{t.workflow.title}</h2>
          </div>
          <div className="workflow-steps">
            {t.workflow.steps.map((step) => (
              <div key={step.number}>
                <strong>{step.number}</strong>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="download" className="section download-section" aria-labelledby="download-title">
          <div>
            <p className="eyebrow">{t.download.eyebrow}</p>
            <h2 id="download-title">{t.download.title}</h2>
            <p>{t.download.body}</p>
          </div>
          <div className="download-box">
            <span className="release-label">{releaseLabel}</span>
            <a className="button primary" href={macAsset?.browser_download_url ?? releasesUrl}>
              {t.download.macButton}
            </a>
            <a className="button secondary" href={release?.html_url ?? releasesUrl}>
              {t.download.assetsButton}
            </a>
            <p>{t.download.gatekeeperNote}</p>
          </div>
        </section>

        <section id="roadmap" className="section roadmap-section" aria-labelledby="roadmap-title">
          <div className="section-heading compact">
            <p className="eyebrow">{t.roadmap.eyebrow}</p>
            <h2 id="roadmap-title">{t.roadmap.title}</h2>
            <p>{t.roadmap.body}</p>
          </div>
          <div className="roadmap-list">
            <a href={`${repositoryUrl}/blob/main/docs/PROJECT_ROADMAP.md`}>{t.roadmap.project}</a>
            <a href={`${repositoryUrl}/issues`}>{t.roadmap.issues}</a>
            <a href={releasesUrl}>{t.roadmap.releases}</a>
          </div>
        </section>
      </main>

      <footer className="footer">
        <span>{t.footer.product}</span>
        <span>{t.footer.claim}</span>
        <a href={repositoryUrl}>{t.footer.repository}</a>
      </footer>
    </div>
  );
}

export default App;
