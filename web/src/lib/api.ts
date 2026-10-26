/** Calls to the ranked-play API. Every call can fail; callers fall back to practice or a saved result. */
import type { AgentId } from "../engine/match";
import type { Outcome } from "./elo";

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  } catch {
    throw new ApiError("offline", "The server could not be reached.", 0);
  }
  const body = (await response.json().catch(() => ({}))) as T & { code?: string; message?: string };
  if (!response.ok) throw new ApiError(body.code ?? "error", body.message ?? `The server answered ${response.status}.`, response.status);
  return body;
}

export const startMatch = (agent: AgentId) =>
  call<{ ticket: string; seed: number }>("/api/start", { method: "POST", body: JSON.stringify({ agent }) });

export interface PublicPlayer {
  handle: string;
  rating: number;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  vs: Partial<Record<AgentId, [number, number, number]>>;
  updated: number;
  rank?: number | null;
}

export interface SubmitResult {
  outcome: Outcome;
  steps: number;
  delta: number;
  player: PublicPlayer;
  rank: number | null;
  persistent: boolean;
}

export const submitMatch = (body: { ticket: string; handle: string; key: string; inputs: number[]; claimed: Outcome }) =>
  call<SubmitResult>("/api/submit", { method: "POST", body: JSON.stringify(body) });

export interface Leaderboard {
  total: number;
  offset: number;
  persistent: boolean;
  players: Array<PublicPlayer & { rank: number }>;
  me: (PublicPlayer & { rank: number | null }) | null;
}

export const fetchLeaderboard = (offset = 0, limit = 50, me?: string | null) =>
  call<Leaderboard>(`/api/leaderboard?offset=${offset}&limit=${limit}${me ? `&me=${encodeURIComponent(me)}` : ""}`);
