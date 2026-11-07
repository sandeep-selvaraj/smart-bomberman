"""Two-player Battle mode on top of the headless engine: human vs Two-Fuse.

Rules (on top of the single-player ones in ``engine.py``):

* two fighters start in opposite corners (the map's ``P`` and ``Q``; without a
  ``Q`` the second start mirrors ``P``). A coin flip (``swap``) decides who gets which.
* both act simultaneously each step; fighters do not block each other
* each fighter has its own bomb limit; flames remember whose bomb made them, so
  kills are credited to the right player
* the map's wandering enemies stay on as hazards for both sides
* **last one standing wins**; dying on the same step is a draw
* **sudden death**: from ``sudden_death_start`` the arena closes in, one cell
  every ``sudden_death_every`` steps, spiralling from the border to the centre.
  A closing cell crushes whatever is on it, so every match ends.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .engine import BOMB, MOVES, Bomb, Cell, Enemy, Engine, EngineConfig, MapLayout

PLAYER_COUNT = 2


@dataclass
class VersusConfig(EngineConfig):
    """Engine rules plus the Battle-mode ones. All durations are in steps."""

    max_steps: int = 1000  # safety net only: sudden death ends matches well before this
    sudden_death_start: int = 200
    sudden_death_every: int = 1
    sudden_death_warning: int = 12  # how many steps ahead a closing cell shows up as danger
    enemies: bool = True


@dataclass
class Fighter:
    """One of the two players."""

    cell: Cell
    alive: bool = True
    killed_by: str | None = None


@dataclass
class FighterEvents:
    """What happened to one fighter during a step."""

    walls_destroyed: int = 0
    enemies_killed: int = 0
    bomb_placed: bool = False
    invalid_action: bool = False
    died: bool = False
    killed_by: str | None = None  # "enemy", "own_bomb", "opponent_bomb" or "crushed"
    killed_opponent: bool = False


@dataclass
class VersusEvents:
    """What happened during a step, per fighter, and how the match stands."""

    players: list[FighterEvents] = field(default_factory=lambda: [FighterEvents() for _ in range(PLAYER_COUNT)])
    done: bool = False
    winner: int | None = None
    draw: bool = False
    truncated: bool = False


def mirror_spawn(layout: MapLayout) -> Cell:
    """The free cell closest to the point mirror of the first player's start."""
    height, width = layout.shape
    target = np.array((height - 1 - layout.player[0], width - 1 - layout.player[1]))
    free = np.argwhere(~layout.solid & (layout.wall_hp == 0))
    free = free[[tuple(cell) != layout.player and tuple(cell) not in layout.enemies for cell in free]]
    r, c = free[np.abs(free - target).sum(axis=1).argmin()]
    return int(r), int(c)


class VersusEngine(Engine):
    """Grid simulation of a two-player Battle-mode match."""

    config: VersusConfig

    def __init__(
        self,
        layout: MapLayout,
        config: VersusConfig | None = None,
        rng: np.random.Generator | None = None,
        swap: bool = False,
    ):
        self.swap = swap
        config = config or VersusConfig()
        if config.sudden_death_every < 1:
            raise ValueError("sudden_death_every must be at least 1")
        super().__init__(layout, config, rng)

    # ------------------------------------------------------------------ setup
    def reset(self, rng: np.random.Generator | None = None, swap: bool | None = None) -> None:
        """Restore the arena. ``swap`` puts player 0 on the second start (the coin flip)."""
        if rng is not None:
            self.rng = rng
        if swap is not None:
            self.swap = swap
        self.solid = self.layout.solid.copy()  # sudden death adds walls, so never share the layout's array
        self.wall_hp = self.layout.wall_hp.copy()
        starts = [self.layout.player, self.layout.rival or mirror_spawn(self.layout)]
        if self.swap:
            starts.reverse()
        self.players = [Fighter(cell) for cell in starts]
        self.steps = 0
        self.bombs: list[Bomb] = []
        self.flames = np.zeros(self.solid.shape, dtype=np.int8)
        self.flame_owner = np.full(self.solid.shape, -1, dtype=np.int8)
        cells = self.layout.enemies if self.config.enemies else []
        self.enemies = [Enemy(cell, self._random_direction(cell)) for cell in cells]
        self.initial_enemies = len(self.enemies)
        self.closing_order = self._spiral_cells()
        self.closed = 0
        self.finished = False
        self.winner: int | None = None

    def _spiral_cells(self) -> list[Cell]:
        """Every open cell, ordered from the border inwards, clockwise ring by ring."""
        top, left = 0, 0
        bottom, right = self.shape[0] - 1, self.shape[1] - 1
        order: list[Cell] = []
        while top <= bottom and left <= right:
            order += [(top, c) for c in range(left, right + 1)]
            order += [(r, right) for r in range(top + 1, bottom + 1)]
            if bottom > top:
                order += [(bottom, c) for c in range(right - 1, left - 1, -1)]
            if right > left:
                order += [(r, left) for r in range(bottom - 1, top, -1)]
            top, left, bottom, right = top + 1, left + 1, bottom - 1, right - 1
        return [cell for cell in order if not self.solid[cell]]

    # ---------------------------------------------------------------- queries
    @property
    def sudden_death(self) -> bool:
        """Whether the arena has started closing in."""
        return self.steps >= self.config.sudden_death_start

    def close_step(self, index: int) -> int:
        """The step at which the ``index``-th cell of the spiral closes."""
        return self.config.sudden_death_start + index * self.config.sudden_death_every

    def closing_map(self) -> np.ndarray:
        """Per-cell urgency in [0, 1] of cells about to close; 1 means it closes next step."""
        urgency = np.zeros(self.shape, dtype=np.float32)
        horizon = self.config.sudden_death_warning
        for index in range(self.closed, len(self.closing_order)):
            wait = self.close_step(index) - self.steps
            if wait > horizon:
                break
            urgency[self.closing_order[index]] = 1.0 - (max(wait, 1) - 1) / horizon
        return urgency

    def hazard_mask(self) -> np.ndarray:
        """Flames, plus cells that close before a freshly placed bomb would go off."""
        mask = super().hazard_mask()
        for index in range(self.closed, len(self.closing_order)):
            if self.close_step(index) - self.steps > self.config.bomb_fuse:
                break
            mask[self.closing_order[index]] = True
        return mask

    def danger_map(self) -> np.ndarray:
        """Bomb and flame danger, plus the closing walls of sudden death."""
        return np.maximum(super().danger_map(), self.closing_map())

    def bombs_left(self, player: int) -> int:
        """How many more bombs ``player`` may place right now."""
        return self.config.bomb_limit - sum(bomb.owner == player for bomb in self.bombs)

    def can_escape_bomb(self, player: int) -> bool:
        """Whether ``player`` could drop a bomb now and still get out of its blast in time."""
        cell = self.players[player].cell
        if self.bombs_left(player) <= 0 or any(bomb.cell == cell for bomb in self.bombs):
            return False
        return bool(self.escape_distances(cell)[cell] <= self.config.bomb_fuse - 1)

    # ------------------------------------------------------------------- step
    def step_versus(self, actions: Sequence[int]) -> VersusEvents:
        """Advance the match by one step; ``actions[i]`` is player ``i``'s action."""
        if self.finished:
            raise RuntimeError("step_versus() called on a finished match; call reset()")
        events = VersusEvents()
        self.steps += 1

        for fighter, action, ev in zip(self.players, actions, events.players, strict=True):
            if fighter.alive and action in MOVES:  # moves are judged against the board before anyone bombs
                dr, dc = MOVES[action]
                target = (fighter.cell[0] + dr, fighter.cell[1] + dc)
                if self.is_blocked(target):
                    ev.invalid_action = True
                else:
                    fighter.cell = target
        for player in self.rng.permutation(PLAYER_COUNT):  # random order settles two bombs on one cell fairly
            fighter, ev = self.players[player], events.players[player]
            if fighter.alive and actions[player] == BOMB:
                if self.bombs_left(player) > 0 and not any(bomb.cell == fighter.cell for bomb in self.bombs):
                    self.bombs.append(Bomb(fighter.cell, self.config.bomb_fuse, self.config.bomb_range, int(player)))
                    ev.bomb_placed = True
                else:
                    ev.invalid_action = True

        self._check_contact(events)
        if self.steps % self.config.enemy_move_every == 0:
            self._move_enemies()
            self._check_contact(events)
        self._tick_owned_bombs(events)
        self._apply_owned_flames(events)
        self._close_cells(events)
        self._resolve(events)
        return events

    def _kill(self, player: int, cause: str, events: VersusEvents) -> None:
        fighter = self.players[player]
        fighter.alive, fighter.killed_by = False, cause
        events.players[player].died = True
        events.players[player].killed_by = cause

    def _check_contact(self, events: VersusEvents) -> None:
        for player, fighter in enumerate(self.players):
            if fighter.alive and any(e.alive and e.cell == fighter.cell for e in self.enemies):
                self._kill(player, "enemy", events)

    def _tick_owned_bombs(self, events: VersusEvents) -> None:
        self.flames[self.flames > 0] -= 1
        self.flame_owner[self.flames == 0] = -1
        for bomb in self.bombs:
            bomb.timer -= 1
        exploding = [bomb for bomb in self.bombs if bomb.timer <= 0]
        while exploding:  # chain reactions: each bomb's flames still belong to its own owner
            bomb = exploding.pop()
            if bomb not in self.bombs:
                continue
            self.bombs.remove(bomb)
            for cell in self.blast_cells(bomb):
                self.flames[cell] = self.config.flame_duration
                self.flame_owner[cell] = bomb.owner
                if self.wall_hp[cell] > 0:
                    self.wall_hp[cell] -= 1
                    events.players[bomb.owner].walls_destroyed += int(self.wall_hp[cell] == 0)
                exploding.extend(b for b in self.bombs if b.cell == cell and b not in exploding)

    def _apply_owned_flames(self, events: VersusEvents) -> None:
        for enemy in self.enemies:
            if enemy.alive and self.flames[enemy.cell] > 0:
                enemy.alive = False
                owner = int(self.flame_owner[enemy.cell])
                if owner >= 0:
                    events.players[owner].enemies_killed += 1
        for player, fighter in enumerate(self.players):
            if fighter.alive and self.flames[fighter.cell] > 0:
                owner = int(self.flame_owner[fighter.cell])
                self._kill(player, "own_bomb" if owner == player else "opponent_bomb", events)
                if 0 <= owner != player:
                    events.players[owner].killed_opponent = True

    def _close_cells(self, events: VersusEvents) -> None:
        while self.closed < len(self.closing_order) and self.steps >= self.close_step(self.closed):
            cell = self.closing_order[self.closed]
            self.closed += 1
            self.solid[cell] = True
            self.wall_hp[cell] = 0
            self.flames[cell] = 0
            self.bombs = [bomb for bomb in self.bombs if bomb.cell != cell]
            for enemy in self.enemies:
                if enemy.alive and enemy.cell == cell:
                    enemy.alive = False
            for player, fighter in enumerate(self.players):
                if fighter.alive and fighter.cell == cell:
                    self._kill(player, "crushed", events)

    def _resolve(self, events: VersusEvents) -> None:
        alive = [fighter.alive for fighter in self.players]
        if not any(alive):
            events.done = events.draw = True
        elif not all(alive):
            events.done, events.winner = True, alive.index(True)
        elif self.steps >= self.config.max_steps:
            events.done = events.draw = events.truncated = True
        self.finished, self.winner = events.done, events.winner

    # ------------------------------------------------------------- utilities
    def render_text(self) -> str:
        """ASCII view: 1 and 2 are the fighters, x a dead one, ! a cell about to close."""
        grid = np.where(self.solid, "#", np.where(self.wall_hp > 0, "b", " ")).astype("<U1")
        grid[(self.closing_map() > 0) & ~self.solid] = "!"
        grid[self.flames > 0] = "*"
        for bomb in self.bombs:
            grid[bomb.cell] = "o"
        for enemy in self.enemies:
            if enemy.alive:
                grid[enemy.cell] = "E"
        for player, fighter in enumerate(self.players):
            grid[fighter.cell] = str(player + 1) if fighter.alive else "x"
        return "\n".join("".join(row) for row in grid)


__all__ = ["Fighter", "FighterEvents", "VersusConfig", "VersusEngine", "VersusEvents", "mirror_spawn"]
