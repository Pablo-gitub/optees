import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const websiteDirectory = resolve(scriptDirectory, "..");
const distDirectory = resolve(websiteDirectory, "dist");
const fallbackSiteUrl = "https://pablo-gitub.github.io/optees";

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

for (const filename of ["index.html", "robots.txt", "sitemap.xml", "llms.txt"]) {
  const path = resolve(distDirectory, filename);
  const source = await readFile(path, "utf8");
  await writeFile(path, source.replaceAll("%SITE_URL%", siteUrl), "utf8");
}

const rootIndexPath = resolve(distDirectory, "index.html");
const rootIndex = await readFile(rootIndexPath, "utf8");
const agentDescription =
  "Connect Claude Desktop and other local AI agents to Optees through private MCP stdio, then discover, validate, orchestrate, and run 13 versioned solver capabilities.";
const agentIndex = rootIndex
  .replace(
    "<title>Optees — Local Optimization Workbench and Solver Platform</title>",
    "<title>Connect AI Agents to Optees — Local MCP Setup</title>",
  )
  .replace(
    /<meta\s+name="description"\s+content="[^"]*"\s*\/>/,
    `<meta name="description" content="${agentDescription}" />`,
  )
  .replace(
    '<link rel="canonical" href="' + siteUrl + '/" />',
    '<link rel="canonical" href="' + siteUrl + '/agents/" />',
  )
  .replace(
    '<meta property="og:url" content="' + siteUrl + '/" />',
    '<meta property="og:url" content="' + siteUrl + '/agents/" />',
  )
  .replace(
    '<meta property="og:title" content="Optees — Optimization for People and Agents" />',
    '<meta property="og:title" content="Connect AI Agents to Optees" />',
  )
  .replace(
    /<meta\s+property="og:description"\s+content="[^"]*"\s*\/>/,
    `<meta property="og:description" content="${agentDescription}" />`,
  )
  .replace(
    '<meta name="twitter:title" content="Optees — Optimization for People and Agents" />',
    '<meta name="twitter:title" content="Connect AI Agents to Optees" />',
  )
  .replace(
    /<meta\s+name="twitter:description"\s+content="[^"]*"\s*\/>/,
    `<meta name="twitter:description" content="${agentDescription}" />`,
  )
  .replaceAll('href="./logo/', 'href="../logo/');

const agentDirectory = resolve(distDirectory, "agents");
await mkdir(agentDirectory, { recursive: true });
await writeFile(resolve(agentDirectory, "index.html"), agentIndex, "utf8");
