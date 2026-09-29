import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const websiteDirectory = resolve(scriptDirectory, "..");
const distDirectory = resolve(websiteDirectory, "dist");
const fallbackSiteUrl = "https://optees.it";

async function localSiteUrl() {
  try {
    const source = await readFile(resolve(websiteDirectory, ".env.local"), "utf8");
    const match = source.match(/^\s*VITE_SITE_URL\s*=\s*(.+?)\s*$/m);
    return match?.[1].replace(/^['"]|['"]$/g, "") || "";
  } catch {
    return "";
  }
}

const siteUrl = (process.env.VITE_SITE_URL || (await localSiteUrl()) || fallbackSiteUrl).replace(
  /\/+$/,
  "",
);

for (const filename of ["robots.txt", "sitemap.xml", "llms.txt"]) {
  const path = resolve(distDirectory, filename);
  const source = await readFile(path, "utf8");
  await writeFile(path, source.replaceAll("%SITE_URL%", siteUrl), "utf8");
}

const rootIndexPath = resolve(distDirectory, "index.html");
const template = (await readFile(rootIndexPath, "utf8")).replaceAll("%SITE_URL%", siteUrl);

const landingMetadata = {
  it: {
    title: "Optees — Ambiente di Ottimizzazione e Piattaforma Solver Locale",
    description:
      "Optees è un ambiente desktop open source e una piattaforma solver locale per persone, script e agenti AI, con 16 capability versionate tramite GUI, CLI, REST e MCP.",
    socialDescription:
      "Modella visivamente o usa 16 capability solver locali e versionate tramite REST autenticata e MCP privato, con tabelle, grafici, asset 3D e report opzionali.",
    locale: "it_IT",
    alternateLocale: "en_US",
    imageAlt: "Icona dell'app Optees",
  },
  en: {
    title: "Optees — Local Optimization Workbench and Solver Platform",
    description:
      "Open-source desktop optimization workbench and local solver platform for people, scripts, and AI agents, with 16 versioned capabilities through GUI, CLI, REST, and MCP.",
    socialDescription:
      "Model visually or expose 16 versioned local solver capabilities to scripts and AI agents through authenticated REST and private MCP stdio.",
    locale: "en_US",
    alternateLocale: "it_IT",
    imageAlt: "Optees app icon",
  },
};

const agentMetadata = {
  it: {
    title: "Collega un agente AI locale a Optees — Configurazione MCP",
    description:
      "Configura Claude Desktop o un altro agente AI locale per usare le 16 capability versionate di Optees tramite MCP stdio privato.",
    socialDescription:
      "Collega un agente AI locale a Optees tramite MCP privato, quindi scopri, valida ed esegui 16 capability solver versionate.",
    locale: "it_IT",
    alternateLocale: "en_US",
    imageAlt: "Icona dell'app Optees",
  },
  en: {
    title: "Connect a Local AI Agent to Optees — MCP Setup",
    description:
      "Configure Claude Desktop or another local AI agent to use all 16 versioned Optees capabilities through private MCP stdio.",
    socialDescription:
      "Connect a local AI agent to Optees through private MCP, then discover, validate, and run 16 versioned solver capabilities.",
    locale: "en_US",
    alternateLocale: "it_IT",
    imageAlt: "Optees app icon",
  },
};

const faq = {
  it: [
    ["Cos'è Optees?", "Optees è un ambiente open source per la ricerca operativa e una piattaforma solver locale per persone, script e agenti AI."],
    ["A chi è rivolto?", "Ad analisti e aziende che prendono decisioni su risorse, scheduling e logistica, oltre a studenti e docenti che vogliono comprendere la matematica delle soluzioni."],
    ["È davvero gratuito?", "Sì. Optees è gratuito, open source e disponibile tramite GitHub Releases."],
    ["Quali piattaforme sono supportate?", "Optees supporta macOS, Windows e Linux."],
    ["Devo saper programmare?", "No. L'interfaccia desktop permette di formulare e risolvere problemi senza scrivere codice."],
    ["Un agente AI può usare Optees?", "Sì. Gli agenti locali possono usare capability versionate tramite REST loopback autenticata o MCP stdio privato."],
  ],
  en: [
    ["What is Optees?", "Optees is an open-source operations-research workbench and local solver platform for people, scripts, and AI agents."],
    ["Who is it for?", "It is for analysts and businesses making resource, scheduling, and logistics decisions, as well as students and teachers who want to understand the mathematics behind solutions."],
    ["Is Optees free?", "Yes. Optees is free, open source, and available through GitHub Releases."],
    ["Which platforms are supported?", "Optees supports macOS, Windows, and Linux."],
    ["Do I need to know how to code?", "No. The desktop interface lets users formulate and solve problems without writing code."],
    ["Can an AI agent use Optees?", "Yes. Local agents can use versioned capabilities through authenticated loopback REST or private MCP stdio."],
  ],
};

function replaceMeta(html, attribute, key, content) {
  const pattern = new RegExp(`<meta\\s+${attribute}="${key}"\\s+content="[^"]*"\\s*/>`, "s");
  return html.replace(pattern, `<meta ${attribute}="${key}" content="${content}" />`);
}

function replaceStructuredData(html, transform) {
  return html.replace(
    /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g,
    (_element, jsonSource) => {
      const transformed = transform(JSON.parse(jsonSource));
      if (transformed === null) return "";
      return `<script type="application/ld+json">\n${JSON.stringify(transformed, null, 2)}\n    </script>`;
    },
  );
}

function renderPage({ language, page, path, alternates, metadata }) {
  let html = template
    .replace(/<html lang="[^"]+">/, `<html lang="${language}">`)
    .replace(/<title>[\s\S]*?<\/title>/, `<title>${metadata.title}</title>`)
    .replace(/<link rel="canonical" href="[^"]+" \/>/, `<link rel="canonical" href="${siteUrl}${path}" />`)
    .replace(/<link rel="alternate" hreflang="en" href="[^"]+" \/>/, `<link rel="alternate" hreflang="en" href="${siteUrl}${alternates.en}" />`)
    .replace(/<link rel="alternate" hreflang="it" href="[^"]+" \/>/, `<link rel="alternate" hreflang="it" href="${siteUrl}${alternates.it}" />`)
    .replace(/<link rel="alternate" hreflang="x-default" href="[^"]+" \/>/, `<link rel="alternate" hreflang="x-default" href="${siteUrl}${alternates.it}" />`);

  html = replaceMeta(html, "name", "description", metadata.description);
  html = replaceMeta(html, "property", "og:locale", metadata.locale);
  html = replaceMeta(html, "property", "og:locale:alternate", metadata.alternateLocale);
  html = replaceMeta(html, "property", "og:title", metadata.title);
  html = replaceMeta(html, "property", "og:description", metadata.socialDescription);
  html = replaceMeta(html, "property", "og:image:alt", metadata.imageAlt);
  html = replaceMeta(html, "property", "og:url", `${siteUrl}${path}`);
  html = replaceMeta(html, "name", "twitter:title", metadata.title);
  html = replaceMeta(html, "name", "twitter:description", metadata.socialDescription);

  return replaceStructuredData(html, (data) => {
    if (page === "agents") return null;
    if (data["@type"] === "SoftwareApplication") {
      return { ...data, inLanguage: language, description: metadata.description };
    }
    if (data["@type"] === "FAQPage") {
      return {
        ...data,
        inLanguage: language,
        mainEntity: faq[language].map(([question, answer]) => ({
          "@type": "Question",
          name: question,
          acceptedAnswer: { "@type": "Answer", text: answer },
        })),
      };
    }
    return data;
  });
}

const pages = [
  { language: "it", page: "landing", path: "/", alternates: { it: "/", en: "/en/" }, metadata: landingMetadata.it },
  { language: "en", page: "landing", path: "/en/", alternates: { it: "/", en: "/en/" }, metadata: landingMetadata.en },
  { language: "it", page: "agents", path: "/agents/", alternates: { it: "/agents/", en: "/en/agents/" }, metadata: agentMetadata.it },
  { language: "en", page: "agents", path: "/en/agents/", alternates: { it: "/agents/", en: "/en/agents/" }, metadata: agentMetadata.en },
];

for (const page of pages) {
  const directory = resolve(distDirectory, `.${page.path}`);
  await mkdir(directory, { recursive: true });
  await writeFile(resolve(directory, "index.html"), renderPage(page), "utf8");
}
