import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  copy,
  detectLanguage,
  formatMessage,
  supportedLanguages,
  type FeatureId,
  type PreviewId,
  type Language,
} from "./i18n";

const repositoryUrl = "https://github.com/Pablo-gitub/optees";
const releasesUrl = `${repositoryUrl}/releases`;
const roadmapUrl = `${repositoryUrl}/blob/main/docs/PROJECT_ROADMAP.md`;
const issuesUrl = `${repositoryUrl}/issues`;
const latestReleaseApi = "https://api.github.com/repos/Pablo-gitub/optees/releases/latest";
const assetUrl = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\//, "")}`;

const authorUrl = "https://paolopietrelli.com";
const authorSiteLabel = "paolopietrelli.com";
const socialLinks: ReadonlyArray<{ href: string; label: string; icon: IconName }> = [
  { href: "https://github.com/Pablo-gitub", label: "GitHub", icon: "github" },
  { href: "https://www.linkedin.com/in/paolo-pietrelli", label: "LinkedIn", icon: "linkedin" },
  { href: "https://www.instagram.com/ing_paolo_pietrelli/", label: "Instagram", icon: "instagram" },
];

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
  assistant: "screenshots/optees-assistant.png",
  lpSolution: "screenshots/optees-lp-solution.png",
  knapsack: "screenshots/optees-knapsack.png",
  knapsackSolution: "screenshots/optees-knapsack-solution.png",
  packingSolution: "screenshots/optees-packing-solution.png",
  nlpSolution: "screenshots/optees-nlp-solution.png",
  regressionSolution: "screenshots/optees-regression-solution.png",
  classificationSolution: "screenshots/optees-classification-solution.png",
  graphSolution: "screenshots/optees-graph-solution.png",
};

const footerLinkHref: Record<string, string> = {
  repo: repositoryUrl,
  releases: releasesUrl,
  roadmap: roadmapUrl,
  issues: issuesUrl,
};

type OSKey = "mac" | "windows" | "linux" | "other";

const preferredAssetMatchers: Record<Exclude<OSKey, "other">, RegExp> = {
  mac: /\.dmg$/i,
  windows: /-setup\.exe$/i,
  linux: /\.appimage$/i,
};

function detectOS(): OSKey {
  if (typeof navigator === "undefined") return "other";
  const ua = navigator.userAgent.toLowerCase();
  if (/android|iphone|ipad|ipod/.test(ua)) return "other";
  const uaData = (navigator as unknown as { userAgentData?: { platform?: string } }).userAgentData;
  const platform = (uaData?.platform || navigator.platform || "").toLowerCase();
  if (/mac/.test(platform) || /mac os x|macintosh/.test(ua)) return "mac";
  if (/win/.test(platform) || /windows/.test(ua)) return "windows";
  if (/linux/.test(platform) || /linux|x11/.test(ua)) return "linux";
  return "other";
}

function assetHrefFor(release: ReleaseInfo | null, os: OSKey): string {
  if (!release || os === "other") return releasesUrl;
  const asset = release.assets.find((item) => preferredAssetMatchers[os].test(item.name));
  return asset?.browser_download_url ?? releasesUrl;
}

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

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* -------------------------------------------------------------------------- */
/* Icons                                                                      */
/* -------------------------------------------------------------------------- */

type IconName =
  | FeatureId
  | "download"
  | "github"
  | "star"
  | "arrow"
  | "check"
  | "chevron"
  | "spark"
  | "apple"
  | "windows"
  | "linux"
  | "linkedin"
  | "instagram";

const filledIcons = new Set<IconName>(["apple", "windows", "linux", "linkedin"]);

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    assistant: (
      <>
        <path d="M4 5h16v11H9l-4 4v-4H4z" />
        <path d="M9.5 10.5h.01M12 10.5h.01M14.5 10.5h.01" />
      </>
    ),
    agentPlatform: (
      <>
        <rect x="4" y="5" width="16" height="12" rx="2" />
        <path d="M8 21h8M12 17v4" />
        <path d="m8 11 2 2 3-4 3 3" />
      </>
    ),
    educational: (
      <>
        <path d="M12 4 2.5 8.5 12 13l9.5-4.5L12 4Z" />
        <path d="M6 10.5V15c0 1.2 2.7 2.5 6 2.5s6-1.3 6-2.5v-4.5" />
        <path d="M21.5 8.5V14" />
      </>
    ),
    variants: (
      <>
        <path d="M12 3 3 7.5l9 4.5 9-4.5L12 3Z" />
        <path d="m3 12 9 4.5L21 12" />
        <path d="m3 16.5 9 4.5 9-4.5" />
      </>
    ),
    benchmarks: (
      <>
        <path d="M9 3h6" />
        <path d="M10 3v5.2a4 4 0 0 1-.8 2.4L5.5 15.4A2 2 0 0 0 7.1 18.6h9.8a2 2 0 0 0 1.6-3.2l-3.7-4.8a4 4 0 0 1-.8-2.4V3" />
        <path d="M8.5 14h7" />
      </>
    ),
    local: (
      <>
        <path d="M12 3 5 6v5c0 4.2 2.9 7.6 7 9 4.1-1.4 7-4.8 7-9V6l-7-3Z" />
        <path d="m9.2 12 1.9 1.9 3.7-3.9" />
      </>
    ),
    openSource: (
      <>
        <path d="m9 8-4 4 4 4" />
        <path d="m15 8 4 4-4 4" />
        <path d="m13 6-2 12" />
      </>
    ),
    download: (
      <>
        <path d="M12 3v12" />
        <path d="m7 11 5 5 5-5" />
        <path d="M5 20h14" />
      </>
    ),
    github: (
      <path d="M12 2.2A9.8 9.8 0 0 0 8.9 21.3c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.3-3.4-1.3-.4-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.6 2.4 1.1 3 .9.1-.7.4-1.1.6-1.4-2.2-.3-4.5-1.1-4.5-5a3.9 3.9 0 0 1 1-2.7c-.1-.3-.5-1.3.1-2.7 0 0 .8-.3 2.7 1a9.3 9.3 0 0 1 5 0c1.9-1.3 2.7-1 2.7-1 .6 1.4.2 2.4.1 2.7a3.9 3.9 0 0 1 1 2.7c0 3.9-2.3 4.7-4.5 5 .4.3.7.9.7 1.9v2.8c0 .3.2.6.7.5A9.8 9.8 0 0 0 12 2.2Z" />
    ),
    star: (
      <path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9L12 3.5Z" />
    ),
    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="m13 6 6 6-6 6" />
      </>
    ),
    check: <path d="m5 12 4 4 10-10" />,
    chevron: <path d="m6 9 6 6 6-6" />,
    spark: (
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
    ),
    apple: (
      <path d="M15.77 12.79c.02 2.6 2.28 3.46 2.3 3.47-.02.06-.36 1.24-1.19 2.46-.72 1.05-1.47 2.1-2.64 2.12-1.15.02-1.52-.68-2.84-.68-1.31 0-1.72.66-2.81.7-1.13.04-1.99-1.13-2.72-2.18-1.48-2.14-2.61-6.05-1.09-8.69.75-1.31 2.1-2.14 3.56-2.16 1.11-.02 2.16.75 2.84.75.68 0 1.96-.93 3.3-.79.56.02 2.14.23 3.15 1.71-.08.05-1.88 1.1-1.86 3.27M13.6 5.67c.6-.73 1.01-1.74.9-2.75-.87.04-1.92.58-2.54 1.31-.56.64-1.05 1.67-.92 2.66.97.08 1.96-.49 2.56-1.22" />
    ),
    windows: (
      <path d="M3 5.4 10.4 4.35v7.1H3zM11.4 4.2 21 3v8.45h-9.6zM3 12.55h7.4v7.1L3 18.6zM11.4 12.55H21V21l-9.6-1.28z" />
    ),
    linux: (
      <path d="M12 2.4c-2 0-3.35 1.7-3.35 3.9v1.1c0 .55-.3.95-.8 1.5-1 1.1-1.75 2.6-2.35 4.3-.32.9-.8 1.55-1.2 2.05-.55.7-.1 1.75.78 1.8.15 0 .3-.02.45-.08-.05.4-.03.75.05 1.02.24.78 1.02 1.2 2.15 1.42 1.02.2 1.55.6 2.42.6h1.6c.87 0 1.4-.4 2.42-.6 1.13-.22 1.9-.64 2.15-1.42.08-.27.1-.62.05-1.02.15.06.3.08.45.08.88-.05 1.33-1.1.78-1.8-.4-.5-.88-1.15-1.2-2.05-.6-1.7-1.35-3.2-2.35-4.3-.5-.55-.8-.95-.8-1.5v-1.1c0-2.2-1.35-3.9-3.35-3.9Zm-1.35 4.05a.75.75 0 1 1 0 1.5.75.75 0 0 1 0-1.5Zm2.7 0a.75.75 0 1 1 0 1.5.75.75 0 0 1 0-1.5Z" />
    ),
    linkedin: (
      <path d="M6.94 8.5v9.5H4V8.5h2.94ZM5.47 4.2a1.71 1.71 0 1 1 0 3.42 1.71 1.71 0 0 1 0-3.42ZM9 8.5h2.82v1.3h.04c.39-.72 1.35-1.48 2.78-1.48 2.97 0 3.52 1.9 3.52 4.38V18h-2.94v-4.36c0-1.04-.02-2.38-1.46-2.38-1.46 0-1.68 1.13-1.68 2.3V18H9V8.5Z" />
    ),
    instagram: (
      <>
        <rect x="4" y="4" width="16" height="16" rx="4.6" />
        <circle cx="12" cy="12" r="3.6" />
        <circle cx="16.7" cy="7.3" r="1" />
      </>
    ),
  };

  const filled = filledIcons.has(name);

  return (
    <svg
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[name]}
    </svg>
  );
}

/* -------------------------------------------------------------------------- */
/* Animated metric                                                            */
/* -------------------------------------------------------------------------- */

function Metric({ value, label }: { value: string; label: string }) {
  const match = /^(\d+)(.*)$/.exec(value);
  const target = match ? Number(match[1]) : null;
  const suffix = match ? match[2] : "";
  const [display, setDisplay] = useState(target === null ? value : `0${suffix}`);

  useEffect(() => {
    if (target === null) {
      setDisplay(value);
      return;
    }
    if (prefersReducedMotion()) {
      setDisplay(`${target}${suffix}`);
      return;
    }
    let frame = 0;
    const duration = 1200;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(`${Math.round(eased * target)}${suffix}`);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, suffix, value]);

  return (
    <div className="metric">
      <strong>{display}</strong>
      <span>{label}</span>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Window frame for screenshots                                               */
/* -------------------------------------------------------------------------- */

function WindowFrame({
  title,
  src,
  alt,
  eager = false,
  className = "",
}: {
  title: string;
  src: string;
  alt: string;
  eager?: boolean;
  className?: string;
}) {
  return (
    <figure className={`window ${className}`.trim()}>
      <div className="window-bar">
        <span className="traffic" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span className="window-title">{title}</span>
      </div>
      <img src={src} alt={alt} loading={eager ? "eager" : "lazy"} decoding="async" />
    </figure>
  );
}

/* -------------------------------------------------------------------------- */
/* OS-aware download button                                                   */
/* -------------------------------------------------------------------------- */

type Copy = (typeof copy)[Language];

function DownloadButton({
  t,
  release,
  os,
  variant,
}: {
  t: Copy;
  release: ReleaseInfo | null;
  os: OSKey;
  variant: "hero" | "box";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const platformList: Array<{ key: "mac" | "windows" | "linux"; label: string; icon: IconName }> = [
    { key: "mac", label: t.download.platformNames.mac, icon: "apple" },
    { key: "windows", label: t.download.platformNames.windows, icon: "windows" },
    { key: "linux", label: t.download.platformNames.linux, icon: "linux" },
  ];

  const known = os !== "other";
  const primaryLabel = known
    ? formatMessage(t.download.downloadFor, { platform: t.download.platformNames[os] })
    : t.download.downloadGeneric;
  const primaryIcon: IconName = known ? platformList.find((p) => p.key === os)!.icon : "download";

  return (
    <div className={`split-download split-${variant}`} ref={ref}>
      <div className="split-main">
        <a className="button primary split-primary" href={assetHrefFor(release, os)}>
          <Icon name={primaryIcon} />
          {primaryLabel}
        </a>
        <button
          type="button"
          className="button primary split-caret"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-label={t.download.otherVersions}
          onClick={() => setOpen((value) => !value)}
        >
          <Icon name="chevron" />
        </button>
      </div>
      {open && (
        <div className="download-menu" role="menu" aria-label={t.download.menuAria}>
          {platformList.map((platform) => (
            <a
              key={platform.key}
              role="menuitem"
              className={platform.key === os ? "menu-item current" : "menu-item"}
              href={assetHrefFor(release, platform.key)}
              onClick={() => setOpen(false)}
            >
              <Icon name={platform.icon} />
              <span>{platform.label}</span>
              {platform.key === os && <em>{t.download.yourSystem}</em>}
            </a>
          ))}
          <a
            role="menuitem"
            className="menu-item menu-all"
            href={release?.html_url ?? releasesUrl}
            onClick={() => setOpen(false)}
          >
            <Icon name="github" />
            <span>{t.download.allReleases}</span>
          </a>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* App                                                                        */
/* -------------------------------------------------------------------------- */

function App() {
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const t = copy[language];
  const [activeAlgorithm, setActiveAlgorithm] = useState(t.algorithms.items[0].id);
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [scrolled, setScrolled] = useState(false);
  const [release, setRelease] = useState<ReleaseInfo | null>(null);
  const [releaseError, setReleaseError] = useState(false);
  const revealRoot = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    window.localStorage.setItem(languageStorageKey, language);
    document.documentElement.lang = language;
    document.title = t.meta.title;
    setMetaContent('meta[name="description"]', t.meta.description);
    setMetaContent('meta[property="og:title"]', t.meta.title);
    setMetaContent('meta[property="og:description"]', t.meta.ogDescription);
    setMetaContent('meta[name="twitter:description"]', t.meta.ogDescription);
  }, [language, t]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

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

  // Reveal-on-scroll animations.
  useEffect(() => {
    const nodes = Array.from(
      revealRoot.current?.querySelectorAll<HTMLElement>("[data-reveal]") ?? [],
    );
    if (prefersReducedMotion() || !("IntersectionObserver" in window)) {
      nodes.forEach((node) => node.classList.add("is-visible"));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -8% 0px" },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [language]);

  const algorithms = t.algorithms.items;

  const selectedAlgorithm = useMemo(
    () => algorithms.find((algorithm) => algorithm.id === activeAlgorithm) ?? algorithms[0],
    [algorithms, activeAlgorithm],
  );

  const screenshots = t.previews.items.map((shot) => ({
    ...shot,
    src: assetUrl(previewAssets[shot.id]),
  }));

  const os = useMemo(() => detectOS(), []);
  const downloadHref = assetHrefFor(release, os);

  const releaseLabel = release
    ? formatMessage(t.download.latestRelease, { version: release.tag_name })
    : releaseError
      ? t.download.fallbackRelease
      : t.download.checkingRelease;

  return (
    <div className="site-shell" ref={revealRoot}>
      <div className="bg-aurora" aria-hidden="true" />
      <div className="bg-grid" aria-hidden="true" />

      <header className={scrolled ? "topbar scrolled" : "topbar"} aria-label={t.nav.aria}>
        <div className="topbar-inner">
          <a className="brand" href="#top" aria-label={t.nav.brandAria}>
            <img className="brand-mark" src={assetUrl("logo/optees-appicon.png")} alt="" />
            <span>{t.footer.product}</span>
          </a>
          <nav className="nav-links" aria-label={t.nav.sectionsAria}>
            <a href="#features">{t.nav.features}</a>
            <a href="#agent-platform">{t.nav.agents}</a>
            <a href="#algorithms">{t.nav.algorithms}</a>
            <a href="#machine-learning">{t.nav.machineLearning}</a>
            <a href="#previews">{t.nav.previews}</a>
            <a href="#faq">{t.nav.faq}</a>
          </nav>
          <div className="topbar-actions">
            <div className="language-switch" role="group" aria-label={t.language.aria}>
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
            <a className="ghost-link" href={repositoryUrl} aria-label="GitHub">
              <Icon name="github" />
            </a>
            <a className="button primary compact topbar-download" href={downloadHref}>
              <Icon name="download" />
              {t.nav.getApp}
            </a>
          </div>
        </div>
      </header>

      <main id="top">
        {/* HERO ---------------------------------------------------------- */}
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-inner">
            <div className="hero-content" data-reveal>
              <p className="badge">
                <span className="badge-dot" aria-hidden="true" />
                {t.hero.badge}
              </p>
              <h1 id="hero-title">
                {t.hero.title} <span className="accent">{t.hero.titleAccent}</span>
              </h1>
              <p className="hero-copy">{t.hero.copy}</p>
              <div className="hero-actions">
                <DownloadButton t={t} release={release} os={os} variant="hero" />
                <a className="button secondary" href={repositoryUrl}>
                  <Icon name="star" />
                  {t.hero.source}
                </a>
              </div>
              <div className="stack-row" aria-label={t.hero.stackLabel}>
                <span className="stack-label">{t.hero.stackLabel}</span>
                <ul>
                  {t.hero.stack.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="hero-visual" data-reveal>
              <div className="hero-glow" aria-hidden="true" />
              <WindowFrame
                className="hero-shot"
                title={t.hero.shotCaption}
                src={assetUrl(previewAssets.lpSolution)}
                  alt={
                    t.previews.items.find((item) => item.id === "lpSolution")
                      ?.alt ?? ""
                  }
                eager
              />
              <div className="float-card float-status" aria-hidden="true">
                <span className="status-led" />
                <div>
                  <strong>{t.hero.floatStatus}</strong>
                  <code>{t.hero.floatObjective}</code>
                </div>
              </div>
              <div className="float-card float-chart" aria-hidden="true">
                <svg viewBox="0 0 120 60" preserveAspectRatio="none">
                  <rect x="6" y="34" width="16" height="22" rx="2" />
                  <rect x="30" y="20" width="16" height="36" rx="2" />
                  <rect x="54" y="26" width="16" height="30" rx="2" />
                  <rect x="78" y="10" width="16" height="46" rx="2" />
                  <rect x="102" y="30" width="16" height="26" rx="2" />
                </svg>
              </div>
            </div>
          </div>

          <div className="hero-metrics" aria-label={t.hero.metricsAria} data-reveal>
            {t.hero.metrics.map((metric) => (
              <Metric key={metric.label} value={metric.value} label={metric.label} />
            ))}
          </div>
        </section>

        {/* FEATURES ------------------------------------------------------ */}
        <section id="features" className="section features-section" aria-labelledby="features-title">
          <div className="section-heading" data-reveal>
            <p className="eyebrow">{t.features.eyebrow}</p>
            <h2 id="features-title">{t.features.title}</h2>
            <p>{t.features.body}</p>
          </div>
          <div className="bento">
            {t.features.items.map((feature, index) => (
              <article
                key={feature.id}
                className={`bento-card bento-${feature.id}`}
                data-reveal
                style={{ transitionDelay: `${index * 60}ms` }}
              >
                <span className="bento-icon">
                  <Icon name={feature.id} />
                </span>
                <div className="bento-card-copy">
                  {feature.kicker && <span className="bento-kicker">{feature.kicker}</span>}
                  <h3>{feature.title}</h3>
                  <p>{feature.body}</p>
                </div>
                {feature.highlights && (
                  <ul className="bento-highlights" aria-label={feature.title}>
                    {feature.highlights.map((highlight) => (
                      <li key={highlight}>
                        <Icon name="check" />
                        {highlight}
                      </li>
                    ))}
                  </ul>
                )}
                {feature.cta && (
                  <a className="bento-cta" href="#agent-platform">
                    {feature.cta}
                    <Icon name="arrow" />
                  </a>
                )}
              </article>
            ))}
          </div>
        </section>

        {/* LOCAL AGENT PLATFORM ---------------------------------------- */}
        <section
          id="agent-platform"
          className="section agent-platform-section"
          aria-labelledby="agent-platform-title"
        >
          <div className="section-heading" data-reveal>
            <p className="eyebrow">{t.agentPlatform.eyebrow}</p>
            <h2 id="agent-platform-title">{t.agentPlatform.title}</h2>
            <p>{t.agentPlatform.body}</p>
          </div>

          <div className="agent-platform-shell" data-reveal>
            <div className="agent-surfaces">
              {t.agentPlatform.surfaces.map((surface, index) => (
                <article key={surface.title}>
                  <span className="agent-surface-index" aria-hidden="true">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <h3>{surface.title}</h3>
                  <p>{surface.body}</p>
                </article>
              ))}
            </div>

            <ol className="agent-flow" aria-label={t.agentPlatform.flowAria}>
              {t.agentPlatform.steps.map((step, index) => (
                <li key={step.label}>
                  <span>{index + 1}</span>
                  <strong>{step.label}</strong>
                  <p>{step.body}</p>
                </li>
              ))}
            </ol>

            <div className="agent-boundaries">
              <div>
                <Icon name="local" />
                <p>{t.agentPlatform.boundary}</p>
              </div>
              <div>
                <Icon name="assistant" />
                <p>
                  <strong>{t.agentPlatform.assistantTitle}</strong>
                  {t.agentPlatform.assistantBody}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ALGORITHMS ---------------------------------------------------- */}
        <section id="algorithms" className="section algorithms-section" aria-labelledby="algorithms-title">
          <div className="section-heading" data-reveal>
            <p className="eyebrow">{t.algorithms.eyebrow}</p>
            <h2 id="algorithms-title">{t.algorithms.title}</h2>
            <p>{t.algorithms.body}</p>
          </div>

          <div className="algorithm-layout" data-reveal>
            <div className="algorithm-tabs" role="tablist" aria-label={t.algorithms.tabsAria}>
              {algorithms.map((algorithm) => {
                const active = activeAlgorithm === algorithm.id;
                return (
                  <button
                    key={algorithm.id}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    className={active ? "algorithm-tab active" : "algorithm-tab"}
                    onClick={() => setActiveAlgorithm(algorithm.id)}
                  >
                    <span className="tab-short">{algorithm.short}</span>
                    <span className="tab-label">{algorithm.label}</span>
                    <em
                      className={
                        algorithm.status.toLowerCase().includes("road") ||
                        algorithm.status.toLowerCase().includes("roadmap")
                          ? "tab-status soon"
                          : "tab-status live"
                      }
                    >
                      {algorithm.status}
                    </em>
                  </button>
                );
              })}
            </div>

            <article className="algorithm-panel" role="tabpanel">
              <header>
                <h3>{selectedAlgorithm.label}</h3>
                <span
                  className={
                    selectedAlgorithm.status.toLowerCase().includes("road")
                      ? "status-pill soon"
                      : "status-pill live"
                  }
                >
                  {selectedAlgorithm.status}
                </span>
              </header>
              <p className="panel-model-label">{t.algorithms.modelLabel}</p>
              <code className="formula">{selectedAlgorithm.formula}</code>
              <p className="panel-desc">{selectedAlgorithm.description}</p>
              <p className="panel-caps-label">{t.algorithms.capabilitiesLabel}</p>
              <ul className="chips">
                {selectedAlgorithm.details.map((detail) => (
                  <li key={detail}>
                    <Icon name="check" />
                    {detail}
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        {/* AI & MACHINE LEARNING --------------------------------------- */}
        <section
          id="machine-learning"
          className="section machine-learning-section"
          aria-labelledby="machine-learning-title"
        >
          <div className="section-heading" data-reveal>
            <p className="eyebrow">{t.machineLearning.eyebrow}</p>
            <h2 id="machine-learning-title">{t.machineLearning.title}</h2>
            <p>{t.machineLearning.body}</p>
          </div>

          <div className="machine-learning-assistant" data-reveal>
            <span className="machine-learning-assistant-icon" aria-hidden="true">
              <Icon name="assistant" />
            </span>
            <div>
              <h3>{t.machineLearning.assistant.title}</h3>
              <p>{t.machineLearning.assistant.body}</p>
            </div>
          </div>

          <div className="machine-learning-workflows">
            {t.machineLearning.workflows.map((workflow, index) => {
              const preview = screenshots.find((shot) => shot.id === workflow.preview);
              if (!preview) return null;

              return (
                <article
                  className="machine-learning-workflow"
                  key={workflow.title}
                  data-reveal
                  style={{ transitionDelay: `${index * 90}ms` }}
                >
                  <div className="machine-learning-copy">
                    <h3>{workflow.title}</h3>
                    <p>{workflow.body}</p>
                    <ul className="machine-learning-points">
                      {workflow.points.map((point) => (
                        <li key={point}>
                          <Icon name="check" />
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <WindowFrame
                    className="machine-learning-shot"
                    title={preview.window}
                    src={preview.src}
                    alt={preview.alt}
                  />
                </article>
              );
            })}
          </div>
        </section>

        {/* PREVIEWS ------------------------------------------------------ */}
        <section id="previews" className="section previews-section" aria-labelledby="previews-title">
          <div className="section-heading" data-reveal>
            <p className="eyebrow">{t.previews.eyebrow}</p>
            <h2 id="previews-title">{t.previews.title}</h2>
            <p>{t.previews.body}</p>
          </div>
          <div className="preview-grid">
            {screenshots.map((shot, index) => (
              <div
                className="preview-item"
                key={shot.id}
                data-reveal
                style={{ transitionDelay: `${index * 70}ms` }}
              >
                <WindowFrame title={shot.window} src={shot.src} alt={shot.alt} />
                <div className="preview-caption">
                  <strong>{shot.title}</strong>
                  <span>{shot.body}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* WORKFLOW ------------------------------------------------------ */}
        <section className="section workflow-section" aria-labelledby="workflow-title">
          <div className="section-heading" data-reveal>
            <p className="eyebrow">{t.workflow.eyebrow}</p>
            <h2 id="workflow-title">{t.workflow.title}</h2>
            <p>{t.workflow.body}</p>
          </div>
          <ol className="workflow-steps">
            {t.workflow.steps.map((step, index) => (
              <li
                key={step.number}
                data-reveal
                style={{ transitionDelay: `${index * 90}ms` }}
              >
                <span className="step-number">{step.number}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* DOWNLOAD ------------------------------------------------------ */}
        <section id="download" className="section download-section" aria-labelledby="download-title">
          <div className="download-panel" data-reveal>
            <div className="download-copy">
              <p className="eyebrow">{t.download.eyebrow}</p>
              <h2 id="download-title">{t.download.title}</h2>
              <p>{t.download.body}</p>
              <div className="platforms">
                <span className="platforms-label">{t.download.platformsLabel}</span>
                <ul>
                  {t.download.platforms.map((platform) => (
                    <li key={platform}>{platform}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="download-box">
              <span className="release-label">
                <span className="status-led" aria-hidden="true" />
                {releaseLabel}
              </span>
              <DownloadButton t={t} release={release} os={os} variant="box" />
              <a className="button secondary" href={release?.html_url ?? releasesUrl}>
                {t.download.assetsButton}
                <Icon name="arrow" />
              </a>
              <p className="gatekeeper">{t.download.gatekeeperNote}</p>
            </div>
          </div>
        </section>

        {/* FAQ ----------------------------------------------------------- */}
        <section id="faq" className="section faq-section" aria-labelledby="faq-title">
          <div className="section-heading" data-reveal>
            <p className="eyebrow">{t.faq.eyebrow}</p>
            <h2 id="faq-title">{t.faq.title}</h2>
            <p>{t.faq.body}</p>
          </div>
          <div className="faq-list" data-reveal>
            {t.faq.items.map((item, index) => {
              const open = openFaq === index;
              return (
                <div key={item.q} className={open ? "faq-item open" : "faq-item"}>
                  <button
                    type="button"
                    aria-expanded={open}
                    onClick={() => setOpenFaq(open ? null : index)}
                  >
                    <span>{item.q}</span>
                    <Icon name="chevron" />
                  </button>
                  <div className="faq-answer">
                    <p>{item.a}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <a className="brand" href="#top" aria-label={t.nav.brandAria}>
              <img className="brand-mark" src={assetUrl("logo/optees-appicon.png")} alt="" />
              <span>{t.footer.product}</span>
            </a>
            <p>{t.footer.tagline}</p>
            <div className="footer-badges">
              <span>
                <Icon name="openSource" />
                {t.footer.license}
              </span>
            </div>
            <div className="footer-social" aria-label={t.footer.socialAria}>
              {socialLinks.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={social.label}
                  title={social.label}
                >
                  <Icon name={social.icon} />
                </a>
              ))}
            </div>
          </div>
          <div className="footer-columns">
            {t.footer.columns.map((column) => (
              <nav key={column.title} aria-label={column.title}>
                <h4>{column.title}</h4>
                <ul>
                  {column.links.map((link) => (
                    <li key={link.key}>
                      <a href={link.key.startsWith("#") ? link.key : footerLinkHref[link.key]}>
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        </div>
        <div className="footer-bottom">
          <span>{formatMessage(t.footer.copyright, { year: String(new Date().getFullYear()) })}</span>
          <a href={authorUrl} target="_blank" rel="noreferrer" aria-label={t.footer.madeBy}>
            {authorSiteLabel}
          </a>
        </div>
      </footer>
    </div>
  );
}

export default App;
