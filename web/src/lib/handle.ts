/** Leaderboard handles: shared by the client form and the server's check. */
export const HANDLE_MIN = 2;
export const HANDLE_MAX = 20;
const RESERVED = ["two-fuse", "twofuse", "two_fuse", "camper", "wanderer", "heuristic", "random", "admin"];

/** An error message for an unusable handle, or null when it is fine. */
export function handleProblem(raw: string): string | null {
  const handle = raw.trim();
  if (handle.length < HANDLE_MIN) return `Use at least ${HANDLE_MIN} characters.`;
  if (handle.length > HANDLE_MAX) return `Use at most ${HANDLE_MAX} characters.`;
  if (!/^[\p{L}\p{N}][\p{L}\p{N} _.-]*$/u.test(handle)) return "Letters, numbers, spaces, dots, dashes and underscores only.";
  if (RESERVED.some((name) => handle.toLowerCase().replace(/[\s.]/g, "").startsWith(name)))
    return "That name belongs to an agent. Pick another.";
  return null;
}

export const handleId = (handle: string): string => handle.trim().toLowerCase();
