# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

- **Front end:** Svelte / Astro (user's choice). The split between Astro pages and Svelte islands is still open.
- **Hosting:** Vercel free tier (user's choice).
- **Agent runtime:** the agents run in the browser, with the game engine ported to TypeScript and the PyTorch policies exported to ONNX. *This was inferred, not chosen by the user.* The user picked "deploy to Vercel free tier" when asked between browser and Python server. Vercel's free serverless functions cannot hold PyTorch and SB3 or keep a game loop running, so running in the browser is the option that fits. Confirm this before building.
- **Leaderboard backend:** a Vercel serverless function plus a free-tier store. Which store (e.g. Upstash Redis or Neon Postgres) is undecided.
- **Existing code:** the Python project (pygame game, Gymnasium env, SB3 training) stays the source of truth for training. The web app plays the trained models; it does not train them.

## Users

- **Players** who open the site to play Bomberman-style Battle mode against the project's AI agents and see how they rank against everyone else.
- **Curious readers**, such as students, ML practitioners and recruiters, who want to understand how the agents were trained.

*The user did not rank one audience above the other.*

## Product Purpose

Turn the smart-bomberman prototype (a desktop pygame game with reinforcement-learning agents) into a web application with two parts:

1. **Play:** a browser game where people play against the different agents, with a global leaderboard.
2. **Learn:** an in-browser explanation of how the agents were trained.

Success means someone can open a link, play a match against a trained agent within seconds, see their result on a shared leaderboard, and understand from the training section why the agent plays the way it does.

## Positioning

The opponents are real reinforcement-learning agents trained for this game, not hand-scripted AI. The training section explains the actual method behind them, using measured results from the project's own experiments.

## Operating Context

The agents available to play against today (Python side):

- **Two-Fuse**, the Battle-mode agent: PPO, warm-started from the single-player agent, then trained by league self-play.
  - *hard*: greedy play
  - *normal*: sampled play
  - The current model is `models/two_fuse.zip` (v2).
- **Scripted bots:** `heuristic` (attacks; this is Two-Fuse's "easy" mode), `camper` (only dodges), `wanderer` (walks at random, never bombs), `random`.
- **Single-player PPO agent** `models/ppo_map1_map2.zip`, which clears maps rather than duelling.

Battle-mode rules:

- Two fighters move at the same time, each with their own bomb, and kills are credited to the bomber.
- Wandering enemies kill either fighter.
- Last one standing wins; dying on the same step is a draw.
- Sudden death starts at step 200 and closes one cell per step in mirrored pairs.
- A coin flip decides the starting corners.

Maps: `arena_1` (13x17, point-symmetric) plus `map_1`–`map_3`.

## Capabilities and Constraints

- **Leaderboard:** global, shared across all players (user's choice).
- **Leaderboard integrity is undecided:**
  - The game runs in the browser, so a submitted result can be faked. How results are validated (for example, replaying a submitted input log on the server) is open.
  - How players are identified (a typed name or an account) is open.
- **Model size:** the policy network is small (an MLP of 256 by 256 over a 9x9 local view plus a state vector), so ONNX inference per tick is cheap in the browser.
- **Engine port:** the TypeScript engine must reproduce the Python engine's rules exactly. Otherwise the exported agents will see different observations than they were trained on, and they will play worse.
- **Terminology:** "Battle mode", "Two-Fuse", "sudden death", "league self-play", and "Elo".

## Brand Commitments

- **Credit:** keep the attribution to *Visual Computing Team Project 2023, TU Dresden, Faculty IMLD*, and the original team (Divyendu Dutta, Juhyun Jonathan Seo, Ken Nakahara, Sandeep Selvaraj).
- **Two-Fuse's name:** the agent's name is Two-Fuse, a Batman-villain pun on Two-Face. The persona's other details are not binding.
- **License:** MIT.

## Evidence on Hand

- Measured results in `README.md` and `docs/EXPERIMENTS.md`:
  - single-player PPO trials
  - Two-Fuse v1 and v2: win rates over 200 games against heuristic, camper and wanderer
  - Elo tournament rankings
  - games won before sudden death against an idle opponent
- Training logs: `runs_two_fuse_v1.log`, `runs_two_fuse_v2.log`. Per-run `metrics.json` files are under `runs/`, which git ignores.
- GIFs: `docs/versus_two_fuse.gif`, `docs/agent_map_1.gif`.
- Original sprites and title art: `src/graphics/`.
- There are no player testimonials, user counts or external press. Do not make these up.

## Product Principles

1. **Honest results only.** Every number on the site comes from a measured run in this repo, labelled with what it measured (games, maps, opponent). Never round a result up into a claim.
2. **Play first, explain second.** The game is the way in. The training story should answer questions a match raises ("why did it wait?", "why is hard so hard?").
3. **The real agents, faithfully.** The browser opponents are the trained models running the same rules they learned on. If the port changes how they behave, it isn't done.
4. **Keep the lineage visible.** It began as a 2023 TU Dresden team project, and the credit stays.
