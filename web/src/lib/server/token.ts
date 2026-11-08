/**
 * Match tickets. /api/start hands out a random seed signed with a server
 * secret; /api/submit only accepts a result for a seed this server issued,
 * once, within two hours. Players cannot pick a seed they have rehearsed.
 */
const encoder = new TextEncoder();
export const TICKET_TTL_MS = 2 * 60 * 60 * 1000;

export interface Ticket {
  seed: number;
  agent: string;
  issued: number;
}

const b64url = (bytes: Uint8Array): string =>
  btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const fromB64url = (text: string): Uint8Array =>
  Uint8Array.from(atob(text.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));

async function hmac(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, [
    "sign",
  ]);
  return b64url(new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(message))));
}

export async function issueTicket(secret: string, agent: string): Promise<{ ticket: string; seed: number }> {
  const seed = crypto.getRandomValues(new Uint32Array(1))[0]!;
  const body = b64url(encoder.encode(JSON.stringify({ seed, agent, issued: Date.now() } satisfies Ticket)));
  return { ticket: `${body}.${await hmac(secret, body)}`, seed };
}

/** The ticket's contents if the signature holds and it has not expired; null otherwise. */
export async function readTicket(secret: string, ticket: string): Promise<(Ticket & { signature: string }) | null> {
  const [body, signature] = ticket.split(".");
  if (!body || !signature || (await hmac(secret, body)) !== signature) return null;
  try {
    const parsed = JSON.parse(new TextDecoder().decode(fromB64url(body))) as Ticket;
    if (Date.now() - parsed.issued > TICKET_TTL_MS) return null;
    return { ...parsed, signature };
  } catch {
    return null;
  }
}

export async function sha256(text: string): Promise<string> {
  return b64url(new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(text))));
}
