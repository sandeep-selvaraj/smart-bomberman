<script lang="ts">
  /**
   * The ladder as a pairing list: agents from the lowest rated to Two-Fuse on
   * hard. New players climb it in order; after one match every opponent is
   * open, like a free roster.
   */
  import type { AgentId } from "../engine/match";
  import { AGENTS, type Agent } from "../lib/agents";

  interface Props {
    beaten: AgentId[];
    played: AgentId[];
    current: AgentId;
    disabled?: boolean;
    onpick: (agent: AgentId) => void;
  }

  let { beaten, played, current, disabled = false, onpick }: Props = $props();

  let next = $derived(AGENTS.find((a) => !beaten.includes(a.id))?.id ?? null);
  let freeRoster = $derived(played.length > 0);

  const open = (agent: Agent): boolean => freeRoster || agent.id === next || beaten.includes(agent.id);
  const status = (agent: Agent): string =>
    beaten.includes(agent.id) ? "Beaten" : agent.id === next ? "Next" : open(agent) ? "Open" : "Locked";
</script>

<section class="ladder sheet" aria-labelledby="ladder-title">
  <h2 id="ladder-title">Your ladder</h2>
  <p class="note">
    {freeRoster ? "Climb in order, or pick any opponent." : "Start at the bottom. One match opens the whole roster."}
  </p>
  <ol>
    {#each AGENTS as agent (agent.id)}
      {@const isOpen = open(agent)}
      <li class:current={agent.id === current} class:locked={!isOpen}>
        <button
          type="button"
          disabled={!isOpen || disabled}
          aria-pressed={agent.id === current}
          onclick={() => onpick(agent.id)}
        >
          <span class="name">{agent.name}</span>
          <span class="about">{agent.about}</span>
          <span class="elo num">{agent.elo}</span>
          <span class="status" class:beaten={beaten.includes(agent.id)}>{status(agent)}</span>
        </button>
      </li>
    {/each}
  </ol>
</section>

<style>
  .ladder {
    padding: 22px 24px 14px;
  }
  h2 {
    font-size: 1.5rem;
  }
  .note {
    margin: 6px 0 12px;
    color: var(--ink-soft);
    font-size: 0.95rem;
  }
  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column-reverse; /* Two-Fuse on hard at the top of the ladder */
  }
  li {
    border-top: 1px solid var(--rule);
  }
  li:last-child {
    border-top: 2px solid var(--ink);
  }
  button {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr auto auto;
    grid-template-areas:
      "name elo status"
      "about about about";
    column-gap: 14px;
    align-items: baseline;
    padding: 10px 6px;
    border: 0;
    background: transparent;
    color: var(--agent);
    text-align: left;
    cursor: pointer;
  }
  button:hover:not(:disabled) {
    background: var(--agent-wash);
  }
  .current button {
    background: var(--agent-wash);
  }
  .current .name::after {
    content: " · selected";
    font-weight: 500;
    font-size: 0.85rem;
  }
  button:disabled {
    cursor: default;
  }
  .locked button {
    color: var(--ink-faint);
  }
  .name {
    grid-area: name;
    font-weight: 720;
    font-stretch: 85%;
    font-size: 1.08rem;
  }
  .about {
    grid-area: about;
    color: var(--ink-soft);
    font-size: 0.86rem;
  }
  .locked .about {
    color: var(--ink-faint);
  }
  .elo {
    grid-area: elo;
    font-weight: 700;
  }
  .status {
    grid-area: status;
    min-width: 4.5em;
    text-align: right;
    color: var(--ink-soft);
    font-size: 0.85rem;
    font-weight: 650;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .status.beaten {
    color: var(--ink);
  }
</style>
