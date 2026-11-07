"""Gymnasium environment for training Two-Fuse, the Battle-mode agent.

The agent is always player 0 of a ``VersusEngine``; player 1 is an opponent
policy drawn at every reset (a scripted bot or an earlier snapshot of the agent
itself, see ``policies.OpponentSampler``).

The observation extends the single-player one in ``env.py`` rather than
replacing it: its first 7 planes and first 19 state values mean the same
things, with "the target" now being the opponent. That lets
``warm_start_policy`` transplant the trained single-player agent, so Two-Fuse
starts out already knowing how to bomb a target and dodge blasts.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .engine import BOMB, MOVES, MapLayout, load_map
from .env import LOCAL_CHANNELS
from .versus_engine import VersusConfig, VersusEngine, VersusEvents

if TYPE_CHECKING:
    from .policies import OpponentSampler, Policy

VERSUS_CHANNELS = (*LOCAL_CHANNELS, "opponent", "closing")
BASE_STATE_SIZE = 19  # the single-player state vector
STATE_SIZE = BASE_STATE_SIZE + 5


@dataclass
class VersusRewardConfig:
    """Reward weights for Battle mode."""

    step: float = -0.005
    invalid_action: float = -0.01
    wall_destroyed: float = 0.05
    enemy_killed: float = 0.3
    win: float = 5.0
    loss: float = -5.0
    draw: float = -2.0  # dying together is not a win: discourages suicide trades
    shaping: float = 0.05
    standoff: int = 3  # approach the opponent only up to this distance
    threat_bomb: float = 0.2  # bomb placed with a way out while the opponent is close
    threat_distance: int = 4


@dataclass
class Perception:
    """Values computed while building an observation that the reward also needs."""

    can_escape: bool
    opponent_distance: float  # walking distance, breakable walls passable at a cost
    opponent_reach: float  # walking distance through open cells only


def versus_observation(engine: VersusEngine, me: int, view_radius: int = 4) -> tuple[dict[str, np.ndarray], Perception]:
    """Observation of the match from player ``me``'s point of view."""
    eng = engine
    height, width = eng.shape
    me_cell = eng.players[me].cell
    rival = eng.players[1 - me]
    pad = view_radius
    danger = eng.danger_map()
    closing = eng.closing_map()

    planes = np.zeros((len(VERSUS_CHANNELS), height + 2 * pad, width + 2 * pad), dtype=np.float32)
    planes[0] = 1.0  # outside the map counts as solid wall
    inner = (slice(pad, pad + height), slice(pad, pad + width))
    planes[0][inner] = eng.solid
    planes[1][inner] = eng.wall_hp > 0
    for bomb in eng.bombs:
        planes[2][bomb.cell[0] + pad, bomb.cell[1] + pad] = bomb.timer / eng.config.bomb_fuse
    planes[3][inner] = eng.flames > 0
    planes[4][inner] = danger
    hostile = [e.cell for e in eng.enemies if e.alive] + ([rival.cell] if rival.alive else [])
    for cell in hostile:  # the opponent is also "an enemy", which is what the warm-started policy hunts
        planes[5][cell[0] + pad, cell[1] + pad] = 1.0
    # plane 6 (door) stays empty: Battle mode has no door
    if rival.alive:
        planes[7][rival.cell[0] + pad, rival.cell[1] + pad] = 1.0
    planes[8][inner] = closing
    r, c = me_cell
    local = planes[:, r : r + 2 * view_radius + 1, c : c + 2 * view_radius + 1]

    target = rival.cell if rival.alive else me_cell
    dist = eng.distance_map([target])
    here = dist[r, c]
    escape = eng.escape_distances()
    can_escape = eng.can_escape_bomb(me)
    hostile_dist = float(eng.distance_map(hostile, breakable_cost=99)[r, c]) if hostile else np.inf
    reach = float(eng.distance_map([target], breakable_cost=99)[r, c])

    escape_gain, step_gain = [], []
    for dr, dc in MOVES.values():
        nr, nc = r + dr, c + dc
        inside = 0 <= nr < height and 0 <= nc < width
        if not inside or eng.is_blocked((nr, nc)):
            escape_gain.append(-1.0)
        else:
            a, b = min(escape[r, c], 99.0), min(escape[nr, nc], 99.0)
            escape_gain.append(float(np.clip(a - b, -1, 1)))
        ok = inside and np.isfinite(dist[nr, nc]) and np.isfinite(here)
        step_gain.append(float(np.clip(here - dist[nr, nc], -1, 1)) if ok else 0.0)

    rival_escape = escape[rival.cell] if rival.alive else 0.0
    cfg = eng.config
    state = np.array(
        [
            # --- the 19 single-player features, with the opponent as the target
            r / (height - 1) * 2 - 1,
            c / (width - 1) * 2 - 1,
            (target[0] - r) / height,
            (target[1] - c) / width,
            min(float(here), 60.0) / 60.0 if np.isfinite(here) else 1.0,
            float(eng.bombs_left(me) > 0),
            (eng.enemies_alive + rival.alive) / max(eng.initial_enemies + 1, 1),
            0.0,  # door open: never, the opponent is always the target
            float(danger[r, c]),
            *step_gain,
            float(can_escape),
            *escape_gain,
            min(hostile_dist, 20.0) / 20.0 if hostile else 1.0,
            # --- Battle-mode extras
            float(eng.bombs_left(1 - me) > 0),
            min(float(rival_escape), 10.0) / 10.0,  # how far the opponent is from safety: >0 means it is in a blast
            float(eng.sudden_death),
            float(np.clip((cfg.sudden_death_start - eng.steps) / cfg.sudden_death_start, 0, 1)),
            float(closing[r, c]),
        ],
        dtype=np.float32,
    )
    obs = {"local": np.ascontiguousarray(local), "state": np.clip(state, -1.0, 1.0)}
    return obs, Perception(can_escape, float(here), reach)


def observation_space(view_radius: int = 4) -> spaces.Dict:
    """The observation space ``versus_observation`` produces."""
    size = 2 * view_radius + 1
    return spaces.Dict(
        {
            "local": spaces.Box(0.0, 1.0, shape=(len(VERSUS_CHANNELS), size, size), dtype=np.float32),
            "state": spaces.Box(-1.0, 1.0, shape=(STATE_SIZE,), dtype=np.float32),
        }
    )


class VersusEnv(gym.Env):
    """Battle mode from player 0's point of view, against a sampled opponent.

    Actions: 0 noop, 1 up, 2 down, 3 left, 4 right, 5 place bomb.
    Goal: be the last one standing.
    """

    metadata = {"render_modes": ["ansi"], "render_fps": 8}  # noqa: RUF012

    def __init__(
        self,
        maps: str | Sequence[str] = "arena_1",
        opponent: str | Policy | OpponentSampler = "heuristic",
        engine_config: VersusConfig | None = None,
        reward_config: VersusRewardConfig | None = None,
        view_radius: int = 4,
        render_mode: str | None = None,
    ):
        super().__init__()
        from .policies import OpponentSampler, make_policy

        names = [maps] if isinstance(maps, str) else list(maps)
        self.layouts: list[MapLayout] = [load_map(name) for name in names]
        self.engine_config = engine_config or VersusConfig()
        self.rewards = reward_config or VersusRewardConfig()
        self.view_radius = view_radius
        self.render_mode = render_mode
        if isinstance(opponent, OpponentSampler):
            self.sampler: OpponentSampler | None = opponent
            self.opponent = make_policy("heuristic")
        else:
            self.sampler = None
            self.opponent = make_policy(opponent) if isinstance(opponent, str) else opponent
        self.action_space = spaces.Discrete(6)
        self.observation_space = observation_space(view_radius)
        self.engine = VersusEngine(self.layouts[0], self.engine_config)
        self._perception = Perception(False, np.inf, np.inf)
        self._stats: dict[str, Any] = {}

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        options = options or {}
        index = int(options.get("map_index", self.np_random.integers(len(self.layouts))))
        swap = bool(options.get("swap", self.np_random.random() < 0.5))  # the coin flip
        if self.sampler is not None:
            self.opponent = self.sampler.sample(self.np_random)
        self.engine = VersusEngine(self.layouts[index], self.engine_config, rng=self.np_random, swap=swap)
        self._stats = {"walls": 0, "kills": 0, "bombs": 0}
        obs, self._perception = versus_observation(self.engine, 0, self.view_radius)
        return obs, self._info()

    def step(self, action):
        action = int(action)
        before = self._perception
        threat = action == BOMB and before.can_escape and before.opponent_reach <= self.rewards.threat_distance
        events = self.engine.step_versus([action, self.opponent.act(self.engine, 1)])
        obs, self._perception = versus_observation(self.engine, 0, self.view_radius)
        mine = events.players[0]
        reward = self._reward(events, before) + self.rewards.threat_bomb * (threat and mine.bomb_placed)
        self._stats["walls"] += mine.walls_destroyed
        self._stats["kills"] += mine.enemies_killed
        self._stats["bombs"] += int(mine.bomb_placed)
        info = self._info()
        if events.done:
            info["episode_stats"] = {
                **self._stats,
                "won": events.winner == 0,
                "lost": events.winner == 1,
                "draw": events.draw,
                "killed_by": mine.killed_by,
                "opponent_killed_by": events.players[1].killed_by,
                "steps": self.engine.steps,
                "map": self.engine.layout.name,
                "opponent": self.opponent.name,
            }
        return obs, reward, events.done and not events.truncated, events.truncated, info

    def _reward(self, events: VersusEvents, before: Perception) -> float:
        cfg = self.rewards
        mine = events.players[0]
        reward = cfg.step + cfg.invalid_action * mine.invalid_action
        reward += cfg.wall_destroyed * mine.walls_destroyed + cfg.enemy_killed * mine.enemies_killed
        if events.done:
            reward += cfg.draw if events.draw else (cfg.win if events.winner == 0 else cfg.loss)
            return float(reward)

        def potential(p: Perception) -> float:
            return -max(p.opponent_distance - cfg.standoff, 0.0) if np.isfinite(p.opponent_distance) else 0.0

        reward += cfg.shaping * (potential(self._perception) - potential(before))
        return float(reward)

    def render(self):
        if self.render_mode == "ansi":
            return self.engine.render_text()
        return None

    def _info(self) -> dict[str, Any]:
        return {"steps": self.engine.steps, "sudden_death": self.engine.sudden_death}


def warm_start_policy(single_player_model: str, model: Any) -> None:
    """Copy a trained single-player PPO policy into a fresh Battle-mode one.

    Both use flattened Dict inputs (``local`` then ``state``). The old inputs keep
    their meaning, so their first-layer weights are copied to the matching
    columns; the new planes and state values start with zero weight. The result
    plays exactly like the old agent until training teaches it the new inputs.
    """
    from stable_baselines3 import PPO

    old = PPO.load(single_player_model, device="cpu")
    old_space, new_space = cast(spaces.Dict, old.observation_space), cast(spaces.Dict, model.observation_space)
    old_local, old_state = spaces.flatdim(old_space["local"]), spaces.flatdim(old_space["state"])
    new_local = spaces.flatdim(new_space["local"])
    if old_state != BASE_STATE_SIZE:
        raise ValueError(f"{single_player_model} is not a single-player model ({old_state} state values)")
    columns = np.concatenate([np.arange(old_local), new_local + np.arange(old_state)])

    new_params = model.policy.state_dict()
    for name, weight in old.policy.state_dict().items():
        target = new_params[name]
        if weight.shape == target.shape:
            target.copy_(weight)
        else:  # a first layer: old inputs go to their new columns, the rest stay zero
            target.zero_()
            target[:, columns] = weight
    model.policy.load_state_dict(new_params)


def make_versus_env(maps: str | Sequence[str] = "arena_1", **kwargs: Any) -> VersusEnv:
    """Factory used by training scripts."""
    return VersusEnv(maps=maps, **kwargs)
