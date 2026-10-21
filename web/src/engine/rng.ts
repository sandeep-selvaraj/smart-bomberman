/**
 * sfc32 seeded through splitmix32: the same generator as `SeedRng` in
 * src/game/ai/web_export.py, bit for bit. A match is reproducible from its
 * seed in both languages, which is what lets the server replay a game.
 */
const mul = (a: number, b: number): number => Math.imul(a, b) >>> 0;

export class SeedRng {
  private a: number;
  private b: number;
  private c: number;
  private d: number;

  constructor(seed: number, stream = 0) {
    let state = (mul(seed >>> 0, 0x9e3779b9) + mul(stream >>> 0, 0x85ebca6b)) >>> 0;
    const words: number[] = [];
    for (let i = 0; i < 4; i++) {
      state = (state + 0x9e3779b9) >>> 0;
      let z = state;
      z = mul(z ^ (z >>> 16), 0x85ebca6b);
      z = mul(z ^ (z >>> 13), 0xc2b2ae35);
      words.push((z ^ (z >>> 16)) >>> 0);
    }
    [this.a, this.b, this.c, this.d] = words as [number, number, number, number];
    for (let i = 0; i < 12; i++) this.nextU32();
  }

  /** The next 32 random bits. */
  nextU32(): number {
    const t = (this.a + this.b + this.d) >>> 0;
    this.d = (this.d + 1) >>> 0;
    this.a = (this.b ^ (this.b >>> 9)) >>> 0;
    this.b = (this.c + (this.c << 3)) >>> 0;
    this.c = ((this.c << 21) | (this.c >>> 11)) >>> 0;
    this.c = (this.c + t) >>> 0;
    return t;
  }

  /** A float in [0, 1). */
  random(): number {
    return this.nextU32() / 4294967296;
  }

  /** An integer in [0, n). */
  integers(n: number): number {
    return Math.floor(this.random() * n);
  }

  /** A shuffled [0, n) (Fisher-Yates). */
  permutation(n: number): number[] {
    const items = Array.from({ length: n }, (_, i) => i);
    for (let i = n - 1; i > 0; i--) {
      const j = this.integers(i + 1);
      [items[i], items[j]] = [items[j]!, items[i]!];
    }
    return items;
  }
}

/** Streams a match seed is split into, matching the Python side. */
export const STREAM = { engine: 0, seat0: 1, seat1: 2, setup: 3 } as const;
