import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Local development and the Firebase custom domain both serve from root.
  base: "/",
  plugins: [react()],
});
