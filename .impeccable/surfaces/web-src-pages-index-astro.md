---
version: 1
slug: "web-src-pages-index-astro"
primary_target: "web/src/pages/index.astro"
related_targets: ["web/src/pages/crosstable.astro","web/src/pages/learn.astro"]
---

# Surface: smart-bomberman web (Play, Crosstable, How they learned)

Mode: Experience on Play (the match leads), Operate on Crosstable, Read on How they learned.

Audience and job: players fight the real trained agents up a ladder (wanderer, camper, heuristic, Two-Fuse normal, Two-Fuse hard; free roster after the first match) and earn an Elo on the same scale as the agents; curious readers learn how the agents were trained. Desktop-first play; Crosstable and Learn fully usable on phones.

Proof: every number is measured in this repo and labelled (agent ratings from a 200-games-per-pair round robin, v1 vs v2 win rates, training curves from metrics.json). Leaderboard results are verified by replaying the submitted input log on the server with the same engine and agent.

Constraints: Astro + Svelte on Vercel free tier; engine and policies in TypeScript with bit-exact seeded RNG (sfc32) matching the Python reference; policy MLP evaluated in plain TS (no ONNX) so browser and server agree exactly; Upstash Redis (REST) for the leaderboard, in-memory fallback in dev.

## Direction contract

THESIS: The site is a rated tournament hall. You are paired against agents on one Elo scale and the crosstable records every result. It refuses the dark neon arcade portal and the hero-plus-card-row game landing.

OWN-WORLD: Baize-green felt (#1d4a37) owns every surface the paper does not. Cool white pairing slips and scoresheets (#f4f5f0), black ink (#141618) for you, carbon-copy blue (#2340a0) for Two-Fuse and agents, flag red (#d93a2b) for danger, sudden death and losses. Colour only ever means state. Ruled tables with tabular figures, slips pinned slightly askew, twin chess-clock faces in a dark bezel.

STORY: The visitor sees Board 1 already set, reads who they face and what a win is worth, plays, watches the flag drop at sudden death, sees the result stamped into the crosstable and their rating move, then climbs the next rung or reads why the agent played as it did.

FIRST VIEWPORT: Top bar (wordmark left; Play, Crosstable, How they learned right). Left: twin chess clock above the live 13x17 board on a white sheet. Right: the pairing slip with a ruled header row (round, board, map), "You vs <opponent>" set large without wrapping the agent name, ratings line, three stake cells (win, draw, loss), and Start match as the slip's one black button. Crosstable edge visible at the bottom.

FORM: Tournament crosstable world, candidate 3 of 7 on the ordered list, assigned by the roll. Raised by: colour = state only (developer console), fixed cells that never reflow (split-flap), every match sheet prints its hard end (j-card), registered paired views in Learn (curved crease), one field colour at page scale (indoor sun). seed:394a7399d21b0640

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Open decisions
- K-factor and provisional period for player Elo (default K=32, start 1000).
- Whether agent ratings are refreshed when a new model ships (recompute with rate_agents).
