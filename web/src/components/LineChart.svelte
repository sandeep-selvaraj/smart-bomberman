<script lang="ts">
  /**
   * A small line chart on a game panel: hairline grid, 2px lines, end labels, and a
   * crosshair tooltip. Series are told apart by dash pattern and direct labels,
   * not by colour, because on this site colour only ever means state. The
   * drawing is laid out at its real pixel width, so text never shrinks.
   */
  interface Series {
    id: string;
    label: string;
    color: string;
    dash?: string;
    points: Array<{ x: number; y: number; note?: string }>;
  }

  interface Props {
    series: Series[];
    title: string;
    yMax?: number;
    yTicks?: number[];
    yFormat?: (y: number) => string;
  }

  let {
    series,
    title,
    yMax = 1,
    yTicks = [0, 0.25, 0.5, 0.75, 1],
    yFormat = (y: number) => `${Math.round(y * 100)}%`,
  }: Props = $props();

  /** Training steps as 0.5M, 1M, ... (props from Astro cannot carry functions). */
  const xLabel = (x: number): string => (x === 0 ? "0" : `${(x / 1e6).toFixed(x % 1e6 ? 1 : 0)}M`);
  let width = $state(720);
  const W = $derived(Math.max(300, Math.min(900, width)));
  const H = $derived(W < 520 ? 260 : 320);
  const M = $derived({ top: 16, right: W < 520 ? 98 : 120, bottom: 36, left: 44 });
  const xs = $derived([...new Set(series.flatMap((s) => s.points.map((p) => p.x)))].sort((a, b) => a - b));
  const xMax = $derived(Math.max(...xs));
  const px = (x: number) => M.left + (x / xMax) * (W - M.left - M.right);
  const py = (y: number) => M.top + (1 - y / yMax) * (H - M.top - M.bottom);
  const tickEvery = $derived(Math.ceil(xs.length / Math.max(2, Math.floor((W - M.left - M.right) / 90))));
  let hover = $state<number | null>(null);
  let svg: SVGSVGElement;

  function move(event: PointerEvent) {
    const box = svg.getBoundingClientRect();
    const x = ((event.clientX - box.left) / box.width) * W;
    let best = 0;
    xs.forEach((value, i) => {
      if (Math.abs(px(value) - x) < Math.abs(px(xs[best]!) - x)) best = i;
    });
    hover = best;
  }

  const path = (s: Series) => s.points.map((p, i) => `${i ? "L" : "M"}${px(p.x).toFixed(1)},${py(p.y).toFixed(1)}`).join("");

  /** End labels nudged apart so they never collide. */
  const ends = $derived.by(() => {
    const items = series.map((s) => ({ s, y: py(s.points[s.points.length - 1]!.y) })).sort((a, b) => a.y - b.y);
    for (let i = 1; i < items.length; i++) items[i]!.y = Math.max(items[i]!.y, items[i - 1]!.y + 16);
    return items;
  });
</script>

<figure class="chart">
  <figcaption>{title}</figcaption>
  <ul class="legend">
    {#each series as s (s.id)}
      <li>
        <svg width="28" height="8" aria-hidden="true"
          ><line x1="1" x2="27" y1="4" y2="4" stroke={s.color} stroke-width="2" stroke-dasharray={s.dash ?? ""} /></svg
        >{s.label}
      </li>
    {/each}
  </ul>
  <div class="plot" bind:clientWidth={width}>
    <svg
      bind:this={svg}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={title}
      onpointermove={move}
      onpointerleave={() => (hover = null)}
    >
      {#each yTicks as t (t)}
        <line x1={M.left} x2={W - M.right} y1={py(t)} y2={py(t)} class="grid" />
        <text x={M.left - 8} y={py(t)} class="tick" text-anchor="end" dominant-baseline="middle">{yFormat(t)}</text>
      {/each}
      {#each xs as x, i (x)}
        {#if (i % tickEvery === 0 && xs.length - 1 - i >= tickEvery / 2) || i === xs.length - 1}
          <text x={px(x)} y={H - M.bottom + 20} class="tick" text-anchor="middle">{xLabel(x)}</text>
        {/if}
      {/each}
      {#each series as s (s.id)}
        {@const last = s.points[s.points.length - 1]!}
        <path
          d={path(s)}
          fill="none"
          stroke={s.color}
          stroke-width="2"
          stroke-dasharray={s.dash ?? ""}
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <circle cx={px(last.x)} cy={py(last.y)} r="4.5" fill={s.color} stroke="#2a2a37" stroke-width="2" />
      {/each}
      {#each ends as { s, y } (s.id)}
        <text x={W - M.right + 10} {y} class="end" dominant-baseline="middle">
          {s.label} {yFormat(s.points[s.points.length - 1]!.y)}
        </text>
      {/each}
      {#if hover !== null}
        <line x1={px(xs[hover]!)} x2={px(xs[hover]!)} y1={M.top} y2={H - M.bottom} class="cross" />
        {#each series as s (s.id)}
          {@const p = s.points.find((q) => q.x === xs[hover!])}
          {#if p}
            <circle cx={px(p.x)} cy={py(p.y)} r="5" fill={s.color} stroke="#2a2a37" stroke-width="2" />
          {/if}
        {/each}
      {/if}
    </svg>
    {#if hover !== null}
      <div class="tip" style:left={`${Math.min(Math.max((px(xs[hover]!) / W) * 100, 22), 78)}%`}>
        <strong>{xLabel(xs[hover]!)}</strong>
        {#each series as s (s.id)}
          {@const p = s.points.find((q) => q.x === xs[hover!])}
          {#if p}
            <span>{s.label} {yFormat(p.y)}{p.note ? ` · ${p.note}` : ""}</span>
          {/if}
        {/each}
      </div>
    {/if}
  </div>
  <details>
    <summary>Show the numbers</summary>
    <table>
      <thead>
        <tr><th scope="col">Steps</th>{#each series as s (s.id)}<th scope="col">{s.label}</th>{/each}</tr>
      </thead>
      <tbody>
        {#each xs as x (x)}
          <tr>
            <th scope="row">{xLabel(x)}</th>
            {#each series as s (s.id)}
              {@const p = s.points.find((q) => q.x === x)}
              <td>{p ? yFormat(p.y) : ""}</td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </details>
</figure>

<style>
  .chart {
    margin: 0;
    padding: 20px 22px 16px;
    background: var(--panel);
    color: var(--text);
    
  }
  figcaption {
    font-weight: 700;
    font-size: 1.05rem;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 18px;
    margin: 8px 0 4px;
    padding: 0;
    list-style: none;
    font-size: 0.88rem;
    color: var(--text-dim);
  }
  .legend li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .plot {
    position: relative;
  }
  .plot > svg {
    width: 100%;
    height: auto;
    display: block;
    touch-action: pan-y;
  }
  .grid {
    stroke: #3d3d50;
    stroke-width: 1;
  }
  .tick {
    font-size: 12px;
    fill: var(--text-faint);
    font-variant-numeric: tabular-nums;
  }
  .end {
    font-size: 12.5px;
    fill: var(--text);
    font-weight: 600;
  }
  .cross {
    stroke: var(--line);
    stroke-width: 1;
  }
  .tip {
    position: absolute;
    top: 8px;
    transform: translateX(-50%);
    display: grid;
    gap: 2px;
    padding: 8px 10px;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 3px;
    box-shadow: 0 6px 16px -10px rgb(0 0 0 / 0.4);
    font-size: 0.82rem;
    white-space: nowrap;
    pointer-events: none;
  }
  details {
    margin-top: 8px;
    font-size: 0.88rem;
  }
  summary {
    cursor: pointer;
    color: var(--text-dim);
  }
  table {
    margin-top: 8px;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }
  th,
  td {
    padding: 4px 12px 4px 0;
    text-align: right;
    border-bottom: 1px solid var(--line);
  }
</style>
