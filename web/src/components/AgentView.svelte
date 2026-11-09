<script lang="ts">
  /**
   * What Two-Fuse sees, live: a seeded match of Two-Fuse against
   * the heuristic bot, the 9x9 window it reads outlined on the board, one of
   * its input planes drawn cell for cell beside it, and the move
   * probabilities its network gives. NetworkView opens over the same match
   * to show the layers in between.
   */
  import { onMount } from "svelte";
  import type { VersusEngine } from "../engine/engine";
  import { newEngine, opponentFor } from "../engine/match";
  import { loadPolicyNet, type PolicyNet } from "../engine/mlp";
  import { observe, VIEW } from "../engine/observation";
  import type { Policy } from "../engine/policies";
  import Board from "./Board.svelte";
  import NetworkView from "./NetworkView.svelte";

  const SEED = 222732;
  const PLANES = [
    { index: 0, label: "Walls", note: "Solid walls; outside the map counts as wall." },
    { index: 1, label: "Breakable", note: "Walls a bomb can open." },
    { index: 2, label: "Bombs", note: "Each bomb, shaded by the fuse it has left." },
    { index: 4, label: "Danger", note: "Cells a blast or a closing wall will reach, darker when sooner." },
    { index: 5, label: "Hostiles", note: "Wandering enemies and the opponent." },
    { index: 7, label: "Opponent", note: "Only the opponent." },
    { index: 8, label: "Closing", note: "Cells sudden death will close soon." },
  ];
  const MOVES = ["Stay", "Up", "Down", "Left", "Right", "Bomb"];

  let engine = $state<VersusEngine>(newEngine(SEED));
  let tick = $state(0);
  let plane = $state(0);
  let running = $state(false);
  let ready = $state(false);
  let failed = $state(false);
  let inside = $state(false);
  let insideSpeed = $state(1);
  // the network view needs time for a step to play through the layers
  let tps = $derived(inside ? insideSpeed : 4);
  let net = $state.raw<PolicyNet | null>(null);
  let me: Policy | null = null;
  let them: Policy | null = null;

  let reading = $derived.by(() => {
    void tick;
    const obs = observe(engine, 0);
    const acts = net ? net.activations(obs) : [];
    const logits = Array.from(acts.at(-1) ?? []);
    const peak = Math.max(...logits);
    const exp = logits.map((l) => Math.exp(l - peak));
    const total = exp.reduce((a, b) => a + b, 0) || 1;
    const probs = exp.map((e) => e / total);
    return { local: obs.local, acts, probs, best: probs.indexOf(Math.max(...probs)), steps: engine.steps };
  });

  function reset() {
    engine = newEngine(SEED);
    if (net) {
      me = opponentFor("two_fuse_hard", SEED, net, 0);
      them = opponentFor("heuristic", SEED, null, 1);
    }
    tick = 0;
  }

  function step() {
    if (!me || !them) return;
    if (engine.finished) {
      reset();
      return;
    }
    engine.step([me.act(engine, 0), them.act(engine, 1)]);
    tick += 1;
  }

  function toggle() {
    running = !running;
  }

  $effect(() => {
    if (!running) return;
    const timer = setInterval(step, 1000 / tps);
    return () => clearInterval(timer);
  });

  onMount(() => {
    loadPolicyNet("/models/two_fuse")
      .then((loaded) => {
        net = loaded;
        reset();
        ready = true;
      })
      .catch(() => (failed = true));
  });
</script>

<figure class="view">
  <div class="panes">
    <div class="pane board panel">
      <Board skins={["two_fuse_hard", "heuristic"]} {engine} {tick} tickMs={1000 / tps} viewFor={0} label="The match Two-Fuse is playing, with its 9 by 9 view outlined" />
      <div class="controls">
    <button class="btn" type="button" onclick={toggle} disabled={!ready}>{running ? "Pause" : tick ? "Resume" : "Play"}</button>
    <button class="btn btn-step" type="button" onclick={step} disabled={!ready || running}>One step</button>
    <span>
      {failed ? "The network could not be loaded." : `Two-Fuse on hard (red and white) against the heuristic robot. Step ${reading.steps}.`}
    </span>
      </div>
    </div>
    <div class="pane eye panel">
      <p class="head">{PLANES.find((p) => p.index === plane)?.label} plane</p>
      <div class="grid" role="img" aria-label="The 9 by 9 input plane, registered to the outlined window">
        {#each Array(VIEW * VIEW) as _, i (i)}
          <i style:opacity={0.06 + 0.94 * (reading.local[plane * VIEW * VIEW + i] ?? 0)} class:centre={i === 40}></i>
        {/each}
      </div>
      <p class="note">{PLANES.find((p) => p.index === plane)?.note}</p>
      <div class="planes" role="radiogroup" aria-label="Input plane">
        {#each PLANES as p (p.index)}
          <button type="button" role="radio" aria-checked={plane === p.index} onclick={() => (plane = p.index)}>{p.label}</button>
        {/each}
      </div>
      <p class="head moves-head">What it does next</p>
      <ol class="moves">
        {#each MOVES as move, i (move)}
          <li class:best={i === reading.best && ready}>
            <span>{move}</span>
            <span class="bar"><i style:width={`${(reading.probs[i] ?? 0) * 100}%`}></i></span>
            <span class="num">{ready ? `${Math.round((reading.probs[i] ?? 0) * 100)}%` : ""}</span>
          </li>
        {/each}
      </ol>
      <button class="btn btn-quiet inside" type="button" onclick={() => (inside = true)} disabled={!ready}>See inside the network</button>
    </div>
  </div>
  <NetworkView
    bind:open={inside}
    bind:speed={insideSpeed}
    {net}
    {engine}
    {tick}
    tickMs={1000 / tps}
    acts={reading.acts}
    probs={reading.probs}
    best={reading.best}
    {running}
    ontoggle={toggle}
    onstep={step}
  />
</figure>

<style>
  .view {
    margin: 0;
    display: grid;
    gap: 14px;
  }
  .panes {
    display: grid;
    grid-template-columns: minmax(0, 1.5fr) minmax(260px, 0.8fr);
    gap: 14px;
  }
  .pane {
    background: var(--panel);
    color: var(--text);
    padding: 14px;
    
    min-width: 0;
  }
  .board {
    display: grid;
    align-content: space-between;
    gap: 14px;
  }
  .head {
    font-weight: 700;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(9, 1fr);
    gap: 2px;
    margin: 10px 0;
    max-width: 260px;
  }
  .grid i {
    aspect-ratio: 1;
    background: var(--text);
    border-radius: 1px;
  }
  .grid i.centre {
    outline: 2px solid var(--two-fuse);
    outline-offset: -1px;
  }
  .note {
    font-size: 0.86rem;
    color: var(--text-dim);
    min-height: 2.6em;
  }
  .planes {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 10px 0 18px;
  }
  .planes button {
    border: 2px solid var(--edge);
    border-radius: 3px;
    background: var(--panel-2);
    padding: 5px 9px 6px;
    font-family: var(--pixel);
    font-size: 0.72rem;
    cursor: pointer;
    box-shadow:
      inset 0 2px 0 var(--bevel-light),
      inset 0 -3px 0 var(--bevel-dark);
  }
  .planes button[aria-checked="true"] {
    background: var(--you);
    color: var(--bg-deep);
  }
  .moves-head {
    border-top: 1px solid var(--line);
    padding-top: 12px;
  }
  .moves {
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
    display: grid;
    gap: 4px;
    font-size: 0.9rem;
  }
  .moves li {
    display: grid;
    grid-template-columns: 4.2em 1fr 3em;
    align-items: center;
    gap: 8px;
  }
  .bar {
    height: 8px;
    background: var(--panel-2);
    border-radius: 2px;
    overflow: hidden;
  }
  .bar i {
    display: block;
    height: 100%;
    background: var(--line);
    border-radius: 0 2px 2px 0;
    transition: width 200ms var(--ease-out);
  }
  .best {
    font-weight: 700;
  }
  .best .bar i {
    background: var(--text);
  }
  .moves .num {
    text-align: right;
  }
  .inside {
    margin-top: 16px;
    width: 100%;
    font-size: 0.85rem;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px 14px;
    color: var(--text-dim);
    font-size: 0.92rem;
  }
  .controls .btn {
    background: var(--panel);
    color: var(--text);
    padding: 0.7em 1.2em;
    font-size: 1rem;
  }
  .controls .btn:hover:not(:disabled) {
    background: #fff;
  }
  .controls .btn:disabled {
    opacity: 0.6;
  }
  @media (max-width: 860px) {
    .panes {
      grid-template-columns: 1fr;
    }
  }
</style>
