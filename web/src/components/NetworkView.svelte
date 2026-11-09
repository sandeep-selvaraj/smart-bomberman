<script lang="ts">
  /**
   * Inside the network, live: a full-screen dialog over the match AgentView
   * is playing. Every input, both hidden layers and the six actions are
   * drawn as cells coloured by their current value. Each step plays as a
   * pulse from inputs to action along the strongest connections, found by
   * walking back from one action (mlp.trace). Those lines are the largest
   * weight × value terms, not a full explanation: tanh sits between layers.
   */
  import { untrack } from "svelte";
  import type { VersusEngine } from "../engine/engine";
  import { trace, type Link, type PolicyNet } from "../engine/mlp";
  import { LOCAL_SIZE, VIEW } from "../engine/observation";
  import Board from "./Board.svelte";

  interface Props {
    open: boolean;
    speed: number;
    net: PolicyNet | null;
    engine: VersusEngine;
    tick: number;
    tickMs: number;
    /** Inputs, hidden layers and logits for the current step; empty until the network has loaded. */
    acts: Float64Array[];
    probs: number[];
    best: number;
    running: boolean;
    ontoggle: () => void;
    onstep: () => void;
  }

  let {
    open = $bindable(false),
    speed = $bindable(1),
    net,
    engine,
    tick,
    tickMs,
    acts,
    probs,
    best,
    running,
    ontoggle,
    onstep,
  }: Props = $props();

  const MOVES = ["Stay", "Up", "Down", "Left", "Right", "Bomb"];
  const PLANE_NAMES = ["Walls", "Breakable", "Bombs", "Flames", "Danger", "Hostiles", "Door (unused)", "Opponent", "Closing"];
  const STATE_NAMES = [
    "Its row on the map",
    "Its column on the map",
    "Rows to the opponent",
    "Columns to the opponent",
    "Path length to the opponent",
    "Its bomb is ready",
    "Hostiles still alive",
    "Unused",
    "Danger on its own cell",
    "Up gets closer to the opponent",
    "Down gets closer to the opponent",
    "Left gets closer to the opponent",
    "Right gets closer to the opponent",
    "It could drop a bomb and escape",
    "Up leads towards safety",
    "Down leads towards safety",
    "Left leads towards safety",
    "Right leads towards safety",
    "Distance to the nearest hostile",
    "The opponent's bomb is ready",
    "The opponent's distance to safety",
    "Sudden death has started",
    "Time left before sudden death",
    "Its own cell is about to close",
  ];
  const SPEEDS = [1, 2, 4];
  const PLANE = VIEW * VIEW;
  const POS = "255,138,31"; // --fuse
  const NEG = "90,169,255";
  const INK = "244,244,246"; // --text
  const DIM = "#b7b7c9"; // --text-dim
  const CELL = "#333345"; // --panel-2
  const YOU = "#f2b51d"; // --you
  const SANS = '"Archivo Variable", "Archivo", system-ui, sans-serif';
  /** When each stage of connections plays, and when each layer takes its new values (fractions of a step). */
  const EDGE_WINDOWS: Array<[number, number]> = [
    [0.05, 0.36],
    [0.4, 0.66],
    [0.7, 0.92],
  ];
  const LAYER_WINDOWS: Array<[number, number]> = [
    [0, 0.08],
    [0.3, 0.42],
    [0.6, 0.72],
    [0.88, 1],
  ];

  interface Block {
    layer: number;
    offset: number;
    cols: number;
    rows: number;
    x: number;
    y: number;
    cell: number;
    label: string;
  }
  interface Node {
    x: number;
    y: number;
    hit: [number, number, number, number];
  }
  interface Layout {
    W: number;
    H: number;
    vertical: boolean;
    blocks: Block[];
    nodes: Node[];
    titles: Array<{ text: string; x: number; y: number }>;
  }
  interface Focus {
    layer: number;
    index: number;
  }

  let dialog: HTMLDialogElement;
  let stage = $state<HTMLDivElement>();
  let canvas = $state<HTMLCanvasElement>();
  let wmap = $state<HTMLCanvasElement>();
  let layout = $state<Layout | null>(null);
  let focus = $state<Focus | null>(null);
  let pinned = $state<number | null>(null);

  let target = $derived(pinned ?? best);
  let links = $derived<Link[][]>(net && acts.length ? trace(net, acts, target) : []);
  let push = $derived.by(() => {
    const last = links[2] ?? [];
    return { up: last.filter((l) => l.value > 0).length, down: last.filter((l) => l.value < 0).length };
  });

  // What is on screen: the previous step's values blend into the current ones.
  let prev: Float64Array[] = [];
  let cur: Float64Array[] = [];
  let prevProbs: number[] = [];
  let curProbs: number[] = [];
  let prevBest = 0;
  let curBest = 0;
  let startAt = 0;
  let duration = 900;
  let raf = 0;

  const clamp01 = (v: number) => Math.min(Math.max(v, 0), 1);
  const within = (t: number, [a, b]: [number, number]) => clamp01((t - a) / (b - a));
  const signed = (v: number) => `${v < 0 ? "−" : "+"}${Math.abs(v).toFixed(2)}`;
  const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

  function computeLayout(W: number): Layout {
    const vertical = W < 720;
    const blocks: Block[] = [];
    const nodes: Node[] = [];
    const titles: Layout["titles"] = [];
    const g = 8;
    const lab = 14;
    const planes = (x0: number, y0: number, cell: number): number => {
      const s = cell * VIEW;
      PLANE_NAMES.forEach((label, p) => {
        blocks.push({
          layer: 0,
          offset: p * PLANE,
          cols: VIEW,
          rows: VIEW,
          x: x0 + (p % 3) * (s + g),
          y: y0 + Math.floor(p / 3) * (s + lab + g) + lab,
          cell,
          label,
        });
      });
      const stateCell = Math.floor((3 * s + 2 * g) / 12);
      const y = y0 + 3 * (s + lab + g) + lab;
      blocks.push({ layer: 0, offset: LOCAL_SIZE, cols: 12, rows: 2, x: x0, y, cell: stateCell, label: "24 state values" });
      return y + 2 * stateCell;
    };

    if (!vertical) {
      const H = Math.min(Math.max(W * 0.5, 400), 600);
      const pad = 14;
      const top = 30;
      const Hh = H - top - pad;
      const cell = Math.max(2, Math.floor(Math.min((W * 0.3 - 2 * g) / 3, (Hh - 4 * lab - 3 * g) / 3.6) / VIEW));
      const s = cell * VIEW;
      const inputsHeight = 3 * (s + lab + g) + lab + 2 * Math.floor((3 * s + 2 * g) / 12);
      planes(pad, top + Math.max(0, (Hh - inputsHeight) / 2), cell);
      const xi = pad + 3 * s + 2 * g;
      const aw = 132;
      const ax = W - pad - aw;
      const mid = ax - xi;
      const unit = Math.max(2, Math.floor(Math.min(Hh, mid * 0.3) / 16));
      const sq = unit * 16;
      const gap = (mid - 2 * sq) / 3;
      const y = top + (Hh - sq) / 2;
      blocks.push({ layer: 1, offset: 0, cols: 16, rows: 16, x: xi + gap, y, cell: unit, label: "" });
      blocks.push({ layer: 2, offset: 0, cols: 16, rows: 16, x: xi + 2 * gap + sq, y, cell: unit, label: "" });
      const spacing = Math.min(46, Hh / 6.5);
      MOVES.forEach((_, k) => {
        const ny = top + Hh / 2 + (k - 2.5) * spacing;
        nodes.push({ x: ax + 12, y: ny, hit: [ax, ny - spacing / 2, aw, spacing] });
      });
      titles.push(
        { text: "753 inputs", x: pad, y: 16 },
        { text: "Layer 1 · 256 neurons", x: xi + gap, y: 16 },
        { text: "Layer 2 · 256 neurons", x: xi + 2 * gap + sq, y: 16 },
        { text: "6 actions", x: ax, y: 16 },
      );
      return { W, H, vertical, blocks, nodes, titles };
    }

    const pad = 12;
    const inner = W - 2 * pad;
    const gap = 64;
    const cell = Math.max(2, Math.floor(Math.min((inner - 2 * g) / 3, 120) / VIEW));
    const wide = 3 * cell * VIEW + 2 * g;
    titles.push({ text: "753 inputs", x: pad, y: 16 });
    let y = planes((W - wide) / 2, 26, cell);
    const unit = Math.max(2, Math.floor(Math.min(inner, 288) / 16));
    const sq = unit * 16;
    for (const layer of [1, 2]) {
      y += gap;
      titles.push({ text: `Layer ${layer} · 256 neurons`, x: pad, y: y - 10 });
      blocks.push({ layer, offset: 0, cols: 16, rows: 16, x: (W - sq) / 2, y, cell: unit, label: "" });
      y += sq;
    }
    y += gap;
    titles.push({ text: "6 actions", x: pad, y: y - 24 });
    MOVES.forEach((_, k) => {
      const nx = pad + (inner * (k + 0.5)) / 6;
      nodes.push({ x: nx, y, hit: [nx - inner / 12, y - 16, inner / 6, 62] });
    });
    return { W, H: y + 52, vertical, blocks, nodes, titles };
  }

  function blockOf(lay: Layout, layer: number, index: number): Block | undefined {
    return lay.blocks.find((b) => b.layer === layer && index >= b.offset && index < b.offset + b.cols * b.rows);
  }

  function centre(lay: Layout, layer: number, index: number): [number, number] {
    if (layer === 3) {
      const n = lay.nodes[index]!;
      return [n.x, n.y];
    }
    const b = blockOf(lay, layer, index)!;
    const i = index - b.offset;
    return [b.x + ((i % b.cols) + 0.5) * b.cell, b.y + (Math.floor(i / b.cols) + 0.5) * b.cell];
  }

  function hitTest(lay: Layout, x: number, y: number): Focus | null {
    for (const b of lay.blocks) {
      if (x < b.x || y < b.y || x >= b.x + b.cols * b.cell || y >= b.y + b.rows * b.cell) continue;
      return { layer: b.layer, index: b.offset + Math.floor((y - b.y) / b.cell) * b.cols + Math.floor((x - b.x) / b.cell) };
    }
    const k = lay.nodes.findIndex((n) => x >= n.hit[0] && y >= n.hit[1] && x < n.hit[0] + n.hit[2] && y < n.hit[1] + n.hit[3]);
    return k >= 0 ? { layer: 3, index: k } : null;
  }

  function draw(now: number): boolean {
    const lay = layout;
    const ctx = canvas?.getContext("2d");
    if (!lay || !ctx || !canvas || cur.length === 0) return false;
    const dpr = window.devicePixelRatio || 1;
    const t = reducedMotion() ? 1 : clamp01((now - startAt) / duration);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, lay.W, lay.H);
    const mix = LAYER_WINDOWS.map((w) => within(t, w));
    const value = (layer: number, i: number) => {
      const a = prev[layer]?.[i] ?? 0;
      return a + ((cur[layer]?.[i] ?? 0) - a) * mix[layer]!;
    };

    ctx.textBaseline = "alphabetic";
    ctx.textAlign = "left";
    ctx.fillStyle = DIM;
    ctx.font = `600 12px ${SANS}`;
    for (const title of lay.titles) ctx.fillText(title.text, title.x, title.y);
    ctx.font = `500 10px ${SANS}`;
    for (const b of lay.blocks) if (b.label) ctx.fillText(b.label, b.x, b.y - 4);

    for (const b of lay.blocks) {
      const inset = b.cell >= 5 ? 1 : 0.5;
      const size = b.cell - inset;
      const plain = b.layer === 0 && b.offset < LOCAL_SIZE;
      for (let i = 0; i < b.cols * b.rows; i++) {
        const x = b.x + (i % b.cols) * b.cell;
        const y = b.y + Math.floor(i / b.cols) * b.cell;
        ctx.fillStyle = CELL;
        ctx.fillRect(x, y, size, size);
        const v = value(b.layer, b.offset + i);
        if (v === 0) continue;
        ctx.fillStyle = `rgba(${plain ? INK : v > 0 ? POS : NEG},${Math.min(1, Math.abs(v))})`;
        ctx.fillRect(x, y, size, size);
      }
    }

    // the strongest connections, pulsing inputs → action
    links.forEach((stageLinks, s) => {
      const p = within(t, EDGE_WINDOWS[s]!);
      if (p <= 0 || stageLinks.length === 0) return;
      const peak = Math.max(...stageLinks.map((l) => Math.abs(l.value))) || 1;
      for (const link of stageLinks) {
        const strength = Math.abs(link.value) / peak;
        const [x1, y1] = centre(lay, s, link.from);
        const [x2, y2] = centre(lay, s + 1, link.to);
        const c1: [number, number] = lay.vertical ? [x1, (y1 + y2) / 2] : [(x1 + x2) / 2, y1];
        const c2: [number, number] = lay.vertical ? [x2, (y1 + y2) / 2] : [(x1 + x2) / 2, y2];
        const rgb = link.value > 0 ? POS : NEG;
        ctx.strokeStyle = `rgba(${rgb},${(0.14 + 0.6 * strength) * Math.min(1, p * 1.5)})`;
        ctx.lineWidth = 0.75 + 1.75 * strength;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.bezierCurveTo(c1[0], c1[1], c2[0], c2[1], x2, y2);
        ctx.stroke();
        if (p < 1) {
          const q = 1 - p;
          const bx = q * q * q * x1 + 3 * q * q * p * c1[0] + 3 * q * p * p * c2[0] + p * p * p * x2;
          const by = q * q * q * y1 + 3 * q * q * p * c1[1] + 3 * q * p * p * c2[1] + p * p * p * y2;
          ctx.fillStyle = `rgb(${rgb})`;
          ctx.beginPath();
          ctx.arc(bx, by, 1.5 + 1.5 * strength, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    });

    // ring the cells on the traced path once the pulse has reached them
    const ring = (layer: number, index: number, colour: string, width: number) => {
      const b = blockOf(lay, layer, index);
      if (!b) return;
      const i = index - b.offset;
      ctx.strokeStyle = colour;
      ctx.lineWidth = width;
      ctx.strokeRect(b.x + (i % b.cols) * b.cell - 0.5, b.y + Math.floor(i / b.cols) * b.cell - 0.5, b.cell, b.cell);
    };
    links.forEach((stageLinks, s) => {
      if (within(t, EDGE_WINDOWS[s]!) <= 0) return;
      for (const i of new Set(stageLinks.map((l) => l.from))) ring(s, i, `rgba(${INK},0.85)`, 1);
    });
    if (focus && focus.layer < 3) ring(focus.layer, focus.index, YOU, 2);

    const settled = mix[3]! >= 0.5;
    const chosen = settled ? curBest : prevBest;
    lay.nodes.forEach((n, k) => {
      const prob = (prevProbs[k] ?? 0) + ((curProbs[k] ?? 0) - (prevProbs[k] ?? 0)) * mix[3]!;
      ctx.fillStyle = CELL;
      ctx.beginPath();
      ctx.arc(n.x, n.y, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = `rgba(${INK},${prob})`;
      ctx.fill();
      if (k === chosen) {
        ctx.strokeStyle = `rgb(${INK})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      if (k === target || (focus?.layer === 3 && focus.index === k)) {
        ctx.strokeStyle = YOU;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(n.x, n.y, 12, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.fillStyle = k === chosen ? `rgb(${INK})` : DIM;
      ctx.font = `${k === chosen ? 700 : 500} 13px ${SANS}`;
      const pct = `${Math.round(prob * 100)}%`;
      if (lay.vertical) {
        ctx.textAlign = "center";
        ctx.fillText(MOVES[k]!, n.x, n.y + 28);
        ctx.fillText(pct, n.x, n.y + 44);
      } else {
        ctx.textAlign = "left";
        ctx.fillText(MOVES[k]!, n.x + 20, n.y + 4.5);
        ctx.textAlign = "right";
        ctx.fillText(pct, n.hit[0] + n.hit[2], n.y + 4.5);
      }
    });
    return t < 1;
  }

  function kick() {
    if (raf) return;
    raf = requestAnimationFrame(function frame(now) {
      raf = draw(now) && open ? requestAnimationFrame(frame) : 0;
    });
  }

  function point(event: MouseEvent): Focus | null {
    if (!layout || !canvas) return null;
    const box = canvas.getBoundingClientRect();
    return hitTest(layout, event.clientX - box.left, event.clientY - box.top);
  }

  function onmove(event: PointerEvent) {
    const hit = point(event);
    if (hit && (hit.layer !== focus?.layer || hit.index !== focus?.index)) focus = hit;
  }

  function onpick(event: MouseEvent) {
    const hit = point(event);
    if (!hit) return;
    focus = hit;
    if (hit.layer === 3) pinned = pinned === hit.index ? null : hit.index;
  }

  $effect(() => {
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
  });

  $effect(() => {
    if (!open || !stage) return;
    const fit = () => {
      const W = Math.floor(stage!.clientWidth);
      if (!canvas || W < 200 || W === layout?.W) return;
      const next = computeLayout(W);
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(next.W * dpr);
      canvas.height = Math.round(next.H * dpr);
      canvas.style.height = `${next.H}px`;
      layout = next;
    };
    const observer = new ResizeObserver(fit);
    observer.observe(stage);
    fit();
    return () => observer.disconnect();
  });

  // a new step, or a different action to trace: replay the pulse
  $effect(() => {
    void links;
    if (!open || acts.length === 0) return;
    if (acts !== cur) {
      prev = cur.length ? cur : acts;
      prevProbs = curProbs.length ? curProbs : probs;
      prevBest = cur.length ? curBest : best;
      cur = acts;
      curProbs = probs;
      curBest = best;
    } else {
      prev = cur;
      prevProbs = curProbs;
      prevBest = curBest;
    }
    startAt = performance.now();
    duration = untrack(() => (running ? Math.min(900, tickMs * 0.85) : 900));
    kick();
  });

  $effect(() => {
    void focus;
    void layout;
    if (open) kick();
  });

  let detail = $derived.by(() => {
    if (!focus || acts.length === 0) return null;
    const { layer, index } = focus;
    const v = acts[layer]?.[index] ?? 0;
    if (layer === 0 && index < LOCAL_SIZE) {
      const row = Math.floor((index % PLANE) / VIEW) - (VIEW - 1) / 2;
      const col = (index % VIEW) - (VIEW - 1) / 2;
      const where =
        row === 0 && col === 0
          ? "Its own cell"
          : [row ? `${Math.abs(row)} ${row < 0 ? "up" : "down"}` : "", col ? `${Math.abs(col)} ${col < 0 ? "left" : "right"}` : ""]
              .filter(Boolean)
              .join(", ");
      return { title: `${PLANE_NAMES[Math.floor(index / PLANE)]} plane`, body: `${where}. Value ${v.toFixed(2)}.` };
    }
    if (layer === 0) return { title: "State value", body: `${STATE_NAMES[index - LOCAL_SIZE]}. Value ${v.toFixed(2)}.` };
    if (layer === 3) {
      return { title: MOVES[index]!, body: `Score ${v.toFixed(2)}, which comes to ${Math.round((probs[index] ?? 0) * 100)}% after comparing all six.` };
    }
    const adds = layer === 2 && net ? ` Right now it adds ${signed(net.weightsInto(2, target)[index]! * v)} to the score for ${MOVES[target]}.` : "";
    return { title: `Layer ${layer}, neuron ${index + 1}`, body: `Output ${signed(v)} on a scale of −1 to +1.${adds}` };
  });

  // a layer-1 neuron's incoming weights, laid out like the inputs
  $effect(() => {
    if (!wmap || !net || focus?.layer !== 1) return;
    const w = net.weightsInto(0, focus.index);
    let peak = 0;
    for (const x of w) peak = Math.max(peak, Math.abs(x));
    const dpr = window.devicePixelRatio || 1;
    const cell = 5;
    const gap = 6;
    const side = cell * VIEW;
    const width = 3 * side + 2 * gap;
    const stateCell = Math.floor(width / 12);
    const height = 3 * (side + gap) + 2 * stateCell;
    wmap.width = width * dpr;
    wmap.height = height * dpr;
    wmap.style.width = `${width}px`;
    wmap.style.height = `${height}px`;
    const ctx = wmap.getContext("2d")!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const paint = (x: number, y: number, size: number, v: number) => {
      ctx.fillStyle = CELL;
      ctx.fillRect(x, y, size - 1, size - 1);
      ctx.fillStyle = `rgba(${v > 0 ? POS : NEG},${Math.min(1, Math.abs(v) / (peak || 1))})`;
      ctx.fillRect(x, y, size - 1, size - 1);
    };
    for (let i = 0; i < LOCAL_SIZE; i++) {
      const p = Math.floor(i / PLANE);
      const at = i % PLANE;
      paint((p % 3) * (side + gap) + (at % VIEW) * cell, Math.floor(p / 3) * (side + gap) + Math.floor(at / VIEW) * cell, cell, w[i]!);
    }
    for (let i = 0; i < w.length - LOCAL_SIZE; i++) {
      paint((i % 12) * stateCell, 3 * (side + gap) + Math.floor(i / 12) * stateCell, stateCell, w[LOCAL_SIZE + i]!);
    }
  });
</script>

<dialog bind:this={dialog} onclose={() => (open = false)} aria-labelledby="net-title">
  {#if open}
    <header>
      <h2 id="net-title">Inside the network</h2>
      <button class="btn btn-quiet close" type="button" onclick={() => (open = false)}>Close</button>
    </header>
    <div class="body">
      <aside>
        <Board skins={["two_fuse_hard", "heuristic"]} {engine} {tick} {tickMs} viewFor={0} label="The match Two-Fuse is playing" />
        <div class="controls">
          <button class="btn" type="button" onclick={ontoggle}>{running ? "Pause" : "Play"}</button>
          <button class="btn btn-quiet" type="button" onclick={onstep} disabled={running}>One step</button>
        </div>
        <div class="row">
          <span class="key" id="net-speed">Steps a second</span>
          <div class="chips" role="radiogroup" aria-labelledby="net-speed">
            {#each SPEEDS as s (s)}
              <button type="button" role="radio" aria-checked={speed === s} onclick={() => (speed = s)}>{s}</button>
            {/each}
          </div>
        </div>
        <div class="row">
          <span class="key" id="net-trace">Trace back from</span>
          <div class="chips" role="radiogroup" aria-labelledby="net-trace">
            <button type="button" role="radio" aria-checked={pinned === null} onclick={() => (pinned = null)}>Its choice</button>
            {#each MOVES as move, k (move)}
              <button type="button" role="radio" aria-checked={pinned === k} onclick={() => (pinned = k)}>{move}</button>
            {/each}
          </div>
        </div>
        <div class="detail">
          {#if detail}
            <p class="head">{detail.title}</p>
            <p>{detail.body}</p>
            {#if focus?.layer === 1}
              <canvas bind:this={wmap} aria-hidden="true"></canvas>
              <p class="faint">Its incoming weights, laid out like the inputs: orange inputs raise this neuron, blue ones lower it.</p>
            {/if}
          {:else}
            <p class="faint">Point at or tap any cell to see what it is. Tap an action to trace that one instead.</p>
          {/if}
        </div>
      </aside>
      <div class="main">
        <div class="stage panel" bind:this={stage}>
          <canvas
            bind:this={canvas}
            role="img"
            aria-label={`The network at step ${engine.steps}: inputs on one side, two layers of 256 neurons, and six actions. It picks ${MOVES[best]}.`}
            onpointermove={onmove}
            onclick={onpick}
          ></canvas>
        </div>
        <p class="summary">
          Step {engine.steps}: Two-Fuse picks <strong>{MOVES[best]}</strong> ({Math.round((probs[best] ?? 0) * 100)}%).
          {#if links.length}
            Of the eight layer-2 neurons that matter most for {MOVES[target]}, {push.up} push for it and {push.down} against.
          {/if}
        </p>
        <ul class="legend">
          <li><i class="pos"></i>positive value, or a connection pushing the next cell up</li>
          <li><i class="neg"></i>negative value, or a connection pushing it down</li>
          <li><i class="ink"></i>something present in the 9×9 view</li>
          <li><i class="ring"></i>on the traced path</li>
        </ul>
        <p class="faint caveat">
          The network has about 260,000 connections. The lines are only the strongest few, found by walking back from
          one action: each is a weight times the value it carries. They show what mattered most this step, not a
          complete reason, and a single neuron rarely stands for one idea.
        </p>
      </div>
    </div>
  {/if}
</dialog>

<style>
  dialog {
    width: min(1320px, calc(100vw - 24px));
    max-width: none;
    height: calc(100dvh - 24px);
    max-height: none;
    padding: 0;
    border: 3px solid var(--edge);
    border-radius: 4px;
    background: var(--bg);
    color: var(--text);
    overscroll-behavior: contain;
  }
  dialog::backdrop {
    background: rgb(8 8 12 / 0.82);
  }
  header {
    position: sticky;
    top: 0;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 16px;
    background: var(--bg);
    border-bottom: 1px solid var(--line);
  }
  h2 {
    margin: 0;
    font-size: 1.15rem;
  }
  .close {
    padding: 0.5em 0.9em;
    font-size: 0.85rem;
  }
  .body {
    display: grid;
    grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
    gap: 16px;
    padding: 16px;
    align-items: start;
  }
  aside,
  .main {
    display: grid;
    gap: 12px;
    min-width: 0;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .controls .btn {
    padding: 0.55em 0.9em;
    font-size: 0.85rem;
  }
  .row {
    display: grid;
    gap: 6px;
  }
  .key {
    font-size: 0.82rem;
    color: var(--text-dim);
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chips button {
    border: 2px solid var(--edge);
    border-radius: 3px;
    background: var(--panel-2);
    color: var(--text);
    padding: 5px 9px 6px;
    font-family: var(--pixel);
    font-size: 0.72rem;
    cursor: pointer;
    box-shadow:
      inset 0 2px 0 var(--bevel-light),
      inset 0 -3px 0 var(--bevel-dark);
  }
  .chips button[aria-checked="true"] {
    background: var(--you);
    color: var(--bg-deep);
  }
  .detail {
    border-top: 1px solid var(--line);
    padding-top: 12px;
    display: grid;
    gap: 6px;
    font-size: 0.9rem;
    min-height: 7em;
    align-content: start;
  }
  .detail p,
  .summary,
  .caveat {
    margin: 0;
  }
  .head {
    font-weight: 700;
  }
  .faint {
    color: var(--text-dim);
    font-size: 0.86rem;
  }
  .stage {
    padding: 0;
    overflow: hidden;
  }
  .stage canvas {
    display: block;
    width: 100%;
    cursor: crosshair;
    touch-action: pan-y;
  }
  .legend {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px 18px;
    font-size: 0.84rem;
    color: var(--text-dim);
  }
  .legend li {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .legend i {
    width: 12px;
    height: 12px;
    border-radius: 1px;
    flex: none;
  }
  .pos {
    background: var(--fuse);
  }
  .neg {
    background: #5aa9ff;
  }
  .ink {
    background: var(--text);
  }
  .ring {
    background: var(--panel-2);
    outline: 1px solid var(--text);
  }
  .caveat {
    max-width: var(--measure);
  }
  @media (max-width: 860px) {
    .body {
      grid-template-columns: 1fr;
    }
    aside :global(canvas:first-child) {
      max-width: 320px;
    }
  }
</style>
