/**
 * The player's own record, kept in this browser: handle and its secret key,
 * last known rating, ladder progress and any results still waiting to be
 * submitted. Storage can be unavailable (private windows, blocked storage);
 * everything degrades to an in-memory profile for the session.
 */
import type { AgentId } from "../engine/match";
import type { Outcome } from "./elo";

export interface PendingResult {
  ticket: string;
  agent: AgentId;
  inputs: number[];
  claimed: Outcome;
  playedAt: number;
}

export interface Profile {
  handle: string | null;
  key: string;
  rating: number | null;
  games: number;
  beaten: AgentId[];
  played: AgentId[];
  pending: PendingResult[];
}

const STORAGE_KEY = "smart-bomberman:profile";

const newKey = (): string =>
  Array.from(crypto.getRandomValues(new Uint8Array(24)), (b) => b.toString(16).padStart(2, "0")).join("");

const blank = (): Profile => ({ handle: null, key: newKey(), rating: null, games: 0, beaten: [], played: [], pending: [] });

let memory: Profile | null = null;

export function loadProfile(): Profile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...blank(), ...(JSON.parse(raw) as Partial<Profile>) };
  } catch {
    // storage unavailable: fall through to the session profile
  }
  memory ??= blank();
  return memory;
}

export function saveProfile(profile: Profile): void {
  memory = profile;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  } catch {
    // keep the session copy
  }
}
