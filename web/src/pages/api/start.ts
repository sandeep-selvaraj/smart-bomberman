import type { APIRoute } from "astro";
import { AGENT_IDS, type AgentId } from "../../engine/match";
import { fail, json, matchSecret } from "../../lib/server/env";
import { issueTicket } from "../../lib/server/token";

export const prerender = false;

/** Issue a signed seed for a ranked match against `agent`. */
export const POST: APIRoute = async ({ request }) => {
  const secret = matchSecret();
  if (!secret) return fail(503, "not_configured", "Ranked play is not configured on this server.");
  const body = (await request.json().catch(() => ({}))) as { agent?: string };
  if (!AGENT_IDS.includes(body.agent as AgentId)) return fail(400, "bad_agent", "Unknown opponent.");
  const { ticket, seed } = await issueTicket(secret, body.agent!);
  return json({ ticket, seed });
};
