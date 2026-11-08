/** Two-Fuse's network on the server, fetched once per instance from the deployment's own static files. */
import { loadPolicyNet, type PolicyNet } from "../../engine/mlp";

let cached: Promise<PolicyNet> | null = null;

export function serverNet(origin: string): Promise<PolicyNet> {
  cached ??= loadPolicyNet(new URL("/models/two_fuse", origin).toString()).catch((error) => {
    cached = null;
    throw error;
  });
  return cached;
}
