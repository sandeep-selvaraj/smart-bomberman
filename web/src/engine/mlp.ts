/**
 * The agent's policy network in plain TypeScript: Linear(753, 256), tanh,
 * Linear(256, 256), tanh, Linear(256, 6), with weights exported by
 * web_export.export_weights. Plain arithmetic (no WebGL, no WASM runtime)
 * gives the same logits in every browser and on the server, which is what
 * makes a replayed match come out the same.
 */
import { LOCAL_SIZE, STATE_SIZE, type Observation } from "./observation";

export interface LayerSpec {
  in: number;
  out: number;
  offset: number;
}

export interface Manifest {
  layers: LayerSpec[];
  sha256: string;
  source: string;
}

export class PolicyNet {
  private readonly weights: Float32Array;
  private readonly layers: LayerSpec[];

  constructor(manifest: Manifest, weights: Float32Array) {
    this.layers = manifest.layers;
    this.weights = weights;
    if (this.layers[0]!.in !== LOCAL_SIZE + STATE_SIZE) throw new Error("model input size does not match the observation");
  }

  /** Action logits for an observation. */
  logits(obs: Observation): Float64Array {
    let x = new Float64Array(LOCAL_SIZE + STATE_SIZE);
    x.set(obs.local, 0);
    x.set(obs.state, LOCAL_SIZE);
    this.layers.forEach((layer, k) => {
      const out = new Float64Array(layer.out);
      const w = this.weights;
      const bias = layer.offset + layer.in * layer.out;
      for (let o = 0; o < layer.out; o++) {
        let sum = w[bias + o]!;
        const row = layer.offset + o * layer.in;
        for (let i = 0; i < layer.in; i++) sum += w[row + i]! * x[i]!;
        out[o] = k < this.layers.length - 1 ? Math.tanh(sum) : sum;
      }
      x = out;
    });
    return x;
  }
}

/** Load the exported network from `base` (e.g. "/models/two_fuse"). */
export async function loadPolicyNet(base: string, fetcher: typeof fetch = fetch): Promise<PolicyNet> {
  const [manifest, buffer] = await Promise.all([
    fetcher(`${base}.json`).then((r) => r.json() as Promise<Manifest>),
    fetcher(`${base}.bin`).then((r) => r.arrayBuffer()),
  ]);
  return new PolicyNet(manifest, new Float32Array(buffer));
}

/** Index of the largest logit (first on ties, like torch.argmax). */
export function argmax(values: ArrayLike<number>): number {
  let best = 0;
  for (let i = 1; i < values.length; i++) if (values[i]! > values[best]!) best = i;
  return best;
}
