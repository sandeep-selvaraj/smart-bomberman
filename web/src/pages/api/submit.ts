import type { APIRoute } from "astro";
import { AGENT_IDS, replay, needsNet, type AgentId } from "../../engine/match";
import { AGENT_BY_ID } from "../../lib/agents";
import { delta, START_RATING, type Outcome } from "../../lib/elo";
import { handleId, handleProblem } from "../../lib/handle";
import { fail, json, matchSecret, serverEnv } from "../../lib/server/env";
import { serverNet } from "../../lib/server/net";
import { getStore, type PlayerRecord } from "../../lib/server/store";
import { readTicket, sha256, TICKET_TTL_MS } from "../../lib/server/token";

export const prerender = false;

interface Body {
  ticket?: string;
  handle?: string;
  key?: string;
  inputs?: unknown;
  claimed?: Outcome;
}

/** Verify a match by replaying its input log from the signed seed, then update the player's rating. */
export const POST: APIRoute = async ({ request }) => {
  const secret = matchSecret();
  if (!secret) return fail(503, "not_configured", "Ranked play is not configured on this server.");
  const body = (await request.json().catch(() => ({}))) as Body;

  const problem = handleProblem(body.handle ?? "");
  if (problem) return fail(400, "bad_handle", problem);
  if (typeof body.key !== "string" || body.key.length < 16 || body.key.length > 128)
    return fail(400, "bad_key", "Missing player key.");
  const inputs = body.inputs;
  if (!Array.isArray(inputs) || inputs.length > 1000 || !inputs.every((a) => Number.isInteger(a) && a >= 0 && a <= 5))
    return fail(400, "bad_inputs", "The match log is malformed.");

  const ticket = await readTicket(secret, body.ticket ?? "");
  if (!ticket || !AGENT_IDS.includes(ticket.agent as AgentId))
    return fail(400, "bad_ticket", "This match ticket is invalid or more than two hours old.");
  const agentId = ticket.agent as AgentId;

  const net = needsNet(agentId) ? await serverNet(new URL(request.url).origin) : null;
  const result = replay(agentId, ticket.seed, inputs as number[], net);
  if (!result.finished) return fail(422, "unfinished", "The match log stops before the match ends.");
  const outcome: Outcome = result.winner === 0 ? "win" : result.winner === 1 ? "loss" : "draw";
  if (body.claimed && body.claimed !== outcome)
    return fail(422, "disagreed", `The replay ended in a ${outcome}, not a ${body.claimed}. Nothing was recorded.`);

  const store = getStore(serverEnv());
  const id = handleId(body.handle!);
  const keyHash = await sha256(body.key);
  const existing = await store.getPlayer(id);
  if (existing && existing.keyHash !== keyHash)
    return fail(403, "handle_taken", "Someone else already plays under that handle.");
  if (!(await store.claimTicket(ticket.signature, Math.ceil(TICKET_TTL_MS / 1000))))
    return fail(409, "used", "This match was already recorded.");

  const player: PlayerRecord = existing ?? {
    handle: body.handle!.trim(),
    rating: START_RATING,
    games: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    vs: {},
    keyHash,
    updated: 0,
  };
  const change = delta(player.rating, AGENT_BY_ID[agentId].elo, outcome, player.games);
  const record = player.vs[agentId] ?? [0, 0, 0];
  record[outcome === "win" ? 0 : outcome === "draw" ? 1 : 2] += 1;
  const updated: PlayerRecord = {
    ...player,
    rating: player.rating + change,
    games: player.games + 1,
    wins: player.wins + Number(outcome === "win"),
    draws: player.draws + Number(outcome === "draw"),
    losses: player.losses + Number(outcome === "loss"),
    vs: { ...player.vs, [agentId]: record },
    updated: Date.now(),
  };
  await store.savePlayer(id, updated);
  const { keyHash: _hidden, ...publicPlayer } = updated;
  return json({
    outcome,
    steps: result.steps,
    delta: change,
    player: publicPlayer,
    rank: await store.rankOf(id),
    persistent: store.persistent,
  });
};
