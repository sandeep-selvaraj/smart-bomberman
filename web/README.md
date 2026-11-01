# smart-bomberman on the web

Play Battle mode in the browser against the trained agents, climb a ladder, and land on a crosstable rated on the
agents' own Elo scale. A second page explains how Two-Fuse was trained, with the real networks running live.

- **Play** (`/`): the board, the twin clock, the pairing slip and your ladder.
- **Crosstable** (`/crosstable`): every player and agent on one Elo scale, with each player's record against each agent.
- **How they learned** (`/learn`): the training story, the agent's own view, v1 against v2, and the measured results.

## How it works

- `src/engine/` is a TypeScript port of the Python Battle-mode engine, the scripted bots and Two-Fuse's network
  (plain arithmetic, no ONNX runtime). `tests/parity.test.ts` replays 12 matches recorded in Python and requires every
  state, every move, every observation and the network's outputs to match.
- A match is fully determined by its seed (the `sfc32` generator in `src/engine/rng.ts`, mirrored by `SeedRng` in
  `src/game/ai/web_export.py`). The server hands out a signed seed (`/api/start`), the browser sends back the finished
  input log (`/api/submit`), and the server replays the match with the same engine and agent before it changes any
  rating. A ticket is good for one result within two hours.
- Agent ratings are fixed anchors from a 200-games-per-pair round robin (`src/data/agents.json`). Players start at
  1000; K is 40 for the first 10 games, then 24.

## Run it

```bash
npm install
npm run dev        # http://localhost:4321, leaderboard kept in memory
npm test           # parity and server tests
npm run check      # astro + TypeScript
npm run build
```

## Deploy on Vercel (free tier)

1. Import the repository and set the **Root Directory** to `web`.
2. Add a Redis store from the Vercel Marketplace (Upstash, free plan). It sets `KV_REST_API_URL` and
   `KV_REST_API_TOKEN`; `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` work too.
3. Set `MATCH_SECRET` to a long random string (`openssl rand -hex 32`). Without it, production refuses ranked play
   and every match is practice.

## Refresh the data after training a new model

From the repository root:

```bash
uv run smart-bomberman export-web               # maps, weights, training curves, parity fixtures
uv run smart-bomberman export-web --rate True   # also re-run the agents' round robin (about 30 minutes)
cd web && npm test                              # the port must still match
```
