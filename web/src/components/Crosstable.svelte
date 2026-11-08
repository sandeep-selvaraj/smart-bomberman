<script lang="ts">
  /**
   * The crosstable: players and agents on one Elo scale. Player rows show
   * their verified record against each agent; agent rows show their measured
   * score against each other (200 games per pair). Agents are fixed anchors,
   * so they carry no rank of their own.
   */
  import { onMount } from "svelte";
  import type { AgentId } from "../engine/match";
  import { SIGNATURE } from "../art/sprites";
  import { AGENTS, characterOf, RATING_GAMES, RATING_RECORDS } from "../lib/agents";
  import { fetchLeaderboard, type Leaderboard, type PublicPlayer } from "../lib/api";
  import { loadProfile } from "../lib/profile";

  interface Props {
    compact?: boolean;
  }

  let { compact = false }: Props = $props();

  const PAGE = compact ? 10 : 50;
  const SHORT: Record<AgentId, string> = {
    camper: "Camper",
    wanderer: "Wanderer",
    heuristic: "Heuristic",
    two_fuse_normal: "Two-Fuse n.",
    two_fuse_hard: "Two-Fuse h.",
  };

  type Row =
    | { kind: "player"; player: PublicPlayer & { rank: number | null }; me: boolean }
    | { kind: "agent"; id: AgentId; name: string; elo: number };

  let board = $state<Leaderboard | null>(null);
  let players = $state<Array<PublicPlayer & { rank: number }>>([]);
  let status = $state<"loading" | "ready" | "offline">("loading");
  let myHandle = $state<string | null>(null);
  let loadingMore = $state(false);

  /** An agent's wins, draws and losses over all its rating games. */
  function agentRecord(id: AgentId): string {
    let w = 0;
    let d = 0;
    let l = 0;
    for (const r of RATING_RECORDS) {
      if (r.a !== id && r.b !== id) continue;
      const mine = r.a === id;
      w += Math.round((mine ? r.win_rate : r.loss_rate) * r.games);
      l += Math.round((mine ? r.loss_rate : r.win_rate) * r.games);
      d += Math.round(r.draw_rate * r.games);
    }
    return `${w}\u2013${d}\u2013${l}`;
  }

  /** An agent's score against another, as a share of points over the measured games. */
  function agentShare(a: AgentId, b: AgentId): number | null {
    const direct = RATING_RECORDS.find((r) => r.a === a && r.b === b);
    const reverse = RATING_RECORDS.find((r) => r.a === b && r.b === a);
    if (direct) return direct.win_rate + direct.draw_rate / 2;
    if (reverse) return reverse.loss_rate + reverse.draw_rate / 2;
    return null;
  }

  /** The opponent each agent scores best against: its strongest matchup, highlighted in its row. */
  const BEST = Object.fromEntries(
    AGENTS.map((row) => {
      let best: AgentId | null = null;
      for (const other of AGENTS) {
        if (other.id === row.id) continue;
        if (best === null || (agentShare(row.id, other.id) ?? 0) > (agentShare(row.id, best) ?? 0)) best = other.id;
      }
      return [row.id, best];
    }),
  ) as Record<AgentId, AgentId>;

  let rows = $derived.by((): Row[] => {
    const list: Row[] = players.map((p) => ({
      kind: "player",
      player: p,
      me: !!myHandle && p.handle.toLowerCase() === myHandle.toLowerCase(),
    }));
    const more = board ? board.offset + players.length < board.total : false;
    const floor = more && players.length ? players[players.length - 1]!.rating : -Infinity;
    for (const agent of AGENTS) {
      if (agent.elo >= floor) list.push({ kind: "agent", id: agent.id, name: agent.name, elo: agent.elo });
    }
    const rating = (row: Row) => (row.kind === "agent" ? row.elo : row.player.rating);
    return list.sort((a, b) => rating(b) - rating(a));
  });

  let pinned = $derived(
    board?.me && !players.some((p) => p.handle.toLowerCase() === board!.me!.handle.toLowerCase()) ? board.me : null,
  );

  async function load(offset = 0) {
    try {
      const page = await fetchLeaderboard(offset, PAGE, myHandle);
      board = page;
      players = offset === 0 ? page.players : [...players, ...page.players];
      status = "ready";
    } catch {
      status = "offline";
    }
  }

  async function more() {
    loadingMore = true;
    await load(players.length);
    loadingMore = false;
  }

  const record = (p: PublicPlayer, id: AgentId): string => {
    const r = p.vs[id];
    return r ? `${r[0]}–${r[1]}–${r[2]}` : "";
  };

  onMount(() => {
    myHandle = loadProfile().handle;
    void load();
  });
</script>

<div class="crosstable panel">
  <p class="swipe">Scroll sideways for each agent</p>
  <div class="scroll" role="region" aria-label="Crosstable" tabindex="0">
    <table>
      <caption class="visually-hidden">Players and agents ranked by Elo rating</caption>
      <thead>
        <tr class="group">
          <th scope="col" colspan="4"><span class="visually-hidden">Player</span></th>
          <th scope="colgroup" colspan={AGENTS.length} class="against">Against each agent</th>
        </tr>
        <tr>
          <th scope="col" class="who">Name</th>
          <th scope="col" class="n">Elo</th>
          <th scope="col" class="n">Games</th>
          <th scope="col" class="n wdl">W–D–L</th>
          {#each AGENTS as agent (agent.id)}
            <th scope="col" class="n vs" title={agent.name}>{SHORT[agent.id]}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each rows as row (row.kind === "agent" ? row.id : row.player.handle)}
          {#if row.kind === "agent"}
            <tr class="agent">
              <th scope="row" class="who" style:color={SIGNATURE[characterOf(row.id)]}>{row.name}<span class="tag">agent</span></th>
              <td class="n strong">{row.elo}</td>
              <td class="n">{RATING_GAMES * (AGENTS.length - 1)}</td>
              <td class="n wdl">{agentRecord(row.id)}</td>
              {#each AGENTS as other (other.id)}
                {#if other.id === row.id}
                  <td class="n vs self"></td>
                {:else}
                  {@const share = agentShare(row.id, other.id) ?? 0}
                  <td
                    class="n vs score"
                    class:best={BEST[row.id] === other.id}
                    style:--share={share.toFixed(3)}
                    style:--tint={SIGNATURE[characterOf(row.id)]}
                  >
                    {Math.round(share * 100)}%{#if BEST[row.id] === other.id}<span class="visually-hidden">, best matchup</span>{/if}
                  </td>
                {/if}
              {/each}
            </tr>
          {:else}
            <tr class:me={row.me}>
              <th scope="row" class="who">{row.player.handle}{#if row.me}<span class="tag">you</span>{/if}</th>
              <td class="n strong">{row.player.rating}</td>
              <td class="n">{row.player.games}</td>
              <td class="n wdl">{row.player.wins}–{row.player.draws}–{row.player.losses}</td>
              {#each AGENTS as agent (agent.id)}
                <td class="n vs">{record(row.player, agent.id)}</td>
              {/each}
            </tr>
          {/if}
        {/each}
        {#if pinned}
          <tr class="me pinned">
            <th scope="row" class="who">{pinned.handle}<span class="tag">you · rank {pinned.rank ?? "–"}</span></th>
            <td class="n strong">{pinned.rating}</td>
            <td class="n">{pinned.games}</td>
            <td class="n wdl">{pinned.wins}–{pinned.draws}–{pinned.losses}</td>
            {#each AGENTS as agent (agent.id)}
              <td class="n vs">{record(pinned, agent.id)}</td>
            {/each}
          </tr>
        {/if}
      </tbody>
    </table>
  </div>

  <p class="legend-note">
    A player's cell is their wins–draws–losses against that agent, every game verified by replay. An agent's cell is its
    score against that agent (a win counts 1, a draw ½) over {RATING_GAMES} games per pair, a separate measurement from
    the win rates on the training page. The bar under each score is drawn in that agent's colour, and its best matchup
    is lit up.
  </p>
  <div class="foot">
    {#if status === "loading"}
      <p>Fetching players…</p>
    {:else if status === "offline"}
      <p>The player list could not be fetched. The agents' ratings above are measured offline and always shown.</p>
    {:else if board && board.total === 0}
      <p>No players yet. Your first recorded match puts you on this table.</p>
    {:else if board}
      <p>
        {board.total}
        {board.total === 1 ? "player" : "players"}, ranked by Elo.
        {#if !board.persistent}<strong>Local development: results are kept in memory.</strong>{/if}
      </p>
    {/if}
    {#if compact}
      <a class="all" href="/crosstable">Full crosstable</a>
    {:else if board && players.length < board.total}
      <button class="btn btn-quiet" type="button" onclick={more} disabled={loadingMore}>
        {loadingMore ? "Loading…" : `Show ${Math.min(PAGE, board.total - players.length)} more`}
      </button>
    {/if}
  </div>
</div>

<style>
  .crosstable {
    padding: 8px 0 0;
  }
  .scroll {
    overflow-x: auto;
    scrollbar-color: var(--line) var(--panel);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.98rem;
  }
  th,
  td {
    padding: 9px 12px;
    border-bottom: 1px solid var(--line);
    text-align: left;
    white-space: nowrap;
  }
  thead th {
    font-size: 0.8rem;
    font-weight: 650;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    border-bottom: 3px solid var(--edge);
  }
  .n {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-stretch: 80%;
  }
  .group th {
    border-bottom: 0;
    padding-bottom: 0;
  }
  .against {
    text-align: center;
    border-left: 1px solid var(--line);
  }
  .swipe {
    display: none;
    padding: 4px 16px 8px;
    font-size: 0.85rem;
    color: var(--text-dim);
  }
  @media (max-width: 760px) {
    .swipe {
      display: block;
    }
    .scroll {
      mask-image: linear-gradient(to right, #000 85%, transparent);
    }
  }
  .who {
    position: sticky;
    left: 0;
    background: var(--panel);
    font-weight: 650;
    min-width: 12ch;
  }
  .strong {
    font-weight: 780;
  }
  .vs {
    border-left: 1px solid var(--line);
    min-width: 6.5ch;
  }
  /* a score bar along the bottom of each agent cell, in that agent's colour; its best matchup is lit */
  .score {
    position: relative;
  }
  .score::after {
    content: "";
    position: absolute;
    left: 10px;
    bottom: 5px;
    height: 4px;
    width: calc((100% - 20px) * var(--share));
    background: var(--tint);
    opacity: 0.4;
    border-radius: 0 2px 2px 0;
  }
  .score.best {
    color: var(--tint);
    font-weight: 800;
  }
  .score.best::after {
    opacity: 1;
  }
  .self {
    background: repeating-linear-gradient(135deg, var(--line) 0 1px, transparent 1px 6px);
  }
  .agent {
    color: var(--text-dim);
  }
  .me,
  .me .who {
    background: var(--panel-2);
  }
  .pinned td,
  .pinned th {
    border-top: 3px solid var(--edge);
  }
  .me .who {
    color: var(--you);
  }
  .tag {
    margin-left: 8px;
    font-size: 0.72rem;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
  }

  .legend-note {
    padding: 12px 16px 0;
    max-width: 90ch;
    color: var(--text-dim);
    font-size: 0.88rem;
  }
  .foot {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px 24px;
    padding: 14px 16px 16px;
    color: var(--text-dim);
    font-size: 0.92rem;
  }
  .foot p {
    max-width: 80ch;
  }
  .all {
    font-weight: 700;
    color: var(--text);
  }
</style>
