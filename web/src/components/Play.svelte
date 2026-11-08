<script lang="ts">
  /**
   * Board 1: a ranked match against one of the agents.
   *
   * The server issues a signed seed; the browser plays the match from it at
   * 7 ticks a second and records one input per tick. The finished log goes
   * back to the server, which replays it with the same engine and agent and
   * only then moves the rating. Without a server the match is practice.
   */
  import { onMount } from "svelte";
  import { BOMB, DOWN, LEFT, NOOP, RIGHT, UP, type Action, type VersusEngine } from "../engine/engine";
  import { matchSetup, needsNet, newEngine, opponentFor, PLAY_MAPS, type AgentId } from "../engine/match";
  import { loadPolicyNet, type PolicyNet } from "../engine/mlp";
  import type { Policy } from "../engine/policies";
  import { SIGNATURE } from "../art/sprites";
  import { AGENTS, AGENT_BY_ID, characterOf, level, shortName } from "../lib/agents";
  import { ApiError, startMatch, submitMatch } from "../lib/api";
  import { START_RATING, stakes, type Outcome } from "../lib/elo";
  import { handleProblem, HANDLE_MAX } from "../lib/handle";
  import { loadProfile, saveProfile, type Profile } from "../lib/profile";
  import Board from "./Board.svelte";
  import Clock from "./Clock.svelte";
  import Ladder from "./Ladder.svelte";
  import Sprite from "./Sprite.svelte";
  import Standings from "./Standings.svelte";

  const TPS = 7;
  const TICK_MS = 1000 / TPS;
  const KEYS: Record<string, Action> = {
    ArrowUp: UP,
    ArrowDown: DOWN,
    ArrowLeft: LEFT,
    ArrowRight: RIGHT,
    w: UP,
    s: DOWN,
    a: LEFT,
    d: RIGHT,
    x: BOMB,
    " ": BOMB,
  };
  /** How a fighter went down, worded from the human's side of the board. */
  function causeOf(killedBy: string | null, theirs: boolean, them: string): string {
    switch (killedBy) {
      case "opponent_bomb":
        return theirs ? "your bomb" : `${them}'s bomb`;
      case "own_bomb":
        return theirs ? "its own bomb" : "your own bomb";
      case "enemy":
        return "a wandering enemy";
      case "crushed":
        return "the closing arena";
      default:
        return "the board";
    }
  }

  type Phase = "preparing" | "ready" | "loading" | "countdown" | "playing" | "over";
  type Recording = "idle" | "practice" | "needs-handle" | "submitting" | "recorded" | "rejected" | "saved";

  let profile = $state<Profile>({ handle: null, key: "", rating: null, games: 0, beaten: [], played: [], pending: [] });
  let opponent = $state<AgentId>(AGENTS[0]!.id);
  let phase = $state<Phase>("preparing");
  let ticket = $state<string | null>(null);
  let round = $state(1);
  let seed = $state(1);
  let practiceReason = $state<string | null>(null);
  let engine = $state<VersusEngine>(newEngine(1, PLAY_MAPS));
  let tick = $state(0);
  let countdown = $state(0);
  let announcement = $state("");
  let outcome = $state<Outcome | null>(null);
  let cause = $state("");
  let recording = $state<Recording>("idle");
  let recordMessage = $state("");
  let ratingChange = $state<{ before: number; after: number; delta: number; rank: number | null } | null>(null);
  let handleDraft = $state("");
  let handleError = $state<string | null>(null);
  let keyboardless = $state(false);

  let net: PolicyNet | null = null;
  let netLoading: Promise<PolicyNet> | null = null;
  let agent: Policy | null = null;
  let inputs: number[] = [];
  let queue: Action[] = [];
  let held: Action | null = null;
  let frame = 0;
  let lastTick = 0;

  let rating = $derived(profile.rating ?? START_RATING);
  let opp = $derived(AGENT_BY_ID[opponent]);
  let worth = $derived(stakes(rating, opp.elo, profile.games));
  let mapName = $derived(matchSetup(seed, PLAY_MAPS).map.replace("_", " "));
  let ranked = $derived(ticket !== null);
  let busy = $derived(phase === "countdown" || phase === "playing" || phase === "loading");
  /** The engine mutates in place; this snapshot re-reads it on every tick. */
  let view = $derived.by(() => {
    void tick;
    const fuse = (p: number): number | null => engine.bombs.find((b) => b.owner === p)?.timer ?? null;
    return {
      steps: engine.steps,
      alive: [engine.players[0].alive, engine.players[1].alive],
      fuse: [fuse(0), fuse(1)],
      open: engine.closingOrder.length - engine.closed,
      sudden: engine.suddenDeath,
    };
  });

  const signed = (n: number): string => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : "0");
  const nextOnLadder = (): AgentId => AGENTS.find((a) => !profile.beaten.includes(a.id))?.id ?? "two_fuse_hard";

  function persist(change: Partial<Profile>) {
    profile = { ...profile, ...change };
    saveProfile(profile);
  }

  function ensureNet(): Promise<PolicyNet> {
    netLoading ??= loadPolicyNet("/models/two_fuse").then((loaded) => (net = loaded));
    return netLoading;
  }

  async function prepare(agentId: AgentId) {
    cancelAnimationFrame(frame);
    opponent = agentId;
    phase = "preparing";
    outcome = null;
    recording = "idle";
    ratingChange = null;
    recordMessage = "";
    if (needsNet(agentId)) ensureNet().catch(() => {});
    try {
      const issued = await startMatch(agentId);
      ticket = issued.ticket;
      seed = issued.seed;
      practiceReason = null;
    } catch (error) {
      ticket = null;
      seed = crypto.getRandomValues(new Uint32Array(1))[0]!;
      practiceReason =
        error instanceof ApiError && error.code !== "offline"
          ? error.message
          : "The ranking server is unreachable, so this one is practice.";
    }
    engine = newEngine(seed, PLAY_MAPS);
    tick = 0;
    round = profile.games + 1;
    phase = "ready";
  }

  async function start() {
    if (phase !== "ready") return;
    if (needsNet(opponent) && !net) {
      phase = "loading";
      try {
        await ensureNet();
      } catch {
        netLoading = null;
        phase = "ready";
        announcement = "Two-Fuse's network failed to load. Check your connection and try again.";
        return;
      }
    }
    agent = opponentFor(opponent, seed, net);
    engine = newEngine(seed, PLAY_MAPS);
    inputs = [];
    queue = [];
    held = null;
    tick = 0;
    phase = "countdown";
    for (const n of [3, 2, 1]) {
      countdown = n;
      announcement = String(n);
      await new Promise((r) => setTimeout(r, 550));
      if (phase !== "countdown") return;
    }
    countdown = 0;
    phase = "playing";
    announcement = `Go. ${shortName(opponent)} starts in the ${engine.swap ? "top-left" : "bottom-right"} corner.`;
    lastTick = performance.now();
    frame = requestAnimationFrame(loop);
  }

  function loop(now: number) {
    while (phase === "playing" && now - lastTick >= TICK_MS) {
      lastTick += TICK_MS;
      step();
    }
    if (phase === "playing") frame = requestAnimationFrame(loop);
  }

  function step() {
    const mine = queue.shift() ?? held ?? NOOP;
    const theirs = agent!.act(engine, 1);
    const wasSudden = engine.suddenDeath;
    engine.step([mine, theirs]);
    inputs.push(mine);
    tick += 1;
    if (!wasSudden && engine.suddenDeath) announcement = "Sudden death. The arena is closing.";
    if (engine.finished) finish();
  }

  function finish() {
    phase = "over";
    const winner = engine.winner;
    outcome = winner === 0 ? "win" : winner === 1 ? "loss" : "draw";
    const them = shortName(opponent);
    cause =
      outcome === "win"
        ? `${them} fell to ${causeOf(engine.players[1].killedBy, true, them)}.`
        : outcome === "loss"
          ? `You fell to ${causeOf(engine.players[0].killedBy, false, them)}.`
          : "You both went down on the same step.";
    announcement = `${outcome === "win" ? "You won" : outcome === "loss" ? "You lost" : "Draw"}. ${cause}`;
    persist({
      played: profile.played.includes(opponent) ? profile.played : [...profile.played, opponent],
      beaten: outcome === "win" && !profile.beaten.includes(opponent) ? [...profile.beaten, opponent] : profile.beaten,
    });
    if (!ticket) recording = "practice";
    else if (!profile.handle) recording = "needs-handle";
    else void record();
  }

  async function record() {
    if (!ticket || !outcome || !profile.handle || recording === "submitting" || recording === "recorded") return;
    recording = "submitting";
    const before = rating;
    const payload = { ticket, handle: profile.handle, key: profile.key, inputs: [...inputs], claimed: outcome };
    try {
      const result = await submitMatch(payload);
      persist({ rating: result.player.rating, games: result.player.games });
      ratingChange = { before, after: result.player.rating, delta: result.delta, rank: result.rank };
      recording = "recorded";
      recordMessage = result.persistent ? "" : "Local development server: this result lives in memory only.";
    } catch (error) {
      if (error instanceof ApiError && (error.code === "offline" || error.status >= 500)) {
        persist({ pending: [...profile.pending, { ...payload, agent: opponent, playedAt: Date.now() }] });
        recording = "saved";
        recordMessage = "Saved in this browser. It will be checked and recorded next time the server answers.";
      } else {
        recording = "rejected";
        recordMessage = error instanceof Error ? error.message : "The result could not be recorded.";
        if (error instanceof ApiError && error.code === "handle_taken") {
          persist({ handle: null });
          recording = "needs-handle";
          handleError = error.message;
        }
      }
    }
  }

  function claimHandle(event: SubmitEvent) {
    event.preventDefault();
    const problem = handleProblem(handleDraft);
    handleError = problem;
    if (problem) return;
    persist({ handle: handleDraft.trim() });
    void record();
  }

  async function flushPending() {
    if (!profile.handle || !profile.pending.length) return;
    const remaining = [];
    for (const item of profile.pending) {
      try {
        const result = await submitMatch({ ...item, handle: profile.handle, key: profile.key });
        persist({ rating: result.player.rating, games: result.player.games });
      } catch (error) {
        if (error instanceof ApiError && (error.code === "offline" || error.status >= 500)) remaining.push(item);
      }
    }
    persist({ pending: remaining });
  }

  function onKeyDown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
    if (phase === "ready" && event.key === "Enter") {
      event.preventDefault();
      void start();
      return;
    }
    if (phase !== "playing" && phase !== "countdown") return;
    const action = KEYS[event.key.length === 1 ? event.key.toLowerCase() : event.key];
    if (action === undefined) return;
    event.preventDefault();
    if (event.repeat) return;
    if (action === BOMB) queue.push(BOMB);
    else {
      queue.push(action);
      held = action;
    }
  }

  function onKeyUp(event: KeyboardEvent) {
    const action = KEYS[event.key.length === 1 ? event.key.toLowerCase() : event.key];
    if (action !== undefined && action === held) held = null;
  }

  onMount(() => {
    profile = loadProfile();
    keyboardless = window.matchMedia("(pointer: coarse)").matches && window.innerWidth < 900;
    void prepare(nextOnLadder());
    void flushPending();
    return () => cancelAnimationFrame(frame);
  });
</script>

<svelte:window onkeydown={onKeyDown} onkeyup={onKeyUp} />

<div class="hall">
  <section class="arena-col" aria-label="Board 1">
    <Clock
      you={{ name: "You", character: "you", alive: view.alive[0]!, fuse: view.fuse[0]! }}
      them={{ name: shortName(opponent), character: characterOf(opponent), alive: view.alive[1]!, fuse: view.fuse[1]! }}
      steps={view.steps}
      suddenDeathStart={engine.config.suddenDeathStart}
      maxSteps={engine.config.maxSteps}
      openCells={view.open}
      tps={TPS}
    />
    <div class="arena">
      <Board
        {engine}
        {tick}
        tickMs={TICK_MS}
        skins={["you", characterOf(opponent)]}
        label={`Board 1 on ${mapName}: you in the yellow jacket against ${opp.name}.`}
      />
      {#if phase === "countdown"}
        <div class="count" aria-hidden="true">{countdown}</div>
      {/if}
    </div>
    <p class="legend">
      <span><Sprite character="spark" size={22} />Spark: wanders, deadly to both</span>
      <span><i class="tile brick"></i>Brick: one blast</span>
      <span><i class="tile stone"></i>Stone: two blasts</span>
      <span><i class="tile wall"></i>Wall: never breaks</span>
    </p>
    <div class="roster-wrap">
      <Ladder
        beaten={profile.beaten}
        played={profile.played}
        current={opponent}
        disabled={busy}
        onpick={(id) => prepare(id)}
      />
    </div>
  </section>

  <div class="side">
    <article class="card panel" class:flipped={phase === "over"} aria-labelledby="card-title">
      <header class="card-head num">
        <span>Round {round}</span>
        <span>{mapName}</span>
        <span class:practice={!ranked}>{ranked ? "Rated" : "Practice"}</span>
      </header>

      {#if phase !== "over"}
        <div class="versus">
          <div class="fighter">
            <Sprite character="you" size={88} animate />
            <span class="fname" style:color={SIGNATURE.you}>You</span>
            <span class="frating num">{rating}</span>
          </div>
          <span class="vs" aria-hidden="true">VS</span>
          <div class="fighter">
            <Sprite character={characterOf(opponent)} size={88} animate />
            <span class="fname" style:color={SIGNATURE[characterOf(opponent)]}>{shortName(opponent)}</span>
            <span class="frating num">{opp.elo}{#if level(opponent)} · {level(opponent)}{/if}</span>
          </div>
        </div>
        <h1 id="card-title" class="visually-hidden">You versus {opp.name}</h1>
        {#if ranked}
          <dl class="stakes num">
            <div><dt>Win</dt><dd class="up">{signed(worth.win)}</dd></div>
            <div><dt>Draw</dt><dd>{signed(worth.draw)}</dd></div>
            <div><dt>Loss</dt><dd class="down">{signed(worth.loss)}</dd></div>
          </dl>
        {:else if practiceReason}
          <p class="note">{practiceReason}</p>
        {/if}

        {#if keyboardless}
          <p class="note">
            Matches need a keyboard. Open this page on a computer to play; the crosstable and the training story work
            here.
          </p>
        {:else}
          <button class="btn start" type="button" onclick={start} disabled={phase !== "ready"}>
            {#if phase === "preparing"}
              Setting up the arena…
            {:else if phase === "loading"}
              Loading {shortName(opponent)}'s network…
            {:else if phase === "countdown" || phase === "playing"}
              Match in progress
            {:else}
              Start match
            {/if}
          </button>
          <p class="keys">
            <kbd>←</kbd><kbd>↑</kbd><kbd>↓</kbd><kbd>→</kbd> move · <kbd>X</kbd> or <kbd>Space</kbd> drops a bomb ·
            <kbd>Enter</kbd> starts
          </p>
        {/if}
      {:else}
        <h1 id="card-title" class="result" class:loss={outcome === "loss"} class:draw={outcome === "draw"}>
          {outcome === "win" ? "You win" : outcome === "loss" ? "You lose" : "Draw"}
        </h1>
        <p class="cause">{cause}</p>
        <p class="meta num">
          Against {opp.name} · {view.steps} steps · {(view.steps / TPS).toFixed(0)} s{view.sudden
            ? " · reached sudden death"
            : ""}
        </p>

        <div class="record" aria-live="polite">
          {#if (recording === "needs-handle" || recording === "submitting") && outcome}
            <p class="rating-move num pending">
              {rating} → {rating + worth[outcome]}
              <span class:down={worth[outcome] < 0}>{signed(worth[outcome])}</span>
              <small>once recorded</small>
            </p>
          {/if}
          {#if recording === "needs-handle"}
            <form onsubmit={claimHandle}>
              <label for="handle">Your name on the crosstable</label>
              <div class="handle-row">
                <input
                  id="handle"
                  bind:value={handleDraft}
                  maxlength={HANDLE_MAX}
                  autocomplete="nickname"
                  aria-invalid={handleError ? "true" : undefined}
                  aria-describedby="handle-help"
                />
                <button class="btn" type="submit">Record result</button>
              </div>
              <p id="handle-help" class:error={!!handleError}>
                {handleError ?? "No signup. The name is tied to this browser."}
              </p>
            </form>
          {:else if recording === "submitting"}
            <p class="status">Checking the replay on the server…</p>
          {:else if recording === "recorded" && ratingChange}
            <p class="rating-move num">
              {ratingChange.before} → <strong>{ratingChange.after}</strong>
              <span class:down={ratingChange.delta < 0}>{signed(ratingChange.delta)}</span>
            </p>
            <p class="status">
              Verified by replay{ratingChange.rank ? ` · rank ${ratingChange.rank} on the crosstable` : ""}.
              {recordMessage}
            </p>
          {:else if recording === "saved" || recording === "rejected"}
            <p class="status" class:error={recording === "rejected"}>{recordMessage}</p>
          {:else if recording === "practice"}
            <p class="status">Practice match: not rated.</p>
          {/if}
        </div>

        <div class="after">
          {#if nextOnLadder() !== opponent}
            <button class="btn" type="button" onclick={() => prepare(nextOnLadder())}>
              Next: {AGENT_BY_ID[nextOnLadder()].name}
            </button>
          {/if}
          <button
            class="btn"
            class:btn-quiet={nextOnLadder() !== opponent}
            type="button"
            onclick={() => prepare(opponent)}>Rematch</button
          >
        </div>
      {/if}
    </article>

    <div class="standings-wrap">
      <Standings {rating} handle={profile.handle} change={recording === "recorded" ? (ratingChange?.delta ?? null) : null} />
    </div>
  </div>

</div>
<p class="visually-hidden" aria-live="assertive">{announcement}</p>

<style>
  .hall {
    max-width: 1344px;
    margin: 0 auto;
    padding: 24px var(--gutter) 0;
    display: grid;
    grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.72fr);
    grid-template-areas: "arena side";
    gap: clamp(18px, 2.4vw, 32px);
    align-items: start;
  }
  .arena-col {
    grid-area: arena;
    display: grid;
    gap: 12px;
    min-width: 0;
  }
  .side {
    grid-area: side;
    display: grid;
    gap: 18px;
    min-width: 0;
  }
  .roster-wrap {
    min-width: 0;
    margin-top: 6px;
  }
  .arena {
    position: relative;
    border: 3px solid var(--edge);
    border-radius: 4px;
    background: var(--floor);
    overflow: hidden;
  }
  .count {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    font-family: var(--pixel);
    font-size: clamp(5rem, 12vw, 9rem);
    font-weight: 700;
    color: var(--you);
    text-shadow: 0 6px 0 var(--edge);
    background: rgb(20 20 28 / 0.35);
    animation: count-in 550ms var(--ease-out);
  }
  @keyframes count-in {
    from {
      transform: scale(1.3);
    }
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 22px;
    color: var(--text-dim);
    font-size: 0.9rem;
  }
  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .tile {
    width: 20px;
    height: 20px;
    background-size: cover;
    image-rendering: pixelated;
  }
  .tile.brick {
    background-image: url("/sprites/destrWall.png");
  }
  .tile.stone {
    background-image: url("/sprites/destrWall_1.png");
  }
  .tile.wall {
    background-image: url("/sprites/wall.png");
  }
  .card {
    padding: 16px 20px 22px;
  }
  .card.flipped {
    animation: pop 420ms var(--ease-out);
  }
  @keyframes pop {
    from {
      transform: scale(0.96);
    }
  }
  .card-head {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding-bottom: 10px;
    border-bottom: 3px solid var(--edge);
    font-family: var(--pixel);
    font-size: 0.8rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .card-head .practice {
    color: var(--danger);
  }
  .versus {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    margin: 18px 0 6px;
  }
  .fighter {
    display: grid;
    justify-items: center;
    gap: 4px;
    text-align: center;
  }
  .fname {
    font-family: var(--pixel);
    font-size: 1.1rem;
    font-weight: 700;
    line-height: 1.1;
    white-space: nowrap;
  }
  .frating {
    font-family: var(--pixel);
    font-size: 0.85rem;
    color: var(--text-dim);
  }
  .vs {
    font-family: var(--pixel);
    font-size: 2rem;
    font-weight: 700;
    color: var(--danger);
    text-shadow: 0 4px 0 var(--edge);
  }
  .stakes {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    margin: 16px 0 18px;
    border: 3px solid var(--edge);
    border-radius: 4px;
    background: var(--bg-deep);
  }
  .stakes div {
    display: flex;
    flex-direction: column-reverse;
    padding: 8px 0 6px;
    text-align: center;
  }
  .stakes div + div {
    border-left: 2px solid var(--line);
  }
  .stakes dt {
    font-size: 0.85rem;
    color: var(--text-dim);
  }
  .stakes dd {
    margin: 0;
    font-family: var(--pixel);
    font-size: 1.4rem;
    font-weight: 700;
  }
  .stakes .up {
    color: var(--you);
  }
  .stakes .down {
    color: var(--danger);
  }
  .note {
    margin: 14px 0;
    color: var(--text-dim);
  }
  .start {
    width: 100%;
    font-size: 1.2rem;
    padding: 0.8em;
  }
  .keys {
    margin-top: 12px;
    font-size: 0.86rem;
    color: var(--text-dim);
  }
  kbd {
    display: inline-block;
    min-width: 1.7em;
    padding: 0 0.35em;
    margin: 0 1px;
    border: 2px solid var(--edge);
    border-bottom-width: 4px;
    border-radius: 3px;
    font-family: var(--pixel);
    font-size: 0.75rem;
    text-align: center;
    background: var(--panel-2);
    color: var(--text);
  }
  .result {
    margin-top: 18px;
    font-size: clamp(2.2rem, 4vw, 3.2rem);
    color: var(--you);
    text-shadow: 0 5px 0 var(--edge);
    animation: slam 380ms var(--ease-out);
  }
  .result.loss {
    color: var(--danger);
  }
  .result.draw {
    color: var(--text);
  }
  @keyframes slam {
    from {
      transform: scale(1.35);
    }
  }
  .cause {
    margin-top: 12px;
    font-size: 1.15rem;
    font-weight: 600;
  }
  .meta {
    margin-top: 6px;
    color: var(--text-dim);
  }
  .record {
    margin: 16px 0;
    padding: 14px 0;
    border-top: 2px solid var(--line);
    border-bottom: 2px solid var(--line);
    min-height: 4.5rem;
  }
  label {
    display: block;
    font-weight: 650;
    margin-bottom: 6px;
  }
  .handle-row {
    display: flex;
    gap: 8px;
  }
  input {
    flex: 1;
    min-width: 0;
    font: inherit;
    font-size: 1.05rem;
    padding: 0.6em 0.7em;
    border: 3px solid var(--edge);
    border-radius: 4px;
    background: var(--bg-deep);
    color: var(--text);
  }
  input[aria-invalid="true"] {
    border-color: var(--danger);
  }
  .handle-row .btn {
    font-size: 1.05rem;
  }
  #handle-help {
    margin-top: 6px;
    font-size: 0.86rem;
    color: var(--text-dim);
  }
  .error {
    color: var(--danger) !important;
  }
  .rating-move {
    font-family: var(--pixel);
    font-size: 1.3rem;
  }
  .rating-move strong {
    font-weight: 700;
    color: var(--you);
  }
  .rating-move span {
    margin-left: 8px;
    font-weight: 700;
    color: var(--you);
  }
  .rating-move span.down {
    color: var(--danger);
  }
  .rating-move.pending {
    font-size: 1.05rem;
    color: var(--text-dim);
    margin-bottom: 10px;
  }
  .rating-move small {
    margin-left: 8px;
    font-family: var(--font);
    font-size: 0.85rem;
  }
  .status {
    color: var(--text-dim);
  }
  .after {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .after .btn {
    flex: 1;
  }
  @media (max-width: 1000px) {
    /* one column: arena, then the VS card, then the roster */
    .hall {
      grid-template-columns: 1fr;
      grid-template-areas: none;
      display: flex;
      flex-direction: column;
    }
    .arena-col,
    .side {
      display: contents;
    }
    .roster-wrap {
      order: 2;
    }
    .standings-wrap {
      display: none;
    }
  }
</style>
