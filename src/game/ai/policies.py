"""Who can sit in a Battle-mode seat: scripted bots, trained models and the self-play league."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from .engine import BOMB, MOVES, NOOP
from .versus_engine import VersusEngine
from .versus_env import versus_observation


class Policy(Protocol):
    """Anything that picks an action for player ``me`` of a match."""

    name: str

    def act(self, engine: VersusEngine, me: int) -> int:
        """Pick the next action."""
        ...


class RandomPolicy:
    """Uniformly random actions: the floor every ranking is measured against."""

    def __init__(self, seed: int | None = None):
        self.name = "random"
        self.rng = np.random.default_rng(seed)

    def act(self, engine: VersusEngine, me: int) -> int:
        return int(self.rng.integers(6))


class HeuristicPolicy:
    """A scripted duelist: flee danger, bomb the opponent when it is close, otherwise close in.

    It is Two-Fuse's "easy" mode and a sparring partner during training.
    ``wander`` is the chance of a random safe move, which keeps it from being
    perfectly predictable.
    """

    def __init__(self, wander: float = 0.1, seed: int | None = None):
        self.name = "heuristic"
        self.wander = wander
        self.rng = np.random.default_rng(seed)

    def act(self, engine: VersusEngine, me: int) -> int:
        view = _BotView(engine, me)
        for rule in (self._flee, self._strike, self._back_off, self._wander, self._advance):
            action = rule(view)
            if action is not None:
                return action
        return NOOP

    def _flee(self, v: _BotView) -> int | None:
        """Standing where a blast or a closing wall will reach: take the quickest way out."""
        if v.escape[v.cell] == 0:
            return None
        if not v.moves:
            return NOOP
        key = lambda m: (v.escape[m[1]], v.enemy_gap(m[1]) <= 1, v.danger[m[1]], self.rng.random())  # noqa: E731
        return int(min(v.moves, key=key)[0])

    def _strike(self, v: _BotView) -> int | None:
        """Bomb the opponent or an enemy that is close, if there is a way out."""
        rival = v.engine.players[1 - v.me]
        gap = abs(v.cell[0] - rival.cell[0]) + abs(v.cell[1] - rival.cell[1]) if rival.alive else 99
        if (gap <= 2 or v.enemy_gap(v.cell) <= 2) and v.engine.can_escape_bomb(v.me):
            return BOMB
        return None

    def _back_off(self, v: _BotView) -> int | None:
        """An enemy is closing in and we cannot bomb it: step away."""
        if v.enemy_gap(v.cell) > 2:
            return None
        retreat = [(a, n) for a, n in v.safe if v.enemy_gap(n) > v.enemy_gap(v.cell)]
        return int(retreat[self.rng.integers(len(retreat))][0]) if retreat else None

    def _wander(self, v: _BotView) -> int | None:
        if v.safe and self.rng.random() < self.wander:
            return int(v.safe[self.rng.integers(len(v.safe))][0])
        return None

    def _advance(self, v: _BotView) -> int | None:
        """Close in on the opponent, blowing open a breakable wall that is in the way."""
        rival = v.engine.players[1 - v.me]
        if not rival.alive:
            return None
        dist = v.engine.distance_map([rival.cell])
        here = dist[v.cell]
        options = [(a, n) for a, n in v.safe if dist[n] < here]
        if options:
            return int(min(options, key=lambda m: (dist[m[1]], self.rng.random()))[0])
        for dr, dc in MOVES.values():
            nxt = (v.cell[0] + dr, v.cell[1] + dc)
            if v.engine.in_bounds(nxt) and v.engine.wall_hp[nxt] > 0 and dist[nxt] < here:
                return BOMB if v.engine.can_escape_bomb(v.me) else None
        return None


class _BotView:
    """What the scripted bot looks at, computed once per decision."""

    def __init__(self, engine: VersusEngine, me: int):
        self.engine, self.me = engine, me
        self.cell = engine.players[me].cell
        self.danger = engine.danger_map()
        self.escape = engine.escape_distances()
        self.enemy_cells = {e.cell for e in engine.enemies if e.alive}
        self.moves: list[tuple[int, tuple[int, int]]] = []
        for action, (dr, dc) in MOVES.items():
            nxt = (self.cell[0] + dr, self.cell[1] + dc)
            if not engine.is_blocked(nxt) and nxt not in self.enemy_cells:
                self.moves.append((action, nxt))
        self.safe = [(a, n) for a, n in self.moves if self.escape[n] == 0 and self.enemy_gap(n) > 1]

    def enemy_gap(self, target: tuple[int, int]) -> int:
        """Manhattan distance from ``target`` to the nearest wandering enemy."""
        return min((abs(target[0] - e[0]) + abs(target[1] - e[1]) for e in self.enemy_cells), default=99)


class ModelPolicy:
    """A trained PPO model (a ``.zip`` path or an already loaded model)."""

    def __init__(self, model: Any, deterministic: bool = True, name: str | None = None, view_radius: int = 4):
        if isinstance(model, (str, Path)):
            from stable_baselines3 import PPO

            name = name or Path(model).stem
            model = PPO.load(str(model), device="cpu")
        self.model = model
        self.deterministic = deterministic
        self.view_radius = view_radius
        self.name = name or "model"

    def act(self, engine: VersusEngine, me: int) -> int:
        obs, _ = versus_observation(engine, me, self.view_radius)
        action, _ = self.model.predict(obs, deterministic=self.deterministic)
        return int(action)


def make_policy(spec: str, deterministic: bool = True, seed: int | None = None) -> Policy:
    """``random``, ``heuristic``, or the path to a trained model."""
    if spec == "random":
        return RandomPolicy(seed)
    if spec == "heuristic":
        return HeuristicPolicy(seed=seed)
    if not Path(spec).exists():
        raise FileNotFoundError(f"no model at {spec!r} (use 'random', 'heuristic' or a .zip path)")
    return ModelPolicy(spec, deterministic=deterministic)


class OpponentSampler:
    """Self-play league: picks the opponent for each training match.

    Snapshots of the learner are saved as ``snap_<steps>.zip`` in ``league_dir``.
    Each match faces the latest snapshot with probability ``latest``, an older one
    with probability ``past``, and a scripted bot otherwise. Mixing in old
    snapshots and bots keeps the learner from forgetting how to beat them.
    """

    def __init__(self, league_dir: str | Path, latest: float = 0.5, past: float = 0.3, cache_size: int = 4):
        self.league_dir = Path(league_dir)
        self.latest, self.past = latest, past
        self.cache_size = cache_size
        self._cache: OrderedDict[Path, ModelPolicy] = OrderedDict()
        self._bots: list[Policy] = [HeuristicPolicy(), HeuristicPolicy(wander=0.3), RandomPolicy()]

    def snapshots(self) -> list[Path]:
        """Saved snapshots, oldest first."""
        return sorted(self.league_dir.glob("snap_*.zip"))

    def sample(self, rng: np.random.Generator) -> Policy:
        """Opponent for the next match."""
        snaps = self.snapshots()
        roll = rng.random()
        if snaps and roll < self.latest:
            return self._load(snaps[-1], rng)
        if len(snaps) > 1 and roll < self.latest + self.past:
            return self._load(snaps[int(rng.integers(len(snaps) - 1))], rng)
        return self._bots[int(rng.choice(len(self._bots), p=[0.6, 0.3, 0.1]))]

    def _load(self, path: Path, rng: np.random.Generator) -> Policy:
        if path not in self._cache:
            self._cache[path] = ModelPolicy(path, deterministic=False)
            if len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
        self._cache.move_to_end(path)
        policy = self._cache[path]
        policy.deterministic = bool(rng.random() < 0.5)  # face both its sharp and its sloppy self
        return policy
