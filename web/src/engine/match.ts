/**
 * Everything a match needs from its seed: map, coin flip, engine and the
 * opponent's seat. The human is always player 0 and the agent player 1; the
 * coin flip decides who starts in which corner. Shared by the browser game
 * and the server-side replay, so both build the identical match.
 */
import maps from "../data/maps.json";
import { parseLayout, VersusEngine, type Action, type Layout } from "./engine";
import type { PolicyNet } from "./mlp";
import { camper, heuristic, ModelPolicy, wanderer, type Policy } from "./policies";
import { SeedRng, STREAM } from "./rng";

export const MAP_NAMES = ["arena_1", "map_2", "map_3"] as const;
export type MapName = (typeof MAP_NAMES)[number];

export const AGENT_IDS = ["wanderer", "camper", "heuristic", "two_fuse_normal", "two_fuse_hard"] as const;
export type AgentId = (typeof AGENT_IDS)[number];

const layouts = new Map<string, Layout>();

export function layoutFor(name: MapName): Layout {
  if (!layouts.has(name)) layouts.set(name, parseLayout(name, (maps as Record<string, string[]>)[name]!));
  return layouts.get(name)!;
}

/** The map and coin flip a seed decides (stream 3), like web_export.match_setup. */
export function matchSetup(seed: number): { map: MapName; swap: boolean } {
  const rng = new SeedRng(seed, STREAM.setup);
  const map = MAP_NAMES[rng.integers(MAP_NAMES.length)]!;
  return { map, swap: rng.random() < 0.5 };
}

export function newEngine(seed: number): VersusEngine {
  const { map, swap } = matchSetup(seed);
  return new VersusEngine(layoutFor(map), new SeedRng(seed, STREAM.engine), swap);
}

export const needsNet = (agent: AgentId): boolean => agent.startsWith("two_fuse");

/** The agent in seat `seat` (its random stream is seat + 1). */
export function opponentFor(agent: AgentId, seed: number, net: PolicyNet | null, seat = 1): Policy {
  const rng = new SeedRng(seed, seat === 0 ? STREAM.seat0 : STREAM.seat1);
  switch (agent) {
    case "wanderer":
      return wanderer(rng);
    case "camper":
      return camper(rng);
    case "heuristic":
      return heuristic(rng);
    case "two_fuse_normal":
    case "two_fuse_hard":
      if (!net) throw new Error("Two-Fuse needs its network loaded");
      return new ModelPolicy(agent, net, agent === "two_fuse_hard", rng);
  }
}

export interface MatchResult {
  finished: boolean;
  winner: number | null;
  steps: number;
  killedBy: [string | null, string | null];
}

/** Replay a human input log against an agent from the seed; the server's verification. */
export function replay(agent: AgentId, seed: number, inputs: readonly number[], net: PolicyNet | null): MatchResult {
  const engine = newEngine(seed);
  const opponent = opponentFor(agent, seed, net);
  for (const input of inputs) {
    if (engine.finished) break;
    if (!Number.isInteger(input) || input < 0 || input > 5) throw new Error("invalid input in log");
    engine.step([input as Action, opponent.act(engine, 1)]);
  }
  return {
    finished: engine.finished,
    winner: engine.finished ? engine.winner : null,
    steps: engine.steps,
    killedBy: [engine.players[0].killedBy, engine.players[1].killedBy],
  };
}
