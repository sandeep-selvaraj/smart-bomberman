<script lang="ts">
  /**
   * Your line on the Elo scale, pinned beside Board 1: the agents' fixed
   * ratings with your own row ruled in among them. When a result is recorded
   * your row is rewritten with the new rating.
   */
  import { SIGNATURE } from "../art/sprites";
  import { AGENTS, characterOf } from "../lib/agents";

  interface Props {
    rating: number;
    handle: string | null;
    change: number | null;
  }

  let { rating, handle, change }: Props = $props();

  let rows = $derived(
    [
      ...AGENTS.map((a) => ({ id: a.id as string, name: a.name, elo: a.elo, you: false, color: SIGNATURE[characterOf(a.id)] })),
      { id: "you", name: handle ?? "You", elo: rating, you: true, color: SIGNATURE.you },
    ].sort((a, b) => b.elo - a.elo),
  );
  const signed = (n: number): string => (n > 0 ? `+${n}` : `−${-n}`);
</script>

<section class="standings panel" aria-labelledby="standings-mini">
  <table>
    <caption id="standings-mini">Where you stand</caption>
    <thead>
      <tr><th scope="col">Name</th><th scope="col" class="n">Elo</th></tr>
    </thead>
    <tbody>
      {#each rows as row (row.id)}
        <tr class:you={row.you} style:color={row.color}>
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
    font-family: var(--pixel);
    font-weight: 700;
    font-size: 1.15rem;
    padding-bottom: 8px;
  }
  th,
  td {
    padding: 6px 4px;
    border-bottom: 1px solid var(--line);
    text-align: left;
    font-weight: 500;
  }
  thead th {
    font-size: 0.78rem;
    font-weight: 650;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    border-bottom: 3px solid var(--edge);
  }
  tbody th,
  tbody td {
    color: inherit;
  }
  .n {
    text-align: right;
  }
  .you th,
  .you td {
    font-weight: 780;
    background: var(--panel-2);
  }
  .change {
    margin-right: 10px;
    font-weight: 700;
    animation: written 600ms var(--ease-out);
  }
  .change.down {
    color: var(--danger);
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
