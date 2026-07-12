import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const githubPagesUrl = "https://pablo-gitub.github.io/optees";

export default defineConfig(({ command, mode }) => {
  const environment = loadEnv(mode, process.cwd(), "");
  const siteUrl = (environment.VITE_SITE_URL || githubPagesUrl).replace(/\/+$/, "");
  const isFirebaseHostingBuild = siteUrl !== githubPagesUrl;

  return {
    // Keep the existing GitHub Pages build valid until Firebase has its own
    // production URL. Local development and Firebase Hosting both serve root.
    base: command === "serve" || isFirebaseHostingBuild ? "/" : "/optees/",
    plugins: [react()],
  };
});
