<script lang="ts">
  /**
   * Choose your opponent: a character-select roster climbing from the
   * lowest-rated agent to Two-Fuse on hard. New players start at the bottom;
   * one match opens the whole roster. Locked opponents show their own character, dimmed.
   */
  import { SIGNATURE } from "../art/sprites";
  import type { AgentId } from "../engine/match";
  import { AGENTS, characterOf, level, shortName, type Agent } from "../lib/agents";
  import Sprite from "./Sprite.svelte";

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

<section class="roster panel" aria-labelledby="roster-title">
  <header>
    <h2 id="roster-title">Choose your opponent</h2>
    <p>{freeRoster ? "Climb in order, or pick anyone." : "Start at the bottom. One match opens the whole roster."}</p>
  </header>
  <ol>
    {#each AGENTS as agent (agent.id)}
      {@const isOpen = open(agent)}
      <li>
        <button
          type="button"
          class:current={agent.id === current}
          class:locked={!isOpen}
          disabled={!isOpen || disabled}
          aria-pressed={agent.id === current}
          onclick={() => onpick(agent.id)}
        >
          <Sprite character={characterOf(agent.id)} size={64} dim={!isOpen} animate={agent.id === current} />
          <span class="name" style:color={isOpen ? SIGNATURE[characterOf(agent.id)] : undefined}>
            {shortName(agent.id)}{#if level(agent.id)}<small>{level(agent.id)}</small>{/if}
          </span>
          <span class="elo num">{agent.elo}</span>
          <span class="status" class:beaten={beaten.includes(agent.id)} class:next={agent.id === next}>{status(agent)}</span>
          <span class="about">{agent.about}</span>
        </button>
      </li>
    {/each}
  </ol>
</section>

<style>
  .roster {
    padding: 18px 18px 20px;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 4px 18px;
    margin-bottom: 14px;
  }
  h2 {
    font-size: 1.3rem;
  }
  header p {
    color: var(--text-dim);
    font-size: 0.95rem;
  }
  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
  }
  button {
    width: 100%;
    height: 100%;
    display: grid;
    justify-items: center;
    align-content: start;
    gap: 4px;
    padding: 12px 8px 12px;
    border: 3px solid var(--edge);
    border-radius: 4px;
    background: var(--panel-2);
    color: var(--text);
    text-align: center;
    cursor: pointer;
    box-shadow:
      inset 0 2px 0 var(--bevel-light),
      inset 0 -3px 0 var(--bevel-dark);
    transition: transform 140ms var(--ease-out);
  }
  button:hover:not(:disabled) {
    transform: translateY(-2px);
  }
  button.current {
    border-color: var(--you);
    background: #3a3a2c;
  }
  button:disabled {
    cursor: default;
  }
  .name {
    margin-top: 6px;
    font-family: var(--pixel);
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.1;
    display: grid;
  }
  .name small {
    font-size: 0.72rem;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .locked .name {
    color: var(--text-faint);
  }
  .elo {
    font-family: var(--pixel);
    font-size: 0.9rem;
  }
  .status {
    font-family: var(--pixel);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-faint);
  }
  .status.next {
    color: var(--you);
  }
  .status.beaten {
    color: var(--text);
  }
  .about {
    font-size: 0.8rem;
    color: var(--text-dim);
    line-height: 1.35;
    margin-top: 4px;
  }
  .locked .about {
    color: var(--text-faint);
  }
  @media (max-width: 760px) {
    ol {
      grid-template-columns: 1fr;
    }
    button {
      grid-template-columns: auto 1fr auto;
      grid-template-areas:
        "art name elo"
        "art about status";
      justify-items: start;
      text-align: left;
      column-gap: 12px;
    }
    button > :global(canvas) {
      grid-area: art;
      align-self: center;
    }
    .name {
      grid-area: name;
      margin: 0;
    }
    .elo {
      grid-area: elo;
    }
    .status {
      grid-area: status;
    }
    .about {
      grid-area: about;
      margin: 0;
    }
  }
</style>
