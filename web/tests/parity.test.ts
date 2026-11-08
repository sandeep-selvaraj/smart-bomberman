/**
 * Parity with the Python reference (src/game/ai): the fixtures are matches
 * recorded by web_export.export_fixtures. Every step must reproduce the
 * recorded actions and state, and the agent's observations and logits must
 * match what the trained network saw in Python.
 */
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { type Action } from "../src/engine/engine";
import { argmax, PolicyNet, type Manifest } from "../src/engine/mlp";
import { matchSetup, newEngine } from "../src/engine/match";
import { observe } from "../src/engine/observation";
import { camper, heuristic, ModelPolicy, RandomPolicy, wanderer, type Policy } from "../src/engine/policies";
import { SeedRng, STREAM } from "../src/engine/rng";
import matches from "../src/data/fixtures/matches.json";
import rngFixture from "../src/data/fixtures/rng.json";

const manifest = JSON.parse(readFileSync("public/models/two_fuse.json", "utf8")) as Manifest;
const blob = readFileSync("public/models/two_fuse.bin");
const net = new PolicyNet(manifest, new Float32Array(blob.buffer, blob.byteOffset, blob.byteLength / 4));

interface Sample {
  step: number;
  me: number;
  local: number[];
  state: number[];
  logits: number[];
}
interface Record {
  seed: number;
  players: string[];
  map: string;
  swap: boolean;
  winner: number | null;
  steps: Array<{ a: number[]; d: string }>;
  samples: Sample[];
}

const logSoftmax = (x: ArrayLike<number>): number[] => {
  const values = Array.from(x);
  const peak = Math.max(...values);
  const norm = peak + Math.log(values.reduce((a, v) => a + Math.exp(v - peak), 0));
  return values.map((v) => v - norm);
};

const sha = (text: string): string => createHash("sha1").update(text).digest("hex").slice(0, 16);

function seat(name: string, seed: number, index: number): Policy {
  const rng = new SeedRng(seed, index === 0 ? STREAM.seat0 : STREAM.seat1);
  if (name === "two_fuse") return new ModelPolicy("two_fuse_hard", net, true, rng);
  if (name === "random") return new RandomPolicy(rng);
  return { heuristic, camper, wanderer }[name as "heuristic"](rng);
}

describe("SeedRng", () => {
  it("matches the Python generator bit for bit", () => {
    const rng = new SeedRng(rngFixture.seed, rngFixture.stream);
    expect(Array.from({ length: 16 }, () => rng.nextU32())).toEqual(rngFixture.u32);
  });

  it("picks the same map and coin flip from a seed", () => {
    for (const [seed, [map, swap]] of Object.entries(rngFixture.setup)) {
      expect(matchSetup(Number(seed))).toEqual({ map, swap });
    }
  });
});

describe.each(matches as Record[])("match $seed: $players.0 vs $players.1 on $map", (record) => {
  it("replays every step, state and action exactly", () => {
    const engine = newEngine(record.seed);
    expect(engine.layout.name).toBe(record.map);
    expect(engine.swap).toBe(record.swap);
    const seats = record.players.map((name, i) => seat(name, record.seed, i));
    const modelMisses: number[] = [];
    record.steps.forEach(({ a, d }, step) => {
      const chosen = seats.map((p, me) => p.act(engine, me));
      chosen.forEach((action, me) => {
        if (action === a[me]) return;
        if (record.players[me] === "two_fuse") modelMisses.push(step);
        else throw new Error(`step ${step}: ${record.players[me]} chose ${action}, Python chose ${a[me]}`);
      });
      engine.step([a[0] as Action, a[1] as Action]); // always follow the recorded actions
      expect(sha(engine.digestText()), `state after step ${step + 1}`).toBe(d);
    });
    expect(engine.finished).toBe(true);
    expect(engine.winner).toBe(record.winner);
    expect(modelMisses).toEqual([]);
  });

  it("builds the agent's observations and logits like Python", () => {
    if (!record.samples.length) return;
    const engine = newEngine(record.seed);
    const seats = record.players.map((name, i) => seat(name, record.seed, i));
    const samples = new Map(record.samples.map((s) => [`${s.step}:${s.me}`, s]));
    record.steps.forEach(({ a }) => {
      for (let me = 0; me < 2; me++) {
        const sample = samples.get(`${engine.steps}:${me}`);
        if (!sample) continue;
        const obs = observe(engine, me);
        Array.from(obs.local).forEach((v, i) => expect(v).toBeCloseTo(sample.local[i]!, 5));
        Array.from(obs.state).forEach((v, i) => expect(v, `state[${i}] at step ${sample.step}`).toBeCloseTo(sample.state[i]!, 5));
        const logits = logSoftmax(net.logits(obs)); // torch's Categorical stores normalized log-probabilities
        logits.forEach((v, i) => expect(v).toBeCloseTo(sample.logits[i]!, 3));
        expect(argmax(logits)).toBe(argmax(sample.logits));
      }
      seats.forEach((p, me) => p.act(engine, me));
      engine.step([a[0] as Action, a[1] as Action]);
    });
  });
});
