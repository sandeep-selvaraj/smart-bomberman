<script lang="ts">
  /**
   * The twin chess clock above the board. Each face belongs to one fighter and
   * shows their bomb: ready, or the fuse still burning. The red panel counts
   * down to sudden death; when it hits zero its flag falls and it counts the
   * open cells the arena has left. Cells never reflow; only values change.
   */
  interface Side {
    name: string;
    agent: boolean;
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
</script>

<div class="clock" role="group" aria-label="Match clock">
  {#each [you, them] as side, i (i)}
    <div class="face" class:agent={side.agent} class:out={!side.alive}>
      <span class="who">{side.name}</span>
      <span class="reading num" aria-live="off">
        {#if !side.alive}
          Out
        {:else if side.fuse === null}
          Bomb ready
        {:else}
          Fuse {side.fuse}
        {/if}
      </span>
    </div>
  {/each}
  <div class="flag-panel" class:fallen class:warning>
    <span class="flag" aria-hidden="true"></span>
    <span class="who">{fallen ? "Arena closing" : "Sudden death in"}</span>
    <span class="reading num">{fallen ? `${openCells} cells left` : left}</span>
    <span class="end">Hard end {hardEnd}</span>
  </div>
</div>

<style>
  .clock {
    display: grid;
    grid-template-columns: 1fr 1fr minmax(150px, 0.8fr);
    gap: 8px;
    padding: 8px;
    background: var(--bezel);
    border-radius: 6px;
    box-shadow:
      inset 0 1px 0 rgb(255 255 255 / 0.06),
      0 10px 24px -16px rgb(0 0 0 / 0.7);
  }
  .face,
  .flag-panel {
    position: relative;
    display: grid;
    align-content: center;
    gap: 2px;
    min-height: 84px;
    padding: 10px 16px 12px;
    background: var(--sheet);
    color: var(--ink);
    border-radius: 2px;
  }
  .who {
    font-size: 0.8rem;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .reading {
    font-size: clamp(1.4rem, 2.6vw, 2.35rem);
    font-weight: 780;
    line-height: 1.05;
    white-space: nowrap;
  }
  .agent .reading,
  .agent .who {
    color: var(--agent);
  }
  .out {
    background: var(--sheet-alt);
  }
  .out .reading {
    color: var(--ink-faint);
  }
  /* paper until sudden death; the flag falls and the panel turns red only then */
  .flag-panel {
    overflow: hidden;
    transition:
      background 500ms var(--ease-out) 300ms,
      color 500ms var(--ease-out) 300ms;
  }
  .warning .reading {
    color: var(--flag-ink);
  }
  .fallen {
    background: var(--flag);
    color: #fff;
  }
  .end {
    font-size: 0.78rem;
    opacity: 0.92;
  }
  /* the clock's flag: a small pennant that falls when sudden death begins */
  .flag {
    position: absolute;
    top: 6px;
    right: 14px;
    width: 2px;
    height: 24px;
    background: var(--ink);
    transform-origin: 1px 24px;
    transition: transform 650ms cubic-bezier(0.5, 0, 0.75, 0); /* a fall accelerates */
  }
  .flag::after {
    content: "";
    position: absolute;
    left: 2px;
    top: 0;
    width: 16px;
    height: 11px;
    background: var(--flag);
    clip-path: polygon(0 0, 100% 50%, 0 100%);
  }
  .fallen .flag {
    transform: rotate(100deg);
    background: #fff;
  }
  .fallen .flag::after {
    background: #fff;
  }
  @media (max-width: 720px) {
    .clock {
      grid-template-columns: 1fr 1fr;
    }
    .flag-panel {
      grid-column: 1 / -1;
      min-height: 64px;
    }
  }
</style>
