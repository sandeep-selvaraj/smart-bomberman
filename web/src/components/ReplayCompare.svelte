<script lang="ts">
  /**
   * v1 and v2 against an opponent that never moves, from the same seed, side
   * by side. The real exported networks play; nothing here is a recording.
   */
  import { NOOP, type VersusEngine } from "../engine/engine";
  import { newEngine, opponentFor } from "../engine/match";
  import { loadPolicyNet, type PolicyNet } from "../engine/mlp";
  import type { Policy } from "../engine/policies";
  import Board from "./Board.svelte";

  const SEED = 9;
  const TPS = 14;

  interface Lane {
    id: string;
    label: string;
    model: string;
    engine: VersusEngine;
    policy: Policy | null;
    bombs: number;
  }

  let lanes = $state<Lane[]>([
    { id: "v1", label: "v1", model: "/models/two_fuse_v1", engine: newEngine(SEED), policy: null, bombs: 0 },
    { id: "v2", label: "v2", model: "/models/two_fuse", engine: newEngine(SEED), policy: null, bombs: 0 },
  ]);
  let tick = $state(0);
  let state = $state<"idle" | "loading" | "running" | "done" | "error">("idle");
  let timer: ReturnType<typeof setInterval> | null = null;

  async function run() {
    if (timer) clearInterval(timer);
    state = "loading";
    let nets: PolicyNet[];
    try {
      nets = await Promise.all(lanes.map((l) => loadPolicyNet(l.model)));
    } catch {
      state = "error";
      return;
    }
    lanes = lanes.map((lane, i) => ({
      ...lane,
      engine: newEngine(SEED),
      policy: opponentFor("two_fuse_hard", SEED, nets[i]!, 0),
      bombs: 0,
    }));
    tick = 0;
    state = "running";
    timer = setInterval(() => {
      let live = false;
      for (const lane of lanes) {
        if (lane.engine.finished) continue;
        live = true;
        const action = lane.policy!.act(lane.engine, 0);
        if (action === 5) lane.bombs += 1;
        lane.engine.step([action, NOOP]);
      }
      tick += 1;
      if (!live) {
        clearInterval(timer!);
        state = "done";
      }
    }, 1000 / TPS);
  }

  const verdict = (lane: Lane): string => {
    void tick;
    const e = lane.engine;
    if (!e.finished) return `Step ${e.steps} · ${lane.bombs} bombs dropped`;
    const how = e.players[1].killedBy === "opponent_bomb" ? "bombed it" : e.players[1].killedBy === "crushed" ? "waited for the walls" : "won";
    return `Won at step ${e.steps} · ${lane.bombs} bombs · ${how}`;
  };
</script>

<figure class="compare">
  <div class="lanes">
    {#each lanes as lane (lane.id)}
      <div class="lane">
        <p class="name"><strong>{lane.label}</strong> against an opponent that never moves</p>
        <div class="board"><Board engine={lane.engine} {tick} tickMs={1000 / TPS} maxCell={26} label={`${lane.label} replay board`} /></div>
        <p class="stat num" aria-live="polite">{verdict(lane)}</p>
      </div>
    {/each}
  </div>
  <figcaption>
    <button class="btn" type="button" onclick={run} disabled={state === "loading" || state === "running"}>
      {state === "running" ? "Playing…" : state === "loading" ? "Loading both networks…" : state === "done" ? "Play again" : "Play both"}
    </button>
    <span>Same seed, same map (map 3), both at twice the game's speed. The black piece is the agent; the blue one never moves.</span>
    {#if state === "error"}<span class="error">The networks could not be loaded.</span>{/if}
  </figcaption>
</figure>

<style>
  .compare {
    margin: 0;
    display: grid;
    gap: 14px;
  }
  .lanes {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .lane {
    background: var(--sheet);
    color: var(--ink);
    padding: 14px;
    box-shadow: var(--shadow-sheet);
    min-width: 0;
  }
  .name {
    margin-bottom: 10px;
    font-size: 0.95rem;
  }
  .stat {
    margin-top: 10px;
    font-weight: 650;
  }
  figcaption {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px 18px;
    color: var(--chalk-dim);
    font-size: 0.92rem;
  }
  figcaption .btn {
    background: var(--sheet);
    color: var(--ink);
  }
  figcaption .btn:hover:not(:disabled) {
    background: #fff;
  }
  .error {
    color: #ffd2cc;
  }
  @media (max-width: 760px) {
    .lanes {
      grid-template-columns: 1fr;
    }
  }
</style>
