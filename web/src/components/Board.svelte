<script lang="ts">
  /**
   * The arena, drawn like the game: grey floor, the original wall, brick and
   * stone tiles, the original bomb and explosion sprites, and pixel-art
   * characters that walk between tiles at the tick rate. The canvas is drawn
   * at 32 px per tile and scaled with crisp pixels to fit its column.
   */
  import { onMount } from "svelte";
  import type { VersusEngine } from "../engine/engine";
  import { VIEW_RADIUS } from "../engine/observation";
  import { drawCharacter, loadTiles, type CharacterKey, type Tiles } from "../art/sprites";

  interface Props {
    engine: VersusEngine;
    tick: number;
    tickMs: number;
    /** Characters for player 0 and player 1. */
    skins: [CharacterKey, CharacterKey];
    /** Outline the 9x9 window this player sees. */
    viewFor?: number | null;
    label?: string;
  }

  let { engine, tick, tickMs, skins, viewFor = null, label = "Match board" }: Props = $props();

  const T = 32;
  let canvas: HTMLCanvasElement;
  let tiles: Tiles | null = null;
  let tickAt = performance.now();
  let previous: Array<[number, number]> = [];
  let current: Array<[number, number]> = [];
  let facing: boolean[] = [];

  const actors = (): Array<[number, number]> => [
    ...engine.players.map((p): [number, number] => [p.r, p.c]),
    ...engine.enemies.map((e): [number, number] => [e.r, e.c]),
  ];

  $effect(() => {
    void tick;
    void engine;
    const next = actors();
    previous = current.length === next.length ? current : next;
    facing = next.map(([, c], k) => {
      const before = previous[k];
      if (!before || before[1] === c) return facing[k] ?? false;
      return c < before[1];
    });
    current = next;
    tickAt = performance.now();
    if (canvas && (canvas.width !== engine.width * T || canvas.height !== engine.height * T)) {
      canvas.width = engine.width * T;
      canvas.height = engine.height * T;
    }
  });

  function draw(now: number) {
    const ctx = canvas.getContext("2d");
    if (!ctx || !tiles) return;
    ctx.imageSmoothingEnabled = false;
    const { height, width } = engine;
    const t = Math.min(1, (now - tickAt) / Math.max(tickMs, 1));
    const ease = 1 - (1 - t) ** 2;
    const closing = engine.closingMap();
    const danger = engine.dangerMap();
    const closed = new Set(engine.closingOrder.slice(0, engine.closed).map(([r, c]) => r * width + c));

    for (let r = 0; r < height; r++) {
      for (let c = 0; c < width; c++) {
        const i = r * width + c;
        const x = c * T;
        const y = r * T;
        if (engine.solid[i]) {
          ctx.drawImage(tiles.wall, x, y, T, T);
          if (closed.has(i)) {
            ctx.fillStyle = "rgba(255, 60, 60, 0.38)";
            ctx.fillRect(x, y, T, T);
          }
          continue;
        }
        ctx.fillStyle = (r + c) % 2 ? "#7b7b7b" : "#838383";
        ctx.fillRect(x, y, T, T);
        if (engine.wallHp[i]! > 1) ctx.drawImage(tiles.stone, x, y, T, T);
        else if (engine.wallHp[i]! > 0) ctx.drawImage(tiles.brick, x, y, T, T);
        if (closing[i]! > 0) {
          ctx.fillStyle = `rgba(255, 60, 60, ${0.15 + 0.5 * closing[i]!})`;
          ctx.fillRect(x, y, T, T);
        } else if (danger[i]! > 0.6 && engine.flames[i] === 0) {
          ctx.fillStyle = "rgba(255, 60, 60, 0.2)";
          ctx.fillRect(x, y, T, T);
        }
      }
    }

    const blink = Math.floor(now / 160) % 2;
    for (const bomb of engine.bombs) {
      const swell = bomb.timer <= 3 ? 1 + 0.12 * blink : 1;
      const size = T * swell;
      const off = (T - size) / 2;
      ctx.drawImage(tiles.bomb, blink * 32, 0, 32, 32, bomb.c * T + off, bomb.r * T + off, size, size);
    }
    for (let r = 0; r < height; r++) {
      for (let c = 0; c < width; c++) {
        if (engine.flames[r * width + c]! > 0) ctx.drawImage(tiles.explosion, c * T, r * T, T, T);
      }
    }

    const at = (k: number): [number, number] => {
      const [r1, c1] = current[k] ?? [0, 0];
      const [r0, c0] = previous[k] ?? [r1, c1];
      const far = Math.abs(r1 - r0) + Math.abs(c1 - c0) > 1;
      return far ? [r1, c1] : [r0 + (r1 - r0) * ease, c0 + (c1 - c0) * ease];
    };
    const moving = (k: number) => {
      const a = current[k];
      const b = previous[k];
      return !!a && !!b && (a[0] !== b[0] || a[1] !== b[1]) && t < 1;
    };
    const step = Math.floor(now / 140) % 2;

    engine.enemies.forEach((enemy, k) => {
      if (!enemy.alive) return;
      const [r, c] = at(engine.players.length + k);
      drawCharacter(ctx, "spark", step, c * T, r * T, T, facing[engine.players.length + k]);
    });

    engine.players.forEach((fighter, p) => {
      const [r, c] = at(p);
      ctx.save();
      if (!fighter.alive) ctx.globalAlpha = 0.35;
      drawCharacter(ctx, skins[p], moving(p) ? step : 0, c * T, r * T, T, facing[p]);
      ctx.restore();
      if (!fighter.alive) {
        ctx.strokeStyle = "#ff3c3c";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(c * T + 6, r * T + 6);
        ctx.lineTo(c * T + T - 6, r * T + T - 6);
        ctx.moveTo(c * T + T - 6, r * T + 6);
        ctx.lineTo(c * T + 6, r * T + T - 6);
        ctx.stroke();
      }
    });

    if (viewFor !== null) {
      const [r, c] = at(viewFor);
      const size = (2 * VIEW_RADIUS + 1) * T;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 4;
      ctx.setLineDash([10, 6]);
      ctx.strokeRect((c - VIEW_RADIUS) * T + 2, (r - VIEW_RADIUS) * T + 2, size - 4, size - 4);
      ctx.setLineDash([]);
    }
  }

  onMount(() => {
    canvas.width = engine.width * T;
    canvas.height = engine.height * T;
    let frame = 0;
    loadTiles().then((loaded) => (tiles = loaded));
    const loop = (now: number) => {
      draw(now);
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  });
</script>

<canvas bind:this={canvas} role="img" aria-label={label}></canvas>

<style>
  canvas {
    display: block;
    width: 100%;
    height: auto;
    image-rendering: pixelated;
  }
</style>
