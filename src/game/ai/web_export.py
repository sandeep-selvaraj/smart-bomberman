"""Export Battle mode to the web app in ``web/``: maps, policy weights, agent ratings and parity fixtures.

The web app runs a TypeScript port of ``versus_engine`` and the bots, so humans
can play the trained agents in a browser and a server can replay a match to
verify it. Two things keep the port honest:

* ``SeedRng`` is a small seeded generator (sfc32) that both languages implement
  bit for bit. Matches played with it are reproducible from a single seed in
  Python and in TypeScript alike.
* ``export_fixtures`` records matches played here, step by step, with the
  observations and action logits the model saw. The web test suite replays
  them and checks every state, action and observation.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Callable
from pathlib import Path

import numpy as np

from .engine import load_map
from .policies import HeuristicPolicy, ModelPolicy, Policy, RandomPolicy, camper, wanderer
from .versus_engine import VersusConfig, VersusEngine
from .versus_env import versus_observation
from .versus_train import CHAMPION, DEFAULT_MAPS, duel, elo_ratings

ROOT = Path(__file__).resolve().parents[3]
WEB_DATA = ROOT / "web" / "src" / "data"
WEB_PUBLIC = ROOT / "web" / "public"
MASK = 0xFFFFFFFF
WEB_MAPS = ("arena_1", "map_2", "map_3")


# ----------------------------------------------------------------------- rng
class SeedRng:
    """sfc32 seeded through splitmix32, with the slice of numpy's Generator API the engine and bots use.

    ``stream`` derives independent generators from one match seed (engine,
    player 0, player 1), so the order one side draws in never shifts the other.
    """

    def __init__(self, seed: int, stream: int = 0):
        state = (seed * 0x9E3779B9 + stream * 0x85EBCA6B) & MASK
        words = []
        for _ in range(4):
            state = (state + 0x9E3779B9) & MASK
            z = state
            z = ((z ^ (z >> 16)) * 0x85EBCA6B) & MASK
            z = ((z ^ (z >> 13)) * 0xC2B2AE35) & MASK
            words.append(z ^ (z >> 16))
        self.a, self.b, self.c, self.d = words
        for _ in range(12):  # discard the first outputs, as sfc32 implementations usually do
            self.next_u32()

    def next_u32(self) -> int:
        """The next 32 random bits."""
        a, b, c, d = self.a, self.b, self.c, self.d
        t = (a + b + d) & MASK
        d = (d + 1) & MASK
        a = b ^ (b >> 9)
        b = (c + (c << 3)) & MASK
        c = ((c << 21) | (c >> 11)) & MASK
        c = (c + t) & MASK
        self.a, self.b, self.c, self.d = a, b, c, d
        return t

    def random(self) -> float:
        """A float in [0, 1)."""
        return self.next_u32() / 4294967296.0

    def integers(self, n: int) -> int:
        """An integer in [0, n)."""
        return int(self.random() * n)

    def permutation(self, n: int) -> list[int]:
        """A shuffled ``range(n)`` (Fisher-Yates)."""
        items = list(range(n))
        for i in range(n - 1, 0, -1):
            j = self.integers(i + 1)
            items[i], items[j] = items[j], items[i]
        return items


def match_setup(seed: int, maps: tuple[str, ...] = WEB_MAPS) -> tuple[str, bool]:
    """The map and coin flip a match seed decides (stream 3), shared with the web app."""
    rng = SeedRng(seed, 3)
    return maps[rng.integers(len(maps))], rng.random() < 0.5


def seeded(policy: Policy, seed: int, stream: int) -> Policy:
    """Give a scripted bot the match's generator for its seat."""
    if isinstance(policy, (HeuristicPolicy, RandomPolicy)):
        policy.rng = SeedRng(seed, stream)  # type: ignore[assignment]
    return policy


def new_match(seed: int) -> VersusEngine:
    """A match exactly as the web app sets it up from ``seed``."""
    name, swap = match_setup(seed)
    return VersusEngine(load_map(name), VersusConfig(), rng=SeedRng(seed, 0), swap=swap)  # type: ignore[arg-type]


# ------------------------------------------------------------------- exports
def export_maps(out: Path = WEB_DATA) -> Path:
    """Write the web maps as ASCII rows: # solid, b/B breakable (1/2 hits), P/Q starts, E enemy."""
    maps = {}
    for name in WEB_MAPS:
        layout = load_map(name)
        rows = []
        for r in range(layout.shape[0]):
            row = ""
            for c in range(layout.shape[1]):
                cell = (r, c)
                if layout.solid[cell]:
                    row += "#"
                elif layout.wall_hp[cell] > 0:
                    row += "b" if layout.wall_hp[cell] == 1 else "B"
                elif cell == layout.player:
                    row += "P"
                elif cell == layout.rival:
                    row += "Q"
                elif cell in layout.enemies:
                    row += "E"
                else:
                    row += "."
            rows.append(row)
        maps[name] = rows
    out.mkdir(parents=True, exist_ok=True)
    path = out / "maps.json"
    path.write_text(json.dumps(maps, indent=1) + "\n")
    return path


def export_weights(
    model_path: str | Path = CHAMPION, out: Path = WEB_PUBLIC / "models", name: str = "two_fuse"
) -> Path:
    """Write the policy network as little-endian float32 (``<name>.bin``) plus a manifest (``<name>.json``).

    Layers in order: Linear(753, 256), tanh, Linear(256, 256), tanh, Linear(256, 6).
    Each layer stores its weight (out x in, row-major) followed by its bias.
    """
    from stable_baselines3 import PPO

    params = PPO.load(str(model_path), device="cpu").policy.state_dict()
    keys = ["mlp_extractor.policy_net.0", "mlp_extractor.policy_net.2", "action_net"]
    blob, layers, offset = bytearray(), [], 0
    for key in keys:
        weight = params[f"{key}.weight"].numpy().astype("<f4")
        bias = params[f"{key}.bias"].numpy().astype("<f4")
        layers.append({"in": int(weight.shape[1]), "out": int(weight.shape[0]), "offset": offset})
        blob += weight.tobytes() + bias.tobytes()
        offset += weight.size + bias.size
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.bin").write_bytes(bytes(blob))
    manifest = {
        "layers": layers,
        "activation": "tanh",
        "inputs": ["local (9, 9, 9) flattened", "state (24)"],
        "sha256": hashlib.sha256(blob).hexdigest(),
        "source": Path(model_path).name,
    }
    (out / f"{name}.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return out / f"{name}.bin"


def _digest(engine: VersusEngine) -> str:
    """A fingerprint of everything that defines the match state, built the same way in TypeScript."""
    fighters = ";".join(f"{f.cell[0]},{f.cell[1]},{int(f.alive)},{f.killed_by or ''}" for f in engine.players)
    bombs = ";".join(f"{b.cell[0]},{b.cell[1]},{b.timer},{b.owner}" for b in engine.bombs)
    enemies = ";".join(
        f"{e.cell[0]},{e.cell[1]},{e.direction[0]},{e.direction[1]},{int(e.alive)}" for e in engine.enemies
    )
    grids = "|".join(
        "".join(str(int(v)) for v in grid.ravel())
        for grid in (engine.wall_hp, engine.flames, engine.flame_owner + 1, engine.solid)
    )
    text = f"{engine.steps}|{fighters}|{bombs}|{enemies}|{engine.closed}|{grids}"
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def export_fixtures(out: Path = WEB_DATA / "fixtures", model_path: str | Path = CHAMPION, matches: int = 12) -> Path:
    """Record seeded matches for the web parity tests.

    Pairings cycle through the bots and the greedy model so every rule and
    every bot gets exercised. Each step stores both actions and the state
    digest; model seats also store the observation and logits every 10 steps.
    """
    import torch

    model = ModelPolicy(str(model_path), deterministic=True, name="two_fuse")
    pairings = [
        ("two_fuse", "heuristic"),
        ("heuristic", "camper"),
        ("wanderer", "two_fuse"),
        ("random", "heuristic"),
        ("camper", "two_fuse"),
        ("heuristic", "wanderer"),
    ]
    bots: dict[str, Callable[[], Policy]] = {
        "heuristic": HeuristicPolicy,
        "camper": camper,
        "wanderer": wanderer,
        "random": RandomPolicy,
    }
    seeds: list[int] = []
    candidate = 1000
    while len(seeds) < matches:  # cycle the maps so every one is covered
        if match_setup(candidate)[0] == WEB_MAPS[len(seeds) % len(WEB_MAPS)]:
            seeds.append(candidate)
        candidate += 7919
    records = []
    for index, seed in enumerate(seeds):
        names = pairings[index % len(pairings)]
        seats: list[Policy] = [
            model if name == "two_fuse" else seeded(bots[name](), seed, 1 + i) for i, name in enumerate(names)
        ]
        engine = new_match(seed)
        steps, samples = [], []
        while not engine.finished:
            actions = []
            for me, policy in enumerate(seats):
                if policy is model and engine.steps % 10 == 0:
                    obs, _ = versus_observation(engine, me)
                    tensor = model.model.policy.obs_to_tensor(obs)[0]
                    with torch.no_grad():
                        logits = model.model.policy.get_distribution(tensor).distribution.logits[0].numpy()
                    samples.append(
                        {
                            "step": engine.steps,
                            "me": me,
                            "local": np.round(obs["local"].ravel(), 6).tolist(),
                            "state": np.round(obs["state"], 6).tolist(),
                            "logits": np.round(logits, 5).tolist(),
                        }
                    )
                actions.append(policy.act(engine, me))
            engine.step_versus(actions)
            steps.append({"a": actions, "d": _digest(engine)})
        records.append(
            {
                "seed": seed,
                "players": list(names),
                "map": engine.layout.name,
                "swap": engine.swap,
                "winner": engine.winner,
                "steps": steps,
                "samples": samples,
            }
        )
    out.mkdir(parents=True, exist_ok=True)
    path = out / "matches.json"
    path.write_text(json.dumps(records, separators=(",", ":")))
    rng_check = SeedRng(42, 1)
    (out / "rng.json").write_text(
        json.dumps(
            {
                "seed": 42,
                "stream": 1,
                "u32": [rng_check.next_u32() for _ in range(16)],
                "setup": {str(s): list(match_setup(s)) for s in (1, 2, 3, 99, 12345)},
            }
        )
    )
    return path


# ------------------------------------------------------------------- ratings
LADDER = (
    ("wanderer", "Wanderer", "Never bombs. Walks at random and dodges."),
    ("camper", "Camper", "Never bombs. Holds its ground and dodges."),
    ("heuristic", "Heuristic", "A scripted duelist: flees, strikes when close, closes in."),
    ("two_fuse_normal", "Two-Fuse · normal", "The trained agent, sampling its moves."),
    ("two_fuse_hard", "Two-Fuse · hard", "The trained agent, always its best move."),
)


def rate_agents(games: int = 200, out: Path = WEB_DATA) -> Path:
    """Round robin between the ladder's agents; writes their Elo ratings and head-to-head records."""
    factories: dict[str, Callable[[], Policy]] = {
        "wanderer": lambda: wanderer(seed=1),
        "camper": lambda: camper(seed=2),
        "heuristic": lambda: HeuristicPolicy(seed=3),
        "two_fuse_normal": lambda: ModelPolicy(str(CHAMPION), deterministic=False, name="two_fuse_normal"),
        "two_fuse_hard": lambda: ModelPolicy(str(CHAMPION), deterministic=True, name="two_fuse_hard"),
    }
    names = [row[0] for row in LADDER]
    scores: dict[tuple[int, int], tuple[float, int]] = {}
    records = []
    for i, j in itertools.combinations(range(len(names)), 2):
        record = duel(factories[names[i]](), factories[names[j]](), DEFAULT_MAPS, games, seed=77_000)
        scores[(i, j)] = (games * (record["win_rate"] + 0.5 * record["draw_rate"]), games)
        records.append({k: record[k] for k in ("a", "b", "games", "win_rate", "loss_rate", "draw_rate", "mean_steps")})
        print(f"  {names[i]:>16} vs {names[j]:<16} {record['win_rate']:.1%} won", flush=True)
    ratings = elo_ratings(names, scores)
    agents = [{"id": key, "name": label, "about": about, "elo": round(ratings[key])} for key, label, about in LADDER]
    out.mkdir(parents=True, exist_ok=True)
    path = out / "agents.json"
    summary = {"games_per_pair": games, "maps": list(WEB_MAPS), "agents": agents, "records": records}
    path.write_text(json.dumps(summary, indent=1) + "\n")
    return path


def export_training(out: Path = WEB_DATA) -> Path:
    """Copy the measured training curves and tournament rankings the Learn page charts."""
    runs = {}
    for run in ("two_fuse_v1", "two_fuse_v2"):
        metrics = json.loads((ROOT / "runs" / run / "metrics.json").read_text())
        runs[run] = {"history": metrics["history"], "ranking": metrics["ranking"], "champion": metrics["champion"]}
    path = out / "training.json"
    path.write_text(json.dumps(runs, indent=1) + "\n")
    return path


def export_all(fixtures: bool = True) -> None:
    """Maps, weights, training curves and (optionally) the parity fixtures."""
    print(export_maps())
    print(export_weights())
    print(export_training())
    if fixtures:
        print(export_fixtures())


__all__ = [
    "SeedRng",
    "export_all",
    "export_fixtures",
    "export_maps",
    "export_training",
    "export_weights",
    "rate_agents",
]
