import svelte from "@astrojs/svelte";
import vercel from "@astrojs/vercel";
import { defineConfig } from "astro/config";

// Pages are static; the API routes (start, submit, leaderboard) run as Vercel functions.
export default defineConfig({
  site: "https://smart-bomberman.vercel.app",
  output: "static",
  adapter: vercel(),
  integrations: [svelte()],
  devToolbar: { enabled: false },
});
