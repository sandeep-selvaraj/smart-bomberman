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
  import { needsNet, newEngine, opponentFor, matchSetup, type AgentId } from "../engine/match";
  import { loadPolicyNet, type PolicyNet } from "../engine/mlp";
  import type { Policy } from "../engine/policies";
  import { AGENTS, AGENT_BY_ID, isTwoFuse, level, shortName } from "../lib/agents";
  import { ApiError, startMatch, submitMatch } from "../lib/api";
  import { START_RATING, stakes, type Outcome } from "../lib/elo";
  import { handleProblem, HANDLE_MAX } from "../lib/handle";
  import { loadProfile, saveProfile, type Profile } from "../lib/profile";
  import Board from "./Board.svelte";
  import Clock from "./Clock.svelte";
  import Ladder from "./Ladder.svelte";
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
  let engine = $state<VersusEngine>(newEngine(1));
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
  let mapName = $derived(matchSetup(seed).map.replace("_", " "));
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
    engine = newEngine(seed);
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
    engine = newEngine(seed);
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
  <section class="table" aria-label="Board 1">
    <Clock
      you={{ name: "You", agent: false, alive: view.alive[0]!, fuse: view.fuse[0]! }}
      them={{ name: opp.name, agent: true, alive: view.alive[1]!, fuse: view.fuse[1]! }}
      steps={view.steps}
      suddenDeathStart={engine.config.suddenDeathStart}
      maxSteps={engine.config.maxSteps}
      openCells={view.open}
      tps={TPS}
    />
    <div class="board-sheet sheet">
      <Board
        {engine}
        {tick}
        tickMs={TICK_MS}
        label={`Board 1 on ${mapName}: you are the black piece, ${opp.name} the blue one.`}
      />
      {#if phase === "countdown"}
        <div class="count num" aria-hidden="true">{countdown}</div>
      {/if}
    </div>
    <p class="legend">
      <span><i class="dot you"></i>You</span>
      <span><i class="dot agent"></i>{shortName(opponent)}</span>
      <span><i class="diamond"></i>Wandering enemy, deadly to both</span>
      <span><i class="hatch"></i>Breakable wall</span>
    </p>
    <div class="ladder-wrap">
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
    <article class="slip sheet" class:flipped={phase === "over"} aria-labelledby="slip-title">
      <header class="slip-head num">
        <span>Round {round}</span>
        <span>Board 1</span>
        <span>{mapName}</span>
        <span class:practice={!ranked}>{ranked ? "Rated" : "Practice"}</span>
      </header>

      {#if phase !== "over"}
        <h1 id="slip-title" class="pairing">
          You vs <span class="opp">{shortName(opponent)}</span>
        </h1>
        <p class="ratings num">
          {#if level(opponent)}<strong>{level(opponent)}</strong> · {/if}rated {opp.elo} · you {rating}
        </p>
        {#if ranked}
          <dl class="stakes num">
            <div><dt>Win</dt><dd>{signed(worth.win)}</dd></div>
            <div><dt>Draw</dt><dd>{signed(worth.draw)}</dd></div>
            <div><dt>Loss</dt><dd>{signed(worth.loss)}</dd></div>
          </dl>
        {:else if practiceReason}
          <p class="practice-note">{practiceReason}</p>
        {/if}

        {#if keyboardless}
          <p class="device-note">
            Matches need a keyboard. Open this page on a computer to play; the crosstable and the training story work
            here.
          </p>
        {:else}
          <button class="btn start" type="button" onclick={start} disabled={phase !== "ready"}>
            {#if phase === "preparing"}
              Setting the board…
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
        <h1 id="slip-title" class="result" class:loss={outcome === "loss"}>
          {outcome === "win" ? "Won" : outcome === "loss" ? "Lost" : "Draw"}
        </h1>
        <p class="cause">{cause}</p>
        <p class="ratings num">
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

    <div class="standings-wrap"><Standings {rating} handle={profile.handle} change={recording === "recorded" ? (ratingChange?.delta ?? null) : null} /></div>
  </div>
</div>
<p class="visually-hidden" aria-live="assertive">{announcement}</p>

<style>
  .hall {
    max-width: 1344px;
    margin: 0 auto;
    padding: 28px var(--gutter) 0;
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.75fr);
    gap: clamp(20px, 3vw, 40px);
    align-items: start;
  }
  .table {
    display: grid;
    gap: 12px;
    min-width: 0;
  }
  .board-sheet {
    position: relative;
    padding: 10px;
  }
  .count {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    font-size: clamp(5rem, 12vw, 9rem);
    font-weight: 800;
    color: var(--ink);
    background: rgb(244 245 240 / 0.55);
    animation: count-in 550ms var(--ease-out);
  }
  @keyframes count-in {
    from {
      transform: scale(1.25);
      opacity: 0.2;
    }
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 22px;
    color: var(--chalk-dim);
    font-size: 0.88rem;
  }
  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .legend i {
    display: inline-block;
    width: 14px;
    height: 14px;
  }
  .dot {
    border-radius: 50%;
    box-shadow: inset 0 0 0 3px currentColor;
  }
  .dot.you {
    background: var(--ink);
    box-shadow: 0 0 0 1.5px var(--chalk);
  }
  .dot.agent {
    background: var(--agent);
    box-shadow: 0 0 0 1.5px var(--chalk);
  }
  .diamond {
    background: var(--flag);
    transform: rotate(45deg) scale(0.75);
  }
  .hatch {
    background: repeating-linear-gradient(135deg, var(--chalk-dim) 0 1.5px, transparent 1.5px 5px);
  }
  .side {
    display: grid;
    gap: 22px;
    min-width: 0;
    position: sticky; /* the slip and your standing stay beside the ladder as it scrolls */
    top: 16px;
  }
  .slip {
    padding: 22px 26px 26px;
    transform: rotate(-0.5deg);
    transform-origin: 30% 0;
  }
  .slip.flipped {
    animation: flip 520ms var(--ease-out);
  }
  @keyframes flip {
    from {
      transform: rotate(-0.5deg) rotateX(70deg);
      opacity: 0.4;
    }
  }
  .slip-head {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding-bottom: 9px;
    border-bottom: 2px solid var(--ink);
    font-size: 0.82rem;
    font-weight: 650;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .slip-head .practice {
    color: var(--flag-ink);
  }
  .pairing {
    margin-top: 20px;
    font-size: clamp(2.4rem, 4.2vw, 3.6rem);
  }
  .opp {
    color: var(--agent);
    white-space: nowrap;
  }
  .ratings {
    margin-top: 8px;
    font-size: 1.05rem;
    color: var(--ink-soft);
  }
  .ratings strong {
    color: var(--agent);
    text-transform: capitalize;
  }
  .stakes {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    margin: 18px 0 20px;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
  }
  .stakes div {
    padding: 10px 0 8px;
    text-align: center;
  }
  .stakes div + div {
    border-left: 1px solid var(--rule);
  }
  .stakes dt {
    font-size: 0.85rem;
    color: var(--ink-soft);
    order: 2;
  }
  .stakes dd {
    margin: 0;
    font-size: 1.85rem;
    font-weight: 780;
    font-stretch: 72%;
  }
  .stakes div {
    display: flex;
    flex-direction: column-reverse;
  }
  .practice-note,
  .device-note {
    margin: 16px 0;
    padding: 10px 0;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    color: var(--ink-soft);
  }
  .start {
    width: 100%;
    font-size: 1.25rem;
    padding: 1em;
  }
  .keys {
    margin-top: 12px;
    font-size: 0.86rem;
    color: var(--ink-soft);
  }
  kbd {
    display: inline-block;
    min-width: 1.6em;
    padding: 0 0.35em;
    margin: 0 1px;
    border: 1px solid var(--rule-strong);
    border-bottom-width: 2px;
    border-radius: 3px;
    font: inherit;
    font-size: 0.8rem;
    text-align: center;
    background: #fff;
    color: var(--ink);
  }
  .result {
    margin-top: 16px;
    font-size: clamp(3.4rem, 6vw, 5rem);
    font-stretch: 70%;
    letter-spacing: 0.01em;
    text-transform: uppercase;
    display: inline-block;
    padding: 0 12px;
    border: 4px solid currentColor;
    border-radius: 4px;
    transform: rotate(-3deg);
    animation: stamp 420ms var(--ease-out) 120ms both;
  }
  .result.loss {
    color: var(--flag-ink);
  }
  @keyframes stamp {
    from {
      transform: rotate(-3deg) scale(1.35);
    }
  }
  .cause {
    margin-top: 14px;
    font-size: 1.15rem;
    font-weight: 600;
  }
  .record {
    margin: 18px 0 18px;
    padding: 14px 0;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
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
    border: 1.5px solid var(--ink);
    border-radius: 2px;
    background: #fff;
    color: var(--ink);
  }
  input[aria-invalid="true"] {
    border-color: var(--flag-ink);
  }
  #handle-help {
    margin-top: 6px;
    font-size: 0.86rem;
    color: var(--ink-soft);
  }
  .error {
    color: var(--flag-ink) !important;
  }
  .rating-move {
    font-size: 1.6rem;
    font-weight: 600;
  }
  .rating-move strong {
    font-weight: 800;
  }
  .rating-move span {
    margin-left: 8px;
    font-weight: 800;
  }
  .rating-move span.down {
    color: var(--flag-ink);
  }
  .rating-move.pending {
    font-size: 1.25rem;
    color: var(--ink-soft);
    margin-bottom: 10px;
  }
  .rating-move small {
    margin-left: 8px;
    font-size: 0.85rem;
    font-weight: 500;
  }
  .status {
    color: var(--ink-soft);
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
    /* one column: board, then the slip, then the ladder; the crosstable follows the page */
    .hall {
      grid-template-columns: 1fr;
    }
    .table,
    .side {
      display: contents;
    }
    .ladder-wrap {
      order: 2;
    }
    .standings-wrap {
      display: none;
    }
    .slip {
      transform: none;
    }
  }
</style>
