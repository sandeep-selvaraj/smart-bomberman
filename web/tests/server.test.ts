/** The ranked-play pieces: Elo, tickets, handles and replay verification. */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { BOMB, NOOP } from "../src/engine/engine";
import { newEngine, opponentFor, replay } from "../src/engine/match";
import { PolicyNet, type Manifest } from "../src/engine/mlp";
import { delta, expected, kFactor, stakes } from "../src/lib/elo";
import { handleProblem } from "../src/lib/handle";
import { getStore } from "../src/lib/server/store";
import { issueTicket, readTicket } from "../src/lib/server/token";

const blob = readFileSync("public/models/two_fuse.bin");
const net = new PolicyNet(
  JSON.parse(readFileSync("public/models/two_fuse.json", "utf8")) as Manifest,
  new Float32Array(blob.buffer, blob.byteOffset, blob.byteLength / 4),
);

describe("elo", () => {
  it("is symmetric and zero-sum in expectation", () => {
    expect(expected(1000, 1000)).toBeCloseTo(0.5);
    expect(expected(1100, 1000) + expected(1000, 1100)).toBeCloseTo(1);
  });

  it("pays more for beating a stronger agent", () => {
    expect(delta(1000, 1118, "win", 20)).toBeGreaterThan(delta(1000, 903, "win", 20));
    expect(delta(1000, 903, "loss", 20)).toBeLessThan(delta(1000, 1118, "loss", 20));
  });

  it("moves new players faster", () => {
    expect(kFactor(0)).toBeGreaterThan(kFactor(50));
    const s = stakes(1000, 1000, 0);
    expect(s.win).toBe(-s.loss);
    expect(s.draw).toBe(0);
  });
});

describe("tickets", () => {
  it("round-trips and rejects tampering or the wrong secret", async () => {
    const { ticket, seed } = await issueTicket("secret", "camper");
    expect((await readTicket("secret", ticket))?.seed).toBe(seed);
    expect(await readTicket("other", ticket)).toBeNull();
    const [body, sig] = ticket.split(".");
    expect(await readTicket("secret", `${body}x.${sig}`)).toBeNull();
  });

  it("can be claimed only once", async () => {
    const store = getStore({});
    expect(await store.claimTicket("sig-1", 60)).toBe(true);
    expect(await store.claimTicket("sig-1", 60)).toBe(false);
  });
});

describe("handles", () => {
  it.each([
    ["Sandeep", null],
    ["a", "short"],
    ["Two-Fuse fan", "agent"],
    ["<script>", "Letters"],
  ])("%s", (handle, problem) => {
    const result = handleProblem(handle);
    if (problem === null) expect(result).toBeNull();
    else expect(result).toContain(problem === "short" ? "at least" : problem === "agent" ? "agent" : problem);
  });
});

describe("replay verification", () => {
  it("reproduces a live match from its seed and input log", () => {
    for (const agent of ["heuristic", "two_fuse_hard", "two_fuse_normal"] as const) {
      const seed = 4242;
      const engine = newEngine(seed);
      const opponent = opponentFor(agent, seed, net);
      const inputs: number[] = [];
      let k = 0;
      while (!engine.finished) {
        const mine = [NOOP, 4, 4, 2, BOMB, 3, 3, 1][k++ % 8]!;
        engine.step([mine as 0, opponent.act(engine, 1)]);
        inputs.push(mine);
      }
      const result = replay(agent, seed, inputs, net);
      expect(result.finished).toBe(true);
      expect(result.winner).toBe(engine.winner);
      expect(result.steps).toBe(engine.steps);
    }
  });

  it("does not finish a truncated log", () => {
    expect(replay("camper", 7, [NOOP, NOOP, NOOP], null).finished).toBe(false);
  });

  it("rejects inputs outside the action set", () => {
    expect(() => replay("camper", 7, [9], null)).toThrow();
  });
});
