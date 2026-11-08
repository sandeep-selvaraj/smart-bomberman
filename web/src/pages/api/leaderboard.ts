import type { APIRoute } from "astro";
import { handleId } from "../../lib/handle";
import { json, serverEnv } from "../../lib/server/env";
import { getStore, type PlayerRecord } from "../../lib/server/store";

export const prerender = false;

const visible = ({ keyHash: _hidden, ...player }: PlayerRecord) => player;

/** Players ranked by rating (agents are merged in on the client from their fixed ratings). */
export const GET: APIRoute = async ({ url }) => {
  const offset = Math.max(0, Number(url.searchParams.get("offset")) || 0);
  const limit = Math.min(100, Math.max(1, Number(url.searchParams.get("limit")) || 50));
  const me = url.searchParams.get("me");
  const store = getStore(serverEnv());
  const { total, players } = await store.top(offset, limit);
  let mine = null;
  if (me) {
    const player = await store.getPlayer(handleId(me));
    if (player) mine = { ...visible(player), rank: await store.rankOf(handleId(me)) };
  }
  return json({
    total,
    offset,
    persistent: store.persistent,
    players: players.map((p, i) => ({ ...visible(p), rank: offset + i + 1 })),
    me: mine,
  });
};
