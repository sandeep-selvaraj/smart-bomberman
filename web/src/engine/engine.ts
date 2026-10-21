/**
 * Battle mode on a tile grid: a TypeScript port of src/game/ai/engine.py and
 * versus_engine.py. Every rule, every random draw and every float32 rounding
 * follows the Python reference, so the trained agents see the observations
 * they were trained on and a match replays identically from its seed. The
 * parity tests in tests/parity.test.ts hold it to that.
 */
import type { SeedRng } from "./rng";

export const NOOP = 0;
export const UP = 1;
export const DOWN = 2;
export const LEFT = 3;
export const RIGHT = 4;
export const BOMB = 5;
export type Action = 0 | 1 | 2 | 3 | 4 | 5;

/** Moves in the reference's dict order: up, down, left, right. */
export const MOVES: ReadonlyArray<readonly [Action, number, number]> = [
  [UP, -1, 0],
  [DOWN, 1, 0],
  [LEFT, 0, -1],
  [RIGHT, 0, 1],
];
const DELTA: Record<number, readonly [number, number]> = { 1: [-1, 0], 2: [1, 0], 3: [0, -1], 4: [0, 1] };

export type Cell = readonly [number, number];
export type Cause = "enemy" | "own_bomb" | "opponent_bomb" | "crushed";

export interface Config {
  bombFuse: number;
  flameDuration: number;
  bombRange: number;
  bombLimit: number;
  enemyMoveEvery: number;
  enemyTurnProb: number;
  maxSteps: number;
  suddenDeathStart: number;
  suddenDeathEvery: number;
  suddenDeathWarning: number;
  enemies: boolean;
}

export const DEFAULT_CONFIG: Config = {
  bombFuse: 8,
  flameDuration: 2,
  bombRange: 1,
  bombLimit: 1,
  enemyMoveEvery: 2,
  enemyTurnProb: 0.25,
  maxSteps: 1000,
  suddenDeathStart: 200,
  suddenDeathEvery: 1,
  suddenDeathWarning: 12,
  enemies: true,
};

export interface Layout {
  name: string;
  height: number;
  width: number;
  solid: Uint8Array;
  wallHp: Int8Array;
  player: Cell;
  rival: Cell | null;
  enemies: Cell[];
}

/** Parse the ASCII rows written by web_export.export_maps. */
export function parseLayout(name: string, rows: string[]): Layout {
  const height = rows.length;
  const width = rows[0]!.length;
  const solid = new Uint8Array(height * width);
  const wallHp = new Int8Array(height * width);
  let player: Cell | null = null;
  let rival: Cell | null = null;
  const enemies: Cell[] = [];
  rows.forEach((row, r) => {
    [...row].forEach((ch, c) => {
      const i = r * width + c;
      if (ch === "#") solid[i] = 1;
      else if (ch === "b") wallHp[i] = 1;
      else if (ch === "B") wallHp[i] = 2;
      else if (ch === "P") player = [r, c];
      else if (ch === "Q") rival = [r, c];
      else if (ch === "E") enemies.push([r, c]);
    });
  });
  if (!player) throw new Error(`map ${name} has no player start`);
  return { name, height, width, solid, wallHp, player, rival, enemies };
}

/** The free cell closest to the point mirror of the first start (row-major tie-break, like numpy argmin). */
export function mirrorSpawn(layout: Layout): Cell {
  const { height, width } = layout;
  const tr = height - 1 - layout.player[0];
  const tc = width - 1 - layout.player[1];
  let best: Cell | null = null;
  let bestDist = Infinity;
  for (let r = 0; r < height; r++) {
    for (let c = 0; c < width; c++) {
      const i = r * width + c;
      if (layout.solid[i] || layout.wallHp[i] > 0) continue;
      if (r === layout.player[0] && c === layout.player[1]) continue;
      if (layout.enemies.some(([er, ec]) => er === r && ec === c)) continue;
      const d = Math.abs(r - tr) + Math.abs(c - tc);
      if (d < bestDist) {
        bestDist = d;
        best = [r, c];
      }
    }
  }
  return best!;
}

export interface Bomb {
  r: number;
  c: number;
  timer: number;
  range: number;
  owner: number;
}

export interface Enemy {
  r: number;
  c: number;
  dr: number;
  dc: number;
  alive: boolean;
}

export interface Fighter {
  r: number;
  c: number;
  alive: boolean;
  killedBy: Cause | null;
}

export interface FighterEvents {
  wallsDestroyed: number;
  enemiesKilled: number;
  bombPlaced: boolean;
  invalidAction: boolean;
  died: boolean;
  killedBy: Cause | null;
  killedOpponent: boolean;
}

export interface StepEvents {
  players: [FighterEvents, FighterEvents];
  done: boolean;
  winner: number | null;
  draw: boolean;
  truncated: boolean;
}

const freshEvents = (): FighterEvents => ({
  wallsDestroyed: 0,
  enemiesKilled: 0,
  bombPlaced: false,
  invalidAction: false,
  died: false,
  killedBy: null,
  killedOpponent: false,
});

export class VersusEngine {
  readonly layout: Layout;
  readonly config: Config;
  readonly height: number;
  readonly width: number;
  rng: SeedRng;
  swap: boolean;

  solid!: Uint8Array;
  wallHp!: Int8Array;
  flames!: Int8Array;
  flameOwner!: Int8Array;
  players!: [Fighter, Fighter];
  bombs!: Bomb[];
  enemies!: Enemy[];
  initialEnemies = 0;
  closingOrder!: Cell[];
  closed = 0;
  steps = 0;
  finished = false;
  winner: number | null = null;

  constructor(layout: Layout, rng: SeedRng, swap = false, config: Partial<Config> = {}) {
    this.layout = layout;
    this.config = { ...DEFAULT_CONFIG, ...config };
    if (this.config.suddenDeathEvery < 1) throw new Error("suddenDeathEvery must be at least 1");
    this.height = layout.height;
    this.width = layout.width;
    this.rng = rng;
    this.swap = swap;
    this.reset();
  }

  // ------------------------------------------------------------------ setup
  reset(): void {
    const { layout } = this;
    this.solid = layout.solid.slice();
    this.wallHp = layout.wallHp.slice();
    const starts: Cell[] = [layout.player, layout.rival ?? mirrorSpawn(layout)];
    if (this.swap) starts.reverse();
    this.players = starts.map(([r, c]) => ({ r, c, alive: true, killedBy: null })) as [Fighter, Fighter];
    this.steps = 0;
    this.bombs = [];
    this.flames = new Int8Array(this.height * this.width);
    this.flameOwner = new Int8Array(this.height * this.width).fill(-1);
    const cells = this.config.enemies ? layout.enemies : [];
    this.enemies = cells.map(([r, c]) => {
      const [dr, dc] = this.randomDirection(r, c);
      return { r, c, dr, dc, alive: true };
    });
    this.initialEnemies = this.enemies.length;
    this.closingOrder = this.spiralCells();
    this.closed = 0;
    this.finished = false;
    this.winner = null;
  }

  private spiralCells(): Cell[] {
    let top = 0;
    let left = 0;
    let bottom = this.height - 1;
    let right = this.width - 1;
    const order: Cell[] = [];
    while (top <= bottom && left <= right) {
      for (let c = left; c <= right; c++) order.push([top, c]);
      for (let r = top + 1; r <= bottom; r++) order.push([r, right]);
      if (bottom > top) for (let c = right - 1; c >= left; c--) order.push([bottom, c]);
      if (right > left) for (let r = bottom - 1; r > top; r--) order.push([r, left]);
      top++;
      left++;
      bottom--;
      right--;
    }
    const fair: Cell[] = [];
    const seen = new Set<number>();
    for (const [r, c] of order) {
      for (const [rr, cc] of [
        [r, c],
        [this.height - 1 - r, this.width - 1 - c],
      ] as const) {
        const i = this.idx(rr, cc);
        if (!seen.has(i) && !this.solid[i]) {
          seen.add(i);
          fair.push([rr, cc]);
        }
      }
    }
    return fair;
  }

  // ---------------------------------------------------------------- queries
  idx(r: number, c: number): number {
    return r * this.width + c;
  }

  inBounds(r: number, c: number): boolean {
    return r >= 0 && r < this.height && c >= 0 && c < this.width;
  }

  isBlocked(r: number, c: number): boolean {
    if (!this.inBounds(r, c)) return true;
    const i = this.idx(r, c);
    if (this.solid[i] || this.wallHp[i]! > 0) return true;
    return this.bombs.some((b) => b.r === r && b.c === c);
  }

  get suddenDeath(): boolean {
    return this.steps >= this.config.suddenDeathStart;
  }

  get enemiesAlive(): number {
    return this.enemies.filter((e) => e.alive).length;
  }

  closeStep(index: number): number {
    return this.config.suddenDeathStart + index * this.config.suddenDeathEvery;
  }

  blastCells(bomb: { r: number; c: number; range: number }): Cell[] {
    const cells: Cell[] = [[bomb.r, bomb.c]];
    for (const [, dr, dc] of MOVES) {
      for (let dist = 1; dist <= bomb.range; dist++) {
        const r = bomb.r + dr * dist;
        const c = bomb.c + dc * dist;
        if (!this.inBounds(r, c) || this.solid[this.idx(r, c)]) break;
        cells.push([r, c]);
        if (this.wallHp[this.idx(r, c)]! > 0) break;
      }
    }
    return cells;
  }

  /** Per-cell urgency of cells about to close; 1 means next step. float32 like the reference. */
  closingMap(): Float32Array {
    const urgency = new Float32Array(this.height * this.width);
    const horizon = this.config.suddenDeathWarning;
    for (let index = this.closed; index < this.closingOrder.length; index++) {
      const wait = this.closeStep(index) - this.steps;
      if (wait > horizon) break;
      const [r, c] = this.closingOrder[index]!;
      urgency[this.idx(r, c)] = 1.0 - (Math.max(wait, 1) - 1) / horizon;
    }
    return urgency;
  }

  /** Flames, plus cells that close before a freshly placed bomb would go off. */
  hazardMask(): Uint8Array {
    const mask = new Uint8Array(this.height * this.width);
    for (let i = 0; i < mask.length; i++) mask[i] = this.flames[i]! > 0 ? 1 : 0;
    for (let index = this.closed; index < this.closingOrder.length; index++) {
      if (this.closeStep(index) - this.steps > this.config.bombFuse) break;
      const [r, c] = this.closingOrder[index]!;
      mask[this.idx(r, c)] = 1;
    }
    return mask;
  }

  /** Bomb and flame danger plus the closing walls, in [0, 1]. */
  dangerMap(): Float32Array {
    const danger = new Float32Array(this.height * this.width);
    for (let i = 0; i < danger.length; i++) danger[i] = this.flames[i]! > 0 ? 1 : 0;
    for (const bomb of this.bombs) {
      const urgency = 1.0 - (bomb.timer - 1) / this.config.bombFuse;
      for (const [r, c] of this.blastCells(bomb)) {
        const i = this.idx(r, c);
        danger[i] = Math.max(danger[i]!, urgency);
      }
    }
    const closing = this.closingMap();
    for (let i = 0; i < danger.length; i++) danger[i] = Math.max(danger[i]!, closing[i]!);
    return danger;
  }

  /** Steps from each cell to the nearest cell no current (or hypothetical) bomb can reach; Infinity if none. */
  escapeDistances(extraBomb: Cell | null = null): Float32Array {
    const bombs: Array<{ r: number; c: number; range: number }> = [...this.bombs];
    if (extraBomb) bombs.push({ r: extraBomb[0], c: extraBomb[1], range: this.config.bombRange });
    const unsafe = this.hazardMask();
    for (const bomb of bombs) for (const [r, c] of this.blastCells(bomb)) unsafe[this.idx(r, c)] = 1;
    const bombCells: number[] = [];
    for (const b of bombs) {
      const i = this.idx(b.r, b.c);
      if (!bombCells.includes(i)) bombCells.push(i);
    }
    const n = this.height * this.width;
    const walkable = new Uint8Array(n);
    for (let i = 0; i < n; i++) walkable[i] = !this.solid[i] && this.wallHp[i] === 0 ? 1 : 0;
    for (const i of bombCells) walkable[i] = 0;
    const dist = new Float32Array(n).fill(Infinity);
    let frontier: number[] = [];
    for (let i = 0; i < n; i++) {
      if (walkable[i] && !unsafe[i]) {
        dist[i] = 0;
        frontier.push(i);
      }
    }
    while (frontier.length) {
      const next: number[] = [];
      for (const i of frontier) {
        const r = Math.floor(i / this.width);
        const c = i % this.width;
        for (const [, dr, dc] of MOVES) {
          const nr = r + dr;
          const nc = c + dc;
          if (!this.inBounds(nr, nc)) continue;
          const j = this.idx(nr, nc);
          if (walkable[j] && dist[j] === Infinity) {
            dist[j] = dist[i]! + 1;
            next.push(j);
          }
        }
      }
      frontier = next;
    }
    for (const i of bombCells) {
      const r = Math.floor(i / this.width);
      const c = i % this.width;
      let best = Infinity;
      for (const [, dr, dc] of MOVES) {
        if (this.inBounds(r + dr, c + dc)) best = Math.min(best, dist[this.idx(r + dr, c + dc)]!);
      }
      dist[i] = best + 1;
    }
    return dist;
  }

  /** Shortest walking distance to the nearest source; breakable walls cost `breakableCost`. */
  distanceMap(sources: Cell[], breakableCost = 4): Float32Array {
    const n = this.height * this.width;
    const dist = new Float32Array(n).fill(Infinity);
    const heap = new MinHeap();
    for (const [r, c] of sources) {
      dist[this.idx(r, c)] = 0;
      heap.push(0, this.idx(r, c));
    }
    while (heap.size) {
      const [d, i] = heap.pop();
      if (d > dist[i]!) continue;
      const r = Math.floor(i / this.width);
      const c = i % this.width;
      for (const [, dr, dc] of MOVES) {
        const nr = r + dr;
        const nc = c + dc;
        if (!this.inBounds(nr, nc)) continue;
        const j = this.idx(nr, nc);
        if (this.solid[j]) continue;
        const nd = d + (this.wallHp[j]! > 0 ? breakableCost : 1);
        if (nd < dist[j]!) {
          dist[j] = nd;
          heap.push(nd, j);
        }
      }
    }
    return dist;
  }

  bombsLeft(player: number): number {
    return this.config.bombLimit - this.bombs.filter((b) => b.owner === player).length;
  }

  canEscapeBomb(player: number): boolean {
    const f = this.players[player]!;
    if (this.bombsLeft(player) <= 0 || this.bombs.some((b) => b.r === f.r && b.c === f.c)) return false;
    return this.escapeDistances([f.r, f.c])[this.idx(f.r, f.c)]! <= this.config.bombFuse - 1;
  }

  // ------------------------------------------------------------------- step
  step(actions: readonly [number, number]): StepEvents {
    if (this.finished) throw new Error("step() called on a finished match");
    const events: StepEvents = {
      players: [freshEvents(), freshEvents()],
      done: false,
      winner: null,
      draw: false,
      truncated: false,
    };
    this.steps += 1;

    this.players.forEach((f, p) => {
      const delta = DELTA[actions[p]!];
      if (f.alive && delta) {
        const r = f.r + delta[0];
        const c = f.c + delta[1];
        if (this.isBlocked(r, c)) events.players[p].invalidAction = true;
        else {
          f.r = r;
          f.c = c;
        }
      }
    });
    for (const p of this.rng.permutation(2)) {
      const f = this.players[p]!;
      const ev = events.players[p as 0 | 1];
      if (f.alive && actions[p] === BOMB) {
        if (this.bombsLeft(p) > 0 && !this.bombs.some((b) => b.r === f.r && b.c === f.c)) {
          this.bombs.push({ r: f.r, c: f.c, timer: this.config.bombFuse, range: this.config.bombRange, owner: p });
          ev.bombPlaced = true;
        } else ev.invalidAction = true;
      }
    }

    this.checkContact(events);
    if (this.steps % this.config.enemyMoveEvery === 0) {
      this.moveEnemies();
      this.checkContact(events);
    }
    this.tickBombs(events);
    this.applyFlames(events);
    this.closeCells(events);
    this.resolve(events);
    return events;
  }

  private randomDirection(r: number, c: number): [number, number] {
    const options = MOVES.filter(([, dr, dc]) => !this.isBlocked(r + dr, c + dc));
    if (!options.length) return [0, 0];
    const [, dr, dc] = options[this.rng.integers(options.length)]!;
    return [dr, dc];
  }

  private moveEnemies(): void {
    for (const e of this.enemies) {
      if (!e.alive) continue;
      const aheadBlocked = (e.dr === 0 && e.dc === 0) || this.isBlocked(e.r + e.dr, e.c + e.dc);
      if (aheadBlocked || this.rng.random() < this.config.enemyTurnProb) {
        const options = MOVES.filter(([, dr, dc]) => !this.isBlocked(e.r + dr, e.c + dc));
        const forward = options.filter(([, dr, dc]) => !(dr === -e.dr && dc === -e.dc));
        const pool = forward.length ? forward : options;
        if (pool.length) {
          const [, dr, dc] = pool[this.rng.integers(pool.length)]!;
          e.dr = dr;
          e.dc = dc;
        } else {
          e.dr = 0;
          e.dc = 0;
        }
      }
      if (e.dr !== 0 || e.dc !== 0) {
        e.r += e.dr;
        e.c += e.dc;
      }
    }
  }

  private kill(p: number, cause: Cause, events: StepEvents): void {
    const f = this.players[p]!;
    f.alive = false;
    f.killedBy = cause;
    events.players[p as 0 | 1].died = true;
    events.players[p as 0 | 1].killedBy = cause;
  }

  private checkContact(events: StepEvents): void {
    this.players.forEach((f, p) => {
      if (f.alive && this.enemies.some((e) => e.alive && e.r === f.r && e.c === f.c)) this.kill(p, "enemy", events);
    });
  }

  private tickBombs(events: StepEvents): void {
    for (let i = 0; i < this.flames.length; i++) {
      if (this.flames[i]! > 0) this.flames[i] = this.flames[i]! - 1;
      if (this.flames[i] === 0) this.flameOwner[i] = -1;
    }
    for (const b of this.bombs) b.timer -= 1;
    const exploding = this.bombs.filter((b) => b.timer <= 0);
    while (exploding.length) {
      const bomb = exploding.pop()!;
      const at = this.bombs.indexOf(bomb);
      if (at < 0) continue;
      this.bombs.splice(at, 1);
      for (const [r, c] of this.blastCells(bomb)) {
        const i = this.idx(r, c);
        this.flames[i] = this.config.flameDuration;
        this.flameOwner[i] = bomb.owner;
        if (this.wallHp[i]! > 0) {
          this.wallHp[i] = this.wallHp[i]! - 1;
          if (this.wallHp[i] === 0) events.players[bomb.owner as 0 | 1].wallsDestroyed += 1;
        }
        for (const b of this.bombs) if (b.r === r && b.c === c && !exploding.includes(b)) exploding.push(b);
      }
    }
  }

  private applyFlames(events: StepEvents): void {
    for (const e of this.enemies) {
      const i = this.idx(e.r, e.c);
      if (e.alive && this.flames[i]! > 0) {
        e.alive = false;
        const owner = this.flameOwner[i]!;
        if (owner >= 0) events.players[owner as 0 | 1].enemiesKilled += 1;
      }
    }
    this.players.forEach((f, p) => {
      const i = this.idx(f.r, f.c);
      if (f.alive && this.flames[i]! > 0) {
        const owner = this.flameOwner[i]!;
        this.kill(p, owner === p ? "own_bomb" : "opponent_bomb", events);
        if (owner >= 0 && owner !== p) events.players[owner as 0 | 1].killedOpponent = true;
      }
    });
  }

  private closeCells(events: StepEvents): void {
    while (this.closed < this.closingOrder.length && this.steps >= this.closeStep(this.closed)) {
      const [r, c] = this.closingOrder[this.closed]!;
      this.closed += 1;
      const i = this.idx(r, c);
      this.solid[i] = 1;
      this.wallHp[i] = 0;
      this.flames[i] = 0;
      this.bombs = this.bombs.filter((b) => !(b.r === r && b.c === c));
      for (const e of this.enemies) if (e.alive && e.r === r && e.c === c) e.alive = false;
      this.players.forEach((f, p) => {
        if (f.alive && f.r === r && f.c === c) this.kill(p, "crushed", events);
      });
    }
  }

  private resolve(events: StepEvents): void {
    const alive = this.players.map((f) => f.alive);
    if (!alive[0] && !alive[1]) events.done = events.draw = true;
    else if (!alive[0] || !alive[1]) {
      events.done = true;
      events.winner = alive[0] ? 0 : 1;
    } else if (this.steps >= this.config.maxSteps) events.done = events.draw = events.truncated = true;
    this.finished = events.done;
    this.winner = events.winner;
  }

  /** The state fingerprint text, identical to web_export._digest before hashing. */
  digestText(): string {
    const fighters = this.players.map((f) => `${f.r},${f.c},${f.alive ? 1 : 0},${f.killedBy ?? ""}`).join(";");
    const bombs = this.bombs.map((b) => `${b.r},${b.c},${b.timer},${b.owner}`).join(";");
    const enemies = this.enemies.map((e) => `${e.r},${e.c},${e.dr},${e.dc},${e.alive ? 1 : 0}`).join(";");
    const owners = Array.from(this.flameOwner, (v) => v + 1);
    const grids = [Array.from(this.wallHp), Array.from(this.flames), owners, Array.from(this.solid)]
      .map((g) => g.join(""))
      .join("|");
    return `${this.steps}|${fighters}|${bombs}|${enemies}|${this.closed}|${grids}`;
  }
}

/** Binary min-heap on (priority, index), ordered like Python's heapq on tuples. */
class MinHeap {
  private items: Array<[number, number]> = [];

  get size(): number {
    return this.items.length;
  }

  push(priority: number, index: number): void {
    const items = this.items;
    items.push([priority, index]);
    let i = items.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (!less(items[i]!, items[parent]!)) break;
      [items[i], items[parent]] = [items[parent]!, items[i]!];
      i = parent;
    }
  }

  pop(): [number, number] {
    const items = this.items;
    const top = items[0]!;
    const last = items.pop()!;
    if (items.length) {
      items[0] = last;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let m = i;
        if (l < items.length && less(items[l]!, items[m]!)) m = l;
        if (r < items.length && less(items[r]!, items[m]!)) m = r;
        if (m === i) break;
        [items[i], items[m]] = [items[m]!, items[i]!];
        i = m;
      }
    }
    return top;
  }
}

const less = (a: [number, number], b: [number, number]): boolean => a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]);
