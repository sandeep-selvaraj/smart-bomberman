<script lang="ts">
  /**
   * The match HUD above the arena, like the original game's top bar: each
   * fighter's portrait and bomb, and the countdown to sudden death in the
   * middle. When it runs out the timer turns into the original red SUDDEN
   * DEATH banner and counts the cells the arena has left. Cells never reflow.
   */
  import type { CharacterKey } from "../art/sprites";
  import { SIGNATURE } from "../art/sprites";
  import Sprite from "./Sprite.svelte";

  interface Side {
    name: string;
    character: CharacterKey;
    alive: boolean;
    fuse: number | null; // steps left on their live bomb, or null when the bomb is ready
  }

  interface Props {
    you: Side;
    them: Side;
    steps: number;
    suddenDeathStart: number;
    maxSteps: number;
    openCells: number;
    tps: number;
  }

  let { you, them, steps, suddenDeathStart, maxSteps, openCells, tps }: Props = $props();

  const clock = (s: number): string => {
    const seconds = Math.max(0, Math.ceil(s / tps));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  };

  let fallen = $derived(steps >= suddenDeathStart);
  let warning = $derived(!fallen && suddenDeathStart - steps <= 12);
  let left = $derived(clock(suddenDeathStart - steps));
  let hardEnd = $derived(clock(maxSteps));
  const status = (side: Side): string => (!side.alive ? "Out" : side.fuse === null ? "Bomb ready" : `Fuse ${side.fuse}`);
</script>

<div class="hud panel" role="group" aria-label="Match status">
  {#each [you, them] as side, i (i)}
    <div class="side" class:right={i === 1} class:out={!side.alive}>
      <Sprite character={side.character} size={44} dim={!side.alive} />
      <div class="who">
        <span class="name" style:color={SIGNATURE[side.character]}>{side.name}</span>
        <span class="status" class:lit={side.fuse !== null && side.alive}>
          <i class="bomb" class:spent={side.fuse !== null || !side.alive} aria-hidden="true"></i>{status(side)}
        </span>
      </div>
    </div>
  {/each}
  <div class="timer" class:fallen class:warning>
    {#if fallen}
      <span class="value banner">Sudden death</span>
      <span class="cells num">{openCells} cells left</span>
    {:else}
      <span class="label">Sudden death in</span>
      <span class="value num">{left}</span>
    {/if}
    <span class="end">Hard end {hardEnd}</span>
  </div>
</div>

<style>
  .hud {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    grid-template-areas: "you timer them";
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    background: var(--bg-deep);
  }
  .side {
    grid-area: you;
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }
  .side.right {
    grid-area: them;
    flex-direction: row-reverse;
    text-align: right;
  }
  .who {
    display: grid;
    min-width: 0;
  }
  .name {
    font-family: var(--pixel);
    font-size: 1.05rem;
    font-weight: 700;
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .status {
    font-family: var(--pixel);
    font-size: 0.82rem;
    white-space: nowrap;
    color: var(--text-dim);
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .right .status {
    flex-direction: row-reverse;
  }
  .status.lit {
    color: var(--fuse);
  }
  .bomb {
    flex: none;
    width: 16px;
    height: 16px;
    border-radius: 2px;
    background: var(--floor) url("/sprites/bomb.png") 0 0 / 32px 16px;
    image-rendering: pixelated;
  }
  .bomb.spent {
    opacity: 0.3;
  }
  .out .name {
    opacity: 0.5;
  }
  .timer {
    grid-area: timer;
    display: grid;
    justify-items: center;
    min-width: 170px;
    padding: 6px 14px;
    border-radius: 3px;
    font-family: var(--pixel);
  }
  .label,
  .banner {
    font-size: 0.78rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .value {
    font-size: 1.7rem;
    font-weight: 700;
    line-height: 1.1;
  }
  .end {
    font-size: 0.72rem;
    color: var(--text-faint);
  }
  .warning .value {
    color: var(--danger);
  }
  .fallen {
    background: var(--danger);
    color: var(--bg-deep);
    animation: drop 500ms var(--ease-out);
  }
  .fallen .banner {
    color: var(--bg-deep);
    font-size: 1.35rem;
    letter-spacing: 0;
    animation: blink 900ms steps(2, start) 3;
  }
  .cells {
    font-size: 0.85rem;
    font-weight: 700;
  }
  .fallen .end {
    color: var(--bg-deep);
  }
  @keyframes drop {
    from {
      transform: translateY(-10px) scale(1.12);
    }
  }
  @keyframes blink {
    to {
      opacity: 0.6;
    }
  }
  @media (max-width: 720px) {
    .hud {
      grid-template-columns: 1fr 1fr;
      grid-template-areas:
        "you them"
        "timer timer";
    }
    .name {
      font-size: 0.9rem;
    }
    .status {
      font-size: 0.7rem;
    }
    .side :global(canvas) {
      width: 32px !important;
      height: 32px !important;
    }
  }
</style>
