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
    return this.activations(obs).at(-1)!;
  }

  /** The incoming weights of one unit: `layer` 0 is the first Linear. */
  weightsInto(layer: number, unit: number): Float32Array {
    const spec = this.layers[layer]!;
    const row = spec.offset + unit * spec.in;
    return this.weights.subarray(row, row + spec.in);
  }

  /** The bias of one unit. */
  bias(layer: number, unit: number): number {
    const spec = this.layers[layer]!;
    return this.weights[spec.offset + spec.in * spec.out + unit]!;
  }

  /**
   * Every layer's values for an observation: the 753 inputs, each hidden
   * layer after tanh, then the action logits.
   */
  activations(obs: Observation): Float64Array[] {
    let x = new Float64Array(LOCAL_SIZE + STATE_SIZE);
    x.set(obs.local, 0);
    x.set(obs.state, LOCAL_SIZE);
    const all = [x];
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
      all.push(out);
    });
    return all;
  }
}

/** One traced connection: unit `from` of a layer feeding unit `to` of the next. */
export interface Link {
  from: number;
  to: number;
  /** weight × the sending unit's value: what it adds to the receiver before tanh. */
  value: number;
}

function strongest(net: PolicyNet, layer: number, unit: number, input: ArrayLike<number>, keep: number): Link[] {
  const w = net.weightsInto(layer, unit);
  const links: Link[] = [];
  for (let i = 0; i < w.length; i++) {
    const value = w[i]! * input[i]!;
    if (value !== 0) links.push({ from: i, to: unit, value });
  }
  return links.sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, keep);
}

/**
 * Walk back from one action: the last-layer units that add most to (or take
 * most from) its logit, the units that drive those, and the inputs that
 * drive those. `keep` is how many senders to follow per receiver at each
 * stage, outputs first. Returns the links per stage, inputs first.
 */
export function trace(net: PolicyNet, acts: Float64Array[], action: number, keep: number[] = [8, 3, 3]): Link[][] {
  const stages: Link[][] = [];
  let receivers = [action];
  for (let layer = acts.length - 2; layer >= 0; layer--) {
    const width = keep[acts.length - 2 - layer] ?? 3;
    const links = receivers.flatMap((unit) => strongest(net, layer, unit, acts[layer]!, width));
    stages.unshift(links);
    receivers = [...new Set(links.map((l) => l.from))];
  }
  return stages;
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
