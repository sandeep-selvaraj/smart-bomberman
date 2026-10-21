/**
 * What a trained agent sees: a port of versus_observation in
 * src/game/ai/versus_env.py. Nine 9x9 planes around the agent (solid,
 * breakable, bomb, flame, danger, hostile, door, opponent, closing) and 24
 * state values, both float32 like the training environment.
 */
import { MOVES, type VersusEngine } from "./engine";

export const VIEW_RADIUS = 4;
export const CHANNELS = 9;
export const VIEW = 2 * VIEW_RADIUS + 1;
export const LOCAL_SIZE = CHANNELS * VIEW * VIEW;
export const STATE_SIZE = 24;

const clip = (v: number, lo: number, hi: number): number => Math.min(Math.max(v, lo), hi);

export interface Observation {
  local: Float32Array;
  state: Float32Array;
}

export function observe(eng: VersusEngine, me: number): Observation {
  const { height, width } = eng;
  const self = eng.players[me]!;
  const rival = eng.players[1 - me]!;
  const r = self.r;
  const c = self.c;
  const danger = eng.dangerMap();
  const closing = eng.closingMap();

  const local = new Float32Array(LOCAL_SIZE);
  const hostile: Array<[number, number]> = eng.enemies.filter((e) => e.alive).map((e) => [e.r, e.c]);
  if (rival.alive) hostile.push([rival.r, rival.c]);
  const bombAt = new Map<number, number>();
  for (const b of eng.bombs) bombAt.set(eng.idx(b.r, b.c), b.timer / eng.config.bombFuse);
  const hostileAt = new Set(hostile.map(([hr, hc]) => eng.idx(hr, hc)));
  const rivalAt = rival.alive ? eng.idx(rival.r, rival.c) : -1;

  for (let y = 0; y < VIEW; y++) {
    for (let x = 0; x < VIEW; x++) {
      const mr = r - VIEW_RADIUS + y;
      const mc = c - VIEW_RADIUS + x;
      const at = y * VIEW + x;
      if (!eng.inBounds(mr, mc)) {
        local[at] = 1; // outside the map counts as solid wall
        continue;
      }
      const i = eng.idx(mr, mc);
      local[at] = eng.solid[i]!;
      local[81 + at] = eng.wallHp[i]! > 0 ? 1 : 0;
      local[2 * 81 + at] = bombAt.get(i) ?? 0;
      local[3 * 81 + at] = eng.flames[i]! > 0 ? 1 : 0;
      local[4 * 81 + at] = danger[i]!;
      local[5 * 81 + at] = hostileAt.has(i) ? 1 : 0;
      // plane 6 (door) stays empty: Battle mode has no door
      local[7 * 81 + at] = i === rivalAt ? 1 : 0;
      local[8 * 81 + at] = closing[i]!;
    }
  }

  const target: [number, number] = rival.alive ? [rival.r, rival.c] : [r, c];
  const dist = eng.distanceMap([target]);
  const here = dist[eng.idx(r, c)]!;
  const escape = eng.escapeDistances();
  const canEscape = eng.canEscapeBomb(me);
  const hostileDist = hostile.length ? eng.distanceMap(hostile, 99)[eng.idx(r, c)]! : Infinity;

  const escapeGain: number[] = [];
  const stepGain: number[] = [];
  for (const [, dr, dc] of MOVES) {
    const nr = r + dr;
    const nc = c + dc;
    const inside = eng.inBounds(nr, nc);
    if (!inside || eng.isBlocked(nr, nc)) escapeGain.push(-1);
    else {
      const a = Math.min(escape[eng.idx(r, c)]!, 99);
      const b = Math.min(escape[eng.idx(nr, nc)]!, 99);
      escapeGain.push(clip(a - b, -1, 1));
    }
    const ok = inside && Number.isFinite(dist[eng.idx(nr, nc)]!) && Number.isFinite(here);
    stepGain.push(ok ? clip(here - dist[eng.idx(nr, nc)]!, -1, 1) : 0);
  }

  const rivalEscape = rival.alive ? escape[eng.idx(rival.r, rival.c)]! : 0;
  const sds = eng.config.suddenDeathStart;
  const values = [
    (r / (height - 1)) * 2 - 1,
    (c / (width - 1)) * 2 - 1,
    (target[0] - r) / height,
    (target[1] - c) / width,
    Number.isFinite(here) ? Math.min(here, 60) / 60 : 1,
    eng.bombsLeft(me) > 0 ? 1 : 0,
    (eng.enemiesAlive + (rival.alive ? 1 : 0)) / Math.max(eng.initialEnemies + 1, 1),
    0,
    danger[eng.idx(r, c)]!,
    ...stepGain,
    canEscape ? 1 : 0,
    ...escapeGain,
    hostile.length ? Math.min(hostileDist, 20) / 20 : 1,
    eng.bombsLeft(1 - me) > 0 ? 1 : 0,
    Math.min(rivalEscape, 10) / 10,
    eng.suddenDeath ? 1 : 0,
    clip((sds - eng.steps) / sds, 0, 1),
    closing[eng.idx(r, c)]!,
  ];
  const state = new Float32Array(STATE_SIZE);
  values.forEach((v, i) => {
    state[i] = clip(Math.fround(v), -1, 1);
  });
  return { local, state };
}
