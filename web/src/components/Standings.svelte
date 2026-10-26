<script lang="ts">
  /**
   * Your line on the Elo scale, pinned beside Board 1: the agents' fixed
   * ratings with your own row ruled in among them. When a result is recorded
   * your row is rewritten with the new rating.
   */
  import { AGENTS } from "../lib/agents";

  interface Props {
    rating: number;
    handle: string | null;
    change: number | null;
  }

  let { rating, handle, change }: Props = $props();

  let rows = $derived(
    [
      ...AGENTS.map((a) => ({ id: a.id as string, name: a.name, elo: a.elo, you: false })),
      { id: "you", name: handle ?? "You", elo: rating, you: true },
    ].sort((a, b) => b.elo - a.elo),
  );
  const signed = (n: number): string => (n > 0 ? `+${n}` : `−${-n}`);
</script>

<section class="standings sheet" aria-labelledby="standings-mini">
  <table>
    <caption id="standings-mini">Where you stand</caption>
    <thead>
      <tr><th scope="col">Name</th><th scope="col" class="n">Elo</th></tr>
    </thead>
    <tbody>
      {#each rows as row (row.id)}
        <tr class:you={row.you}>
          <th scope="row">{row.name}</th>
          <td class="n num">
            {#if row.you && change}<span class="change" class:down={change < 0}>{signed(change)}</span>{/if}
            {row.elo}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
  <a href="/crosstable">Full crosstable</a>
</section>

<style>
  .standings {
    padding: 16px 22px 14px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  caption {
    text-align: left;
    font-weight: 760;
    font-stretch: 78%;
    font-size: 1.35rem;
    padding-bottom: 8px;
  }
  th,
  td {
    padding: 6px 4px;
    border-bottom: 1px solid var(--rule);
    text-align: left;
    font-weight: 500;
  }
  thead th {
    font-size: 0.78rem;
    font-weight: 650;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-soft);
    border-bottom: 2px solid var(--ink);
  }
  tbody th,
  tbody td {
    color: var(--agent);
  }
  .n {
    text-align: right;
  }
  .you th,
  .you td {
    color: var(--ink);
    font-weight: 780;
    background: var(--sheet-alt);
  }
  .change {
    margin-right: 10px;
    font-weight: 700;
    animation: written 600ms var(--ease-out);
  }
  .change.down {
    color: var(--flag-ink);
  }
  @keyframes written {
    from {
      transform: translateY(-4px);
    }
  }
  a {
    display: inline-block;
    margin-top: 10px;
    font-weight: 650;
    font-size: 0.92rem;
  }
</style>
