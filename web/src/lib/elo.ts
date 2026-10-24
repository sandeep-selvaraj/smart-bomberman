/**
 * Player ratings on the agents' Elo scale. The agents' ratings are fixed
 * anchors measured offline (web_export.rate_agents, 200 games per pair);
 * a player's rating moves after each verified match against one of them.
 */
export const START_RATING = 1000;
export const PROVISIONAL_GAMES = 10;

/** K is larger while a player is new, so their rating finds its level quickly. */
export const kFactor = (gamesPlayed: number): number => (gamesPlayed < PROVISIONAL_GAMES ? 40 : 24);

export const expected = (rating: number, opponent: number): number => 1 / (1 + 10 ** ((opponent - rating) / 400));

export type Outcome = "win" | "draw" | "loss";
export const SCORE: Record<Outcome, number> = { win: 1, draw: 0.5, loss: 0 };

/** Rating change for one result, rounded to whole points. */
export function delta(rating: number, opponent: number, outcome: Outcome, gamesPlayed: number): number {
  return Math.round(kFactor(gamesPlayed) * (SCORE[outcome] - expected(rating, opponent)));
}

/** What a win, a draw and a loss would be worth right now. */
export function stakes(rating: number, opponent: number, gamesPlayed: number): Record<Outcome, number> {
  return {
    win: delta(rating, opponent, "win", gamesPlayed),
    draw: delta(rating, opponent, "draw", gamesPlayed),
    loss: delta(rating, opponent, "loss", gamesPlayed),
  };
}
