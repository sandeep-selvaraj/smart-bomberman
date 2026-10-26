<script lang="ts">
  /**
   * The match board, drawn on a canvas as a ruled sheet: ink walls, hatched
   * breakable walls, bombs as clock dials whose filled sector is the fuse
   * left, red where danger is. Fighters glide between tiles at the tick rate.
   */
  import { onMount } from "svelte";
  import type { VersusEngine } from "../engine/engine";
  import { VIEW_RADIUS } from "../engine/observation";

  interface Props {
    engine: VersusEngine;
    tick: number;
    tickMs: number;
    /** Outline the 9x9 window this player's agent sees. */
    viewFor?: number | null;
    maxCell?: number;
    label?: string;
  }

  let { engine, tick, tickMs, viewFor = null, maxCell = 44, label = "Match board" }: Props = $props();

  const C = {
    sheet: "#f4f5f0",
    rule: "#d5d8cf",
    wall: "#2b2f33",
    hatch: "#8d928a",
    you: "#141618",
    agent: "#2340a0",
    flag: "#d93a2b",
    flagWash: "rgba(217, 58, 43, 0.16)",
  };

  let canvas: HTMLCanvasElement;
  let wrap: HTMLDivElement;
  let cell = $state(32);
  let tickAt = performance.now();
  let previous: Array<[number, number]> = [];
  let current: Array<[number, number]> = [];

  const actors = (): Array<[number, number]> => [
    ...engine.players.map((p): [number, number] => [p.r, p.c]),
    ...engine.enemies.map((e): [number, number] => [e.r, e.c]),
  ];

  $effect(() => {
    void tick;
    void engine;
    previous = current.length === engine.players.length + engine.enemies.length ? current : actors();
    current = actors();
    tickAt = performance.now();
  });

  function resize() {
    const width = wrap.clientWidth;
    cell = Math.max(6, Math.min(maxCell, Math.floor(width / engine.width)));
    const ratio = window.devicePixelRatio || 1;
    canvas.width = engine.width * cell * ratio;
    canvas.height = engine.height * cell * ratio;
    canvas.style.width = `${engine.width * cell}px`;
    canvas.style.height = `${engine.height * cell}px`;
    canvas.getContext("2d")!.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function hatch(ctx: CanvasRenderingContext2D, x: number, y: number, s: number, color: string, gap: number, cross: boolean) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(x, y, s, s);
    ctx.clip();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (let k = -s; k < s; k += gap) {
      ctx.moveTo(x + k, y + s);
      ctx.lineTo(x + k + s, y);
      if (cross) {
        ctx.moveTo(x + k, y);
        ctx.lineTo(x + k + s, y + s);
      }
    }
    ctx.stroke();
    ctx.restore();
  }

  function draw(now: number) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const s = cell;
    const { height, width } = engine;
    const t = Math.min(1, (now - tickAt) / Math.max(tickMs, 1));
    const ease = 1 - (1 - t) ** 3;
    ctx.fillStyle = C.sheet;
    ctx.fillRect(0, 0, width * s, height * s);

    const closing = engine.closingMap();
    const danger = engine.dangerMap();
    const closedFrom = new Set(engine.closingOrder.slice(0, engine.closed).map(([r, c]) => r * width + c));

    for (let r = 0; r < height; r++) {
      for (let c = 0; c < width; c++) {
        const i = r * width + c;
        const x = c * s;
        const y = r * s;
        if (engine.solid[i]) {
          ctx.fillStyle = C.wall;
          ctx.fillRect(x, y, s, s);
          if (closedFrom.has(i)) hatch(ctx, x, y, s, "rgba(217,58,43,0.55)", 5, false);
          continue;
        }
        ctx.strokeStyle = C.rule;
        ctx.lineWidth = 1;
        ctx.strokeRect(x + 0.5, y + 0.5, s - 1, s - 1);
        if (engine.wallHp[i]! > 0) hatch(ctx, x + 2, y + 2, s - 4, C.hatch, 5, engine.wallHp[i]! > 1);
        if (closing[i]! > 0) {
          ctx.fillStyle = `rgba(217, 58, 43, ${0.12 + 0.5 * closing[i]!})`;
          ctx.fillRect(x, y, s, s);
        } else if (danger[i]! > 0.6 && engine.flames[i] === 0) {
          ctx.fillStyle = C.flagWash;
          ctx.fillRect(x, y, s, s);
        }
        if (engine.flames[i]! > 0) {
          ctx.fillStyle = C.flag;
          ctx.fillRect(x + 2, y + 2, s - 4, s - 4);
        }
      }
    }

    for (const bomb of engine.bombs) {
      const cx = bomb.c * s + s / 2;
      const cy = bomb.r * s + s / 2;
      const radius = s * 0.34;
      const color = bomb.owner === 0 ? C.you : C.agent;
      ctx.fillStyle = C.sheet;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + (Math.PI * 2 * bomb.timer) / engine.config.bombFuse);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.stroke();
    }

    const at = (k: number): [number, number] => {
      const [r1, c1] = current[k] ?? [0, 0];
      const [r0, c0] = previous[k] ?? [r1, c1];
      const far = Math.abs(r1 - r0) + Math.abs(c1 - c0) > 1;
      return far ? [r1, c1] : [r0 + (r1 - r0) * ease, c0 + (c1 - c0) * ease];
    };

    engine.enemies.forEach((enemy, k) => {
      if (!enemy.alive) return;
      const [r, c] = at(engine.players.length + k);
      const cx = c * s + s / 2;
      const cy = r * s + s / 2;
      const d = s * 0.26;
      ctx.fillStyle = C.flag;
      ctx.beginPath();
      ctx.moveTo(cx, cy - d);
      ctx.lineTo(cx + d, cy);
      ctx.lineTo(cx, cy + d);
      ctx.lineTo(cx - d, cy);
      ctx.closePath();
      ctx.fill();
    });

    engine.players.forEach((fighter, p) => {
      const [r, c] = at(p);
      const cx = c * s + s / 2;
      const cy = r * s + s / 2;
      const color = p === 0 ? C.you : C.agent;
      if (!fighter.alive) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        const d = s * 0.26;
        ctx.beginPath();
        ctx.moveTo(cx - d, cy - d);
        ctx.lineTo(cx + d, cy + d);
        ctx.moveTo(cx + d, cy - d);
        ctx.lineTo(cx - d, cy + d);
        ctx.stroke();
        return;
      }
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(cx, cy, s * 0.36, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = C.sheet;
      ctx.lineWidth = Math.max(1.5, s * 0.06);
      ctx.beginPath();
      ctx.arc(cx, cy, s * 0.21, 0, Math.PI * 2);
      ctx.stroke();
    });

    if (viewFor !== null) {
      const fighter = engine.players[viewFor]!;
      const [r, c] = at(viewFor);
      const size = (2 * VIEW_RADIUS + 1) * s;
      ctx.strokeStyle = viewFor === 0 ? C.you : C.agent;
      ctx.lineWidth = 3;
      ctx.setLineDash(fighter.alive ? [] : [6, 4]);
      ctx.strokeRect((c - VIEW_RADIUS) * s + 1.5, (r - VIEW_RADIUS) * s + 1.5, size - 3, size - 3);
      ctx.setLineDash([]);
    }
  }

  onMount(() => {
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(wrap);
    let frame = 0;
    const loop = (now: number) => {
      draw(now);
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  });
</script>

<div class="board" bind:this={wrap}>
  <canvas bind:this={canvas} role="img" aria-label={label}></canvas>
</div>

<style>
  .board {
    width: 100%;
    display: flex;
    justify-content: center;
  }
  canvas {
    display: block;
    max-width: 100%;
    height: auto !important;
  }
</style>
