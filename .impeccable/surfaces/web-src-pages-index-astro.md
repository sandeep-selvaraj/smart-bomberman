---
version: 1
slug: "web-src-pages-index-astro"
primary_target: "web/src/pages/index.astro"
related_targets: ["web/src/pages/crosstable.astro","web/src/pages/learn.astro"]
---

# Surface: smart-bomberman web (Play, Crosstable, How they learned)

Mode: Experience on Play (the match leads), Operate on Crosstable, Read on How they learned.

Audience and job: players fight the real trained agents, choosing opponents from a character-select roster that climbs from the lowest-rated agent to Two-Fuse on hard (the whole roster opens after one match), and earn an Elo on the agents' own scale; curious readers learn how the agents were trained. Desktop-first play; Crosstable and Learn fully usable on phones.

Proof: every number is measured in this repo and labelled. Leaderboard results are verified by replaying the submitted input log on the server with the same engine and agent.

Constraints: Astro + Svelte on Vercel free tier; TypeScript engine with bit-exact seeded RNG matching Python; policy MLP in plain TS; Upstash Redis for the leaderboard.

## Direction contract

THESIS: The site looks and feels like the actual game (user-pinned, replacing the earlier tournament-table world): the arena is the original game's grey floor and tile sprites, the page is its HUD navy, and the opponents are characters you pick from a roster. It refuses the chess-table metaphor and refuses reusing any existing franchise's characters.

OWN-WORLD: Page #1e1e28 (the pygame HUD bar), deep #14141c, bevelled menu panels #2a2a37 with a dark #0c0c12 frame. Arena: grey #808080 checker floor; the repo's own wall, brick, stone, bomb and explosion sprites, drawn pixel-crisp. Original 16x16 characters: you (generic adventurer, yellow jacket #f2b51d), Spark hazards, Camper (tent), Wanderer (sprout slime), Heuristic (robot), Two-Fuse normal/hard (split two-face bomb with two fuses). Yellow is yours (buttons, your name); red #ff5a5a is danger and sudden death (the original HUD red); each agent's name wears its character's colour. Silkscreen pixel lettering for the game's words; Archivo for reading.

STORY: The visitor sees the arena set, both fighters squared off on a VS card with the stakes, starts, watches the HUD flip to SUDDEN DEATH, gets a big YOU WIN / YOU LOSE, records the result and sees their line move among the agents, then picks the next opponent from the roster or reads how the agent learned.

FIRST VIEWPORT: Top HUD bar (pixel wordmark left; Play, Crosstable, How they learned right). Left: match HUD (your portrait and bomb, sudden-death countdown, opponent portrait and bomb) above the arena. Right: VS card (round, map, rated; both portraits with names and ratings; win/draw/loss stakes; yellow Start match) and "Where you stand" below it. The roster sits under the arena in the left column; locked opponents show their own characters, dimmed.

FORM: User-pinned direction ("like the actual game", keep generic tiles, original characters, unique agent makeovers); no roll was run for this world. It supersedes the earlier roll seed:394a7399d21b0640, which had assigned the tournament crosstable.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Open decisions
- K-factor and provisional period for player Elo (K=40 for 10 games, then 24; start 1000).
