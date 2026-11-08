/**
 * Leaderboard storage. On Vercel it uses Upstash Redis over its REST API
 * (KV_REST_API_URL / KV_REST_API_TOKEN, or UPSTASH_REDIS_REST_URL / _TOKEN);
 * without those it falls back to process memory, which is fine for local
 * development and nothing else.
 */
import type { AgentId } from "../../engine/match";

export interface PlayerRecord {
  handle: string;
  rating: number;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  vs: Partial<Record<AgentId, [number, number, number]>>; // wins, draws, losses
  keyHash: string;
  updated: number;
}

export interface Store {
  readonly persistent: boolean;
  getPlayer(id: string): Promise<PlayerRecord | null>;
  savePlayer(id: string, player: PlayerRecord): Promise<void>;
  /** Marks a ticket used; false when it already was. */
  claimTicket(signature: string, ttlSeconds: number): Promise<boolean>;
  top(offset: number, limit: number): Promise<{ total: number; players: PlayerRecord[] }>;
  rankOf(id: string): Promise<number | null>;
}

const PREFIX = "sb:";

class RedisStore implements Store {
  readonly persistent = true;

  constructor(
    private readonly url: string,
    private readonly token: string,
  ) {}

  private async run<T>(commands: Array<Array<string | number>>): Promise<T[]> {
    const response = await fetch(`${this.url}/pipeline`, {
      method: "POST",
      headers: { Authorization: `Bearer ${this.token}`, "Content-Type": "application/json" },
      body: JSON.stringify(commands),
    });
    if (!response.ok) throw new Error(`leaderboard store answered ${response.status}`);
    const results = (await response.json()) as Array<{ result?: T; error?: string }>;
    return results.map((r) => {
      if (r.error) throw new Error(r.error);
      return r.result as T;
    });
  }

  async getPlayer(id: string): Promise<PlayerRecord | null> {
    const [raw] = await this.run<string | null>([["GET", `${PREFIX}player:${id}`]]);
    return raw ? (JSON.parse(raw) as PlayerRecord) : null;
  }

  async savePlayer(id: string, player: PlayerRecord): Promise<void> {
    await this.run([
      ["SET", `${PREFIX}player:${id}`, JSON.stringify(player)],
      ["ZADD", `${PREFIX}ratings`, player.rating, id],
    ]);
  }

  async claimTicket(signature: string, ttlSeconds: number): Promise<boolean> {
    const [ok] = await this.run<string | null>([["SET", `${PREFIX}used:${signature}`, "1", "NX", "EX", ttlSeconds]]);
    return ok === "OK";
  }

  async top(offset: number, limit: number): Promise<{ total: number; players: PlayerRecord[] }> {
    const [ids, total] = await this.run<unknown>([
      ["ZRANGE", `${PREFIX}ratings`, offset, offset + limit - 1, "REV"],
      ["ZCARD", `${PREFIX}ratings`],
    ]);
    const list = (ids as string[]) ?? [];
    if (!list.length) return { total: Number(total) || 0, players: [] };
    const [raws] = await this.run<Array<string | null>>([["MGET", ...list.map((id) => `${PREFIX}player:${id}`)]]);
    const players = (raws ?? []).filter((r): r is string => !!r).map((r) => JSON.parse(r) as PlayerRecord);
    return { total: Number(total) || 0, players };
  }

  async rankOf(id: string): Promise<number | null> {
    const [rank] = await this.run<number | null>([["ZREVRANK", `${PREFIX}ratings`, id]]);
    return rank === null || rank === undefined ? null : Number(rank) + 1;
  }
}

class MemoryStore implements Store {
  readonly persistent = false;
  private players = new Map<string, PlayerRecord>();
  private used = new Map<string, number>();

  async getPlayer(id: string) {
    return this.players.get(id) ?? null;
  }

  async savePlayer(id: string, player: PlayerRecord) {
    this.players.set(id, player);
  }

  async claimTicket(signature: string, ttlSeconds: number) {
    const now = Date.now();
    if ((this.used.get(signature) ?? 0) > now) return false;
    this.used.set(signature, now + ttlSeconds * 1000);
    return true;
  }

  private ranked(): Array<[string, PlayerRecord]> {
    return [...this.players.entries()].sort((a, b) => b[1].rating - a[1].rating || a[1].updated - b[1].updated);
  }

  async top(offset: number, limit: number) {
    const ranked = this.ranked();
    return { total: ranked.length, players: ranked.slice(offset, offset + limit).map(([, p]) => p) };
  }

  async rankOf(id: string) {
    const index = this.ranked().findIndex(([key]) => key === id);
    return index < 0 ? null : index + 1;
  }
}

let memory: MemoryStore | null = null;

export function getStore(env: Record<string, string | undefined>): Store {
  const url = env.KV_REST_API_URL ?? env.UPSTASH_REDIS_REST_URL;
  const token = env.KV_REST_API_TOKEN ?? env.UPSTASH_REDIS_REST_TOKEN;
  if (url && token) return new RedisStore(url.replace(/\/$/, ""), token);
  memory ??= new MemoryStore();
  return memory;
}
