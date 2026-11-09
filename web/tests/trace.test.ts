/**
 * The network view's tracing: activations must end in the same logits the
 * agent plays from, and a unit's traced terms must be real parts of its sum.
 */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { PolicyNet, trace, type Manifest } from "../src/engine/mlp";
import { newEngine } from "../src/engine/match";
import { observe } from "../src/engine/observation";

const manifest = JSON.parse(readFileSync("public/models/two_fuse.json", "utf8")) as Manifest;
const blob = readFileSync("public/models/two_fuse.bin");
const net = new PolicyNet(manifest, new Float32Array(blob.buffer, blob.byteOffset, blob.byteLength / 4));
const acts = net.activations(observe(newEngine(222732), 0));

describe("network tracing", () => {
  it("exposes every layer and ends in the logits", () => {
    expect(acts.map((a) => a.length)).toEqual([753, 256, 256, 6]);
    expect(Array.from(acts[3]!)).toEqual(Array.from(net.logits(observe(newEngine(222732), 0))));
  });

  it("weight × value terms plus the bias add up to the logit", () => {
    const w = net.weightsInto(2, 5);
    let sum = net.bias(2, 5);
    for (let i = 0; i < w.length; i++) sum += w[i]! * acts[2]![i]!;
    expect(sum).toBeCloseTo(acts[3]![5]!, 9);
  });

  it("follows the strongest senders back from an action", () => {
    const [toLayer1, toLayer2, toAction] = trace(net, acts, 2);
    expect(toAction).toHaveLength(8);
    expect(toAction!.every((l) => l.to === 2)).toBe(true);
    const w = net.weightsInto(2, 2);
    const all = Array.from(acts[2]!, (v, i) => Math.abs(w[i]! * v)).sort((a, b) => b - a);
    expect(Math.abs(toAction![0]!.value)).toBeCloseTo(all[0]!, 12);
    const layer2 = new Set(toAction!.map((l) => l.from));
    expect(toLayer2!.every((l) => layer2.has(l.to))).toBe(true);
    const layer1 = new Set(toLayer2!.map((l) => l.from));
    expect(toLayer1!.every((l) => layer1.has(l.to))).toBe(true);
  });
});
