/** Runtime configuration for the API routes. */
export function serverEnv(): Record<string, string | undefined> {
  return typeof process !== "undefined" ? process.env : {};
}

/** The ticket-signing secret. Production must set MATCH_SECRET; local development gets a fixed one. */
export function matchSecret(env = serverEnv()): string | null {
  if (env.MATCH_SECRET) return env.MATCH_SECRET;
  return env.VERCEL_ENV === "production" ? null : "local-development-only";
}

export const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });

export const fail = (status: number, code: string, message: string): Response => json({ code, message }, status);
