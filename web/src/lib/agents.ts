/** The ladder's agents with their measured ratings (src/data/agents.json, written by web_export.rate_agents). */
import data from "../data/agents.json";
import type { CharacterKey } from "../art/sprites";
import type { AgentId } from "../engine/match";

export interface Agent {
  id: AgentId;
  name: string;
  about: string;
  elo: number;
}

/** Ordered by rating: the ladder runs from the lowest-rated agent to Two-Fuse on hard. */
export const AGENTS: Agent[] = (data.agents as Agent[]).slice().sort((a, b) => a.elo - b.elo);
export const AGENT_BY_ID = Object.fromEntries(AGENTS.map((a) => [a.id, a])) as Record<AgentId, Agent>;
export const RATING_GAMES = data.games_per_pair;
export const RATING_RECORDS = data.records;

export const isTwoFuse = (id: AgentId): boolean => id.startsWith("two_fuse");
/** The name as printed on a slip: "Two-Fuse" with its level as a separate word. */
export const shortName = (id: AgentId): string => (isTwoFuse(id) ? "Two-Fuse" : AGENT_BY_ID[id].name);
export const level = (id: AgentId): string | null =>
  id === "two_fuse_hard" ? "hard" : id === "two_fuse_normal" ? "normal" : null;

/** Each agent's character on the board and in portraits (their ids double as character keys). */
export const characterOf = (id: AgentId): CharacterKey => id;
