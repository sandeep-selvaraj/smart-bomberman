/**
 * The opponents: ports of the scripted bots in src/game/ai/policies.py, plus
 * the trained agent driven by its exported network. Random draws come from
 * the seat's own SeedRng stream, in the same order as the Python bots, so a
 * seeded match plays out identically in both languages.
 */
import { BOMB, MOVES, NOOP, type Action, type VersusEngine } from "./engine";
import { argmax, type PolicyNet } from "./mlp";
import { observe } from "./observation";
import type { SeedRng } from "./rng";

export interface Policy {
  readonly id: string;
  act(engine: VersusEngine, me: number): Action;
}

type Move = readonly [Action, number, number]; // action, row, col

/** Lexicographic comparison of key tuples, like Python's tuple ordering. */
function keyLess(a: number[], b: number[]): boolean {
  for (let i = 0; i < a.length; i++) {
    if (a[i]! < b[i]!) return true;
    if (a[i]! > b[i]!) return false;
  }
  return false;
}

/** Python's min(items, key=...): evaluates the key once per item in order and keeps the first minimum. */
function minBy<T>(items: T[], key: (item: T) => number[]): T {
  let best = items[0]!;
  let bestKey = key(best);
  for (let i = 1; i < items.length; i++) {
    const k = key(items[i]!);
    if (keyLess(k, bestKey)) {
      best = items[i]!;
      bestKey = k;
    }
  }
  return best;
}

class BotView {
  readonly cell: readonly [number, number];
  readonly danger: Float32Array;
  readonly escape: Float32Array;
  readonly enemyCells: Array<[number, number]>;
  readonly moves: Move[] = [];
  readonly safe: Move[];

  constructor(
    readonly engine: VersusEngine,
    readonly me: number,
  ) {
    const f = engine.players[me]!;
    this.cell = [f.r, f.c];
    this.danger = engine.dangerMap();
    this.escape = engine.escapeDistances();
    this.enemyCells = engine.enemies.filter((e) => e.alive).map((e) => [e.r, e.c]);
    for (const [action, dr, dc] of MOVES) {
      const r = f.r + dr;
      const c = f.c + dc;
      if (!engine.isBlocked(r, c) && !this.enemyCells.some(([er, ec]) => er === r && ec === c)) {
        this.moves.push([action, r, c]);
      }
    }
    this.safe = this.moves.filter(([, r, c]) => this.escape[engine.idx(r, c)] === 0 && this.enemyGap(r, c) > 1);
  }

  esc(r: number, c: number): number {
    return this.escape[this.engine.idx(r, c)]!;
  }

  /** Manhattan distance to the nearest wandering enemy (99 when there is none). */
  enemyGap(r: number, c: number): number {
    let best = 99;
    for (const [er, ec] of this.enemyCells) best = Math.min(best, Math.abs(r - er) + Math.abs(c - ec));
    return best;
  }
}

export class HeuristicPolicy implements Policy {
  private readonly rules: Array<(v: BotView) => Action | null>;

  constructor(
    readonly id: string,
    private readonly rng: SeedRng,
    private readonly wander = 0.1,
    aggressive = true,
  ) {
    this.rules = aggressive
      ? [this.flee, this.strike, this.backOff, this.wanderRule, this.advance]
      : [this.flee, this.backOff, this.wanderRule];
  }

  act(engine: VersusEngine, me: number): Action {
    const view = new BotView(engine, me);
    for (const rule of this.rules) {
      const action = rule.call(this, view);
      if (action !== null) return action;
    }
    return NOOP;
  }

  private flee(v: BotView): Action | null {
    if (v.esc(v.cell[0], v.cell[1]) === 0) return null;
    if (!v.moves.length) return NOOP;
    const key = ([, r, c]: Move) => [
      v.esc(r, c),
      v.enemyGap(r, c) <= 1 ? 1 : 0,
      v.danger[v.engine.idx(r, c)]!,
      this.rng.random(),
    ];
    return minBy(v.moves, key)[0];
  }

  private strike(v: BotView): Action | null {
    const rival = v.engine.players[1 - v.me]!;
    const gap = rival.alive ? Math.abs(v.cell[0] - rival.r) + Math.abs(v.cell[1] - rival.c) : 99;
    if ((gap <= 2 || v.enemyGap(v.cell[0], v.cell[1]) <= 2) && v.engine.canEscapeBomb(v.me)) return BOMB;
    return null;
  }

  private backOff(v: BotView): Action | null {
    const gapHere = v.enemyGap(v.cell[0], v.cell[1]);
    if (gapHere > 2) return null;
    const retreat = v.safe.filter(([, r, c]) => v.enemyGap(r, c) > gapHere);
    return retreat.length ? retreat[this.rng.integers(retreat.length)]![0] : null;
  }

  private wanderRule(v: BotView): Action | null {
    if (v.safe.length && this.rng.random() < this.wander) return v.safe[this.rng.integers(v.safe.length)]![0];
    return null;
  }

  private advance(v: BotView): Action | null {
    const rival = v.engine.players[1 - v.me]!;
    if (!rival.alive) return null;
    const dist = v.engine.distanceMap([[rival.r, rival.c]]);
    const here = dist[v.engine.idx(v.cell[0], v.cell[1])]!;
    const options = v.safe.filter(([, r, c]) => dist[v.engine.idx(r, c)]! < here);
    if (options.length) return minBy(options, ([, r, c]) => [dist[v.engine.idx(r, c)]!, this.rng.random()])[0];
    for (const [, dr, dc] of MOVES) {
      const r = v.cell[0] + dr;
      const c = v.cell[1] + dc;
      if (v.engine.inBounds(r, c) && v.engine.wallHp[v.engine.idx(r, c)]! > 0 && dist[v.engine.idx(r, c)]! < here) {
        return v.engine.canEscapeBomb(v.me) ? BOMB : null;
      }
    }
    return null;
  }
}

export class RandomPolicy implements Policy {
  readonly id = "random";

  constructor(private readonly rng: SeedRng) {}

  act(): Action {
    return this.rng.integers(6) as Action;
  }
}

/** The trained agent. Greedy plays its best move; sampled draws from its softmax with the seat's generator. */
export class ModelPolicy implements Policy {
  constructor(
    readonly id: string,
    private readonly net: PolicyNet,
    private readonly greedy: boolean,
    private readonly rng: SeedRng,
  ) {}

  act(engine: VersusEngine, me: number): Action {
    const logits = this.net.logits(observe(engine, me));
    if (this.greedy) return argmax(logits) as Action;
    const peak = Math.max(...logits);
    const weights = Array.from(logits, (l) => Math.exp(l - peak));
    const total = weights.reduce((a, b) => a + b, 0);
    let u = this.rng.random() * total;
    for (let i = 0; i < weights.length; i++) {
      u -= weights[i]!;
      if (u < 0) return i as Action;
    }
    return (weights.length - 1) as Action;
  }
}

export const camper = (rng: SeedRng): HeuristicPolicy => new HeuristicPolicy("camper", rng, 0.1, false);
export const wanderer = (rng: SeedRng): HeuristicPolicy => new HeuristicPolicy("wanderer", rng, 0.8, false);
export const heuristic = (rng: SeedRng): HeuristicPolicy => new HeuristicPolicy("heuristic", rng, 0.1, true);
