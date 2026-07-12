import { readFile, writeFile } from "node:fs/promises";
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
