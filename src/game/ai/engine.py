"""Headless, step-based Bomberman simulation used for reinforcement learning.

The pygame game in ``game.level`` advances by pixels and measures bomb fuses in
wall-clock seconds, which makes it unusable as an RL environment: one tile of
movement takes 16-32 actions and the outcome of an episode depends on how fast
the machine renders. This module re-implements the same rules on the tile grid,
so one action is one tile and every timer is counted in steps.

Rules carried over from the game:

* maps are the CSV files in ``src/maps`` (``#``/``W`` solid, ``B_1``/``I``
  breakable, ``B_2`` takes two hits, ``P`` player, ``E`` enemy, ``D`` door)
* bombs have range 1 and the player can have one bomb on the map at a time
* flames stop at solid walls and at the first breakable wall they damage
* enemies wander and turn around when blocked; touching one kills the player
* the door only opens once every enemy is dead; reaching it wins the level
"""

from __future__ import annotations

import csv
import heapq
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MAP_DIR = Path(__file__).resolve().parents[2] / "maps"
ARENA_DIR = Path(__file__).resolve().parents[2] / "arenas"  # versus maps; kept apart so `play` does not list them

NOOP, UP, DOWN, LEFT, RIGHT, BOMB = range(6)
ACTION_NAMES = ("noop", "up", "down", "left", "right", "bomb")
MOVES = {UP: (-1, 0), DOWN: (1, 0), LEFT: (0, -1), RIGHT: (0, 1)}

Cell = tuple[int, int]


@dataclass
class EngineConfig:
    """Tunable rules of the simulation. All durations are in steps."""

    bomb_fuse: int = 8
    flame_duration: int = 2
    bomb_range: int = 1
    bomb_limit: int = 1
    enemy_move_every: int = 2  # enemies move at half the player's speed, as in the game
    enemy_turn_prob: float = 0.25
    max_steps: int = 400


@dataclass
class Bomb:
    """A placed bomb."""

    cell: Cell
    timer: int
    range: int
    owner: int = 0


@dataclass
class Enemy:
    """A wandering enemy."""

    cell: Cell
    direction: Cell
    alive: bool = True


@dataclass
class StepEvents:
    """What happened during a single step; the environment turns this into reward."""

    walls_destroyed: int = 0
    enemies_killed: int = 0
    bomb_placed: bool = False
    invalid_action: bool = False
    player_died: bool = False
    reached_door: bool = False
    truncated: bool = False
    killed_by: str | None = None


@dataclass
class MapLayout:
    """A parsed map."""

    name: str
    solid: np.ndarray  # bool (H, W)
    wall_hp: np.ndarray  # int (H, W), >0 for breakable walls
    player: Cell
    enemies: list[Cell]
    door: Cell | None
    rival: Cell | None = None  # second player's start ('Q'), used by versus mode

    @property
    def shape(self) -> tuple[int, int]:
        """Grid height and width."""
        return self.solid.shape  # type: ignore[return-value]


def load_map(name_or_path: str) -> MapLayout:
    """Parse a map CSV, by file path or by name (``map_1``, ``arena_1``) inside ``src/maps`` or ``src/arenas``."""
    path = Path(name_or_path)
    if not path.exists():
        stem = name_or_path.removesuffix(".csv")
        path = next((d / f"{stem}.csv" for d in (MAP_DIR, ARENA_DIR) if (d / f"{stem}.csv").exists()), path)
    with open(path, newline="", encoding="utf-8-sig") as file:
        rows = list(csv.reader(file))
    rows = [row for row in rows if any(cell.strip() for cell in row)]  # drop blank header rows
    height, width = len(rows), max(len(row) for row in rows)
    solid = np.zeros((height, width), dtype=bool)
    wall_hp = np.zeros((height, width), dtype=np.int8)
    player: Cell | None = None
    enemies: list[Cell] = []
    door: Cell | None = None
    rival: Cell | None = None
    for r, row in enumerate(rows):
        for c in range(width):
            token = row[c].strip() if c < len(row) else "#"
            if token in ("#", "W"):
                solid[r, c] = True
            elif token in ("B_1", "I"):
                wall_hp[r, c] = 1
            elif token == "B_2":
                wall_hp[r, c] = 2
            elif token == "P":
                player = (r, c)
            elif token == "E":
                enemies.append((r, c))
            elif token == "D":
                door = (r, c)
            elif token == "Q":
                rival = (r, c)
    if player is None:
        raise ValueError(f"map {path} has no player start 'P'")
    return MapLayout(path.stem, solid, wall_hp, player, enemies, door, rival)


class Engine:
    """Grid simulation of one level."""

    def __init__(self, layout: MapLayout, config: EngineConfig | None = None, rng: np.random.Generator | None = None):
        self.layout = layout
        self.config = config or EngineConfig()
        self.rng = rng or np.random.default_rng()
        self.reset()

    # ------------------------------------------------------------------ setup
    def reset(self, rng: np.random.Generator | None = None) -> None:
        """Restore the level to its initial state."""
        if rng is not None:
            self.rng = rng
        self.solid = self.layout.solid
        self.wall_hp = self.layout.wall_hp.copy()
        self.player: Cell = self.layout.player
        self.alive = True
        self.won = False
        self.steps = 0
        self.bombs: list[Bomb] = []
        self.flames = np.zeros(self.solid.shape, dtype=np.int8)
        self.enemies = [Enemy(cell, self._random_direction(cell)) for cell in self.layout.enemies]
        self.initial_enemies = len(self.enemies)
        self.door = self.layout.door if self.layout.door is not None else self._pick_door()

    def _pick_door(self) -> Cell:
        """Pick a free cell far from the player when the map has no 'D'."""
        free = np.argwhere(~self.solid & (self.wall_hp == 0))
        dists = np.abs(free - np.array(self.player)).sum(axis=1)
        far = free[dists >= np.percentile(dists, 75)]
        r, c = far[self.rng.integers(len(far))]
        return int(r), int(c)

    # ---------------------------------------------------------------- queries
    @property
    def shape(self) -> tuple[int, int]:
        """Grid height and width."""
        return self.layout.shape

    @property
    def enemies_alive(self) -> int:
        """Number of living enemies."""
        return sum(enemy.alive for enemy in self.enemies)

    @property
    def door_open(self) -> bool:
        """The door opens once every enemy is dead."""
        return self.enemies_alive == 0

    @property
    def bombs_available(self) -> int:
        """How many more bombs the player may place right now."""
        return self.config.bomb_limit - len(self.bombs)

    def in_bounds(self, cell: Cell) -> bool:
        """Whether a cell lies on the grid."""
        return 0 <= cell[0] < self.shape[0] and 0 <= cell[1] < self.shape[1]

    def is_blocked(self, cell: Cell) -> bool:
        """Solid walls, breakable walls and bombs block movement."""
        if not self.in_bounds(cell) or self.solid[cell] or self.wall_hp[cell] > 0:
            return True
        return any(bomb.cell == cell for bomb in self.bombs)

    def blast_cells(self, bomb: Bomb) -> list[Cell]:
        """Cells a bomb's explosion would cover, without changing anything."""
        cells = [bomb.cell]
        for dr, dc in MOVES.values():
            for dist in range(1, bomb.range + 1):
                cell = (bomb.cell[0] + dr * dist, bomb.cell[1] + dc * dist)
                if not self.in_bounds(cell) or self.solid[cell]:
                    break
                cells.append(cell)
                if self.wall_hp[cell] > 0:
                    break
        return cells

    def hazard_mask(self) -> np.ndarray:
        """Cells that are deadly right now, apart from bomb blasts. Subclasses add their own hazards."""
        return self.flames > 0

    def danger_map(self) -> np.ndarray:
        """Per-cell urgency in [0, 1]: 1 means a flame is there or about to be."""
        danger = (self.flames > 0).astype(np.float32)
        for bomb in self.bombs:
            urgency = 1.0 - (bomb.timer - 1) / self.config.bomb_fuse
            for cell in self.blast_cells(bomb):
                danger[cell] = max(danger[cell], urgency)
        return danger

    def escape_distances(self, extra_bomb: Cell | None = None) -> np.ndarray:
        """Steps from each cell to the nearest cell no current (or hypothetical) bomb can reach.

        ``extra_bomb`` adds a bomb that has not been placed yet, which answers
        "can I drop a bomb here and still get away?". Unreachable cells are inf.
        """
        bombs = list(self.bombs)
        if extra_bomb is not None:
            bombs.append(Bomb(extra_bomb, self.config.bomb_fuse, self.config.bomb_range))
        unsafe = self.hazard_mask().copy()
        for bomb in bombs:
            for cell in self.blast_cells(bomb):
                unsafe[cell] = True
        bomb_cells = list(dict.fromkeys(bomb.cell for bomb in bombs))  # placement order, so ports can reproduce it
        walkable = ~self.solid & (self.wall_hp == 0)
        for cell in bomb_cells:
            walkable[cell] = False
        dist = np.full(self.shape, np.inf, dtype=np.float32)
        frontier = [tuple(cell) for cell in np.argwhere(walkable & ~unsafe)]
        for cell in frontier:
            dist[cell] = 0
        while frontier:  # multi-source BFS outward from every safe cell
            nxt_frontier = []
            for r, c in frontier:
                for dr, dc in MOVES.values():
                    nxt = (r + dr, c + dc)
                    if self.in_bounds(nxt) and walkable[nxt] and dist[nxt] == np.inf:
                        dist[nxt] = dist[r, c] + 1
                        nxt_frontier.append(nxt)
            frontier = nxt_frontier
        for cell in bomb_cells:  # you can always step off a bomb you are standing on
            neighbours = [
                dist[cell[0] + dr, cell[1] + dc]
                for dr, dc in MOVES.values()
                if self.in_bounds((cell[0] + dr, cell[1] + dc))
            ]
            dist[cell] = min(neighbours, default=np.inf) + 1
        return dist

    def can_escape_own_bomb(self) -> bool:
        """Whether a bomb dropped right now would leave the player a way out in time."""
        if self.bombs_available <= 0:
            return False
        return bool(self.escape_distances(self.player)[self.player] <= self.config.bomb_fuse - 1)

    # ------------------------------------------------------------------- step
    def step(self, action: int) -> StepEvents:
        """Advance the simulation by one step."""
        events = StepEvents()
        if not self.alive or self.won:
            raise RuntimeError("step() called on a finished episode; call reset()")
        self.steps += 1

        self._apply_player_action(action, events)
        self._check_enemy_contact(events)
        if self.steps % self.config.enemy_move_every == 0:
            self._move_enemies()
            self._check_enemy_contact(events)
        self._tick_bombs(events)
        self._apply_flames(events)

        if self.alive and self.door_open and self.player == self.door:
            self.won = True
            events.reached_door = True
        if self.alive and not self.won and self.steps >= self.config.max_steps:
            events.truncated = True
        return events

    def _apply_player_action(self, action: int, events: StepEvents) -> None:
        if action in MOVES:
            dr, dc = MOVES[action]
            target = (self.player[0] + dr, self.player[1] + dc)
            if self.is_blocked(target):
                events.invalid_action = True
            else:
                self.player = target
        elif action == BOMB:
            if self.bombs_available > 0 and not any(b.cell == self.player for b in self.bombs):
                self.bombs.append(Bomb(self.player, self.config.bomb_fuse, self.config.bomb_range))
                events.bomb_placed = True
            else:
                events.invalid_action = True

    def _random_direction(self, cell: Cell) -> Cell:
        options = [d for d in MOVES.values() if not self.is_blocked((cell[0] + d[0], cell[1] + d[1]))]
        if not options:
            return (0, 0)
        return options[self.rng.integers(len(options))]

    def _move_enemies(self) -> None:
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            r, c = enemy.cell
            dr, dc = enemy.direction
            ahead_blocked = enemy.direction == (0, 0) or self.is_blocked((r + dr, c + dc))
            if ahead_blocked or self.rng.random() < self.config.enemy_turn_prob:
                options = [d for d in MOVES.values() if not self.is_blocked((r + d[0], c + d[1]))]
                forward = [d for d in options if d != (-dr, -dc)]
                pool = forward or options  # only reverse at dead ends, like the game's enemies
                enemy.direction = pool[self.rng.integers(len(pool))] if pool else (0, 0)
            dr, dc = enemy.direction
            if (dr, dc) != (0, 0):
                enemy.cell = (r + dr, c + dc)

    def _check_enemy_contact(self, events: StepEvents) -> None:
        if self.alive and any(e.alive and e.cell == self.player for e in self.enemies):
            self.alive = False
            events.player_died = True
            events.killed_by = "enemy"

    def _tick_bombs(self, events: StepEvents) -> None:
        self.flames[self.flames > 0] -= 1
        for bomb in self.bombs:
            bomb.timer -= 1
        exploding = [bomb for bomb in self.bombs if bomb.timer <= 0]
        while exploding:  # chain reactions: flames detonate other bombs immediately
            bomb = exploding.pop()
            if bomb not in self.bombs:
                continue
            self.bombs.remove(bomb)
            for cell in self.blast_cells(bomb):
                self.flames[cell] = self.config.flame_duration
                if self.wall_hp[cell] > 0:
                    self.wall_hp[cell] -= 1
                    events.walls_destroyed += int(self.wall_hp[cell] == 0)
                exploding.extend(b for b in self.bombs if b.cell == cell and b not in exploding)

    def _apply_flames(self, events: StepEvents) -> None:
        for enemy in self.enemies:
            if enemy.alive and self.flames[enemy.cell] > 0:
                enemy.alive = False
                events.enemies_killed += 1
        if self.alive and self.flames[self.player] > 0:
            self.alive = False
            events.player_died = True
            events.killed_by = "bomb"

    # ------------------------------------------------------------- utilities
    def distance_map(self, sources: Sequence[Cell], breakable_cost: int = 4) -> np.ndarray:
        """Shortest walking distance from every cell to the nearest source.

        Breakable walls are passable at ``breakable_cost`` so the distance stays
        finite on maps where the way forward has to be bombed open.
        """
        height, width = self.shape
        dist = np.full((height, width), np.inf, dtype=np.float32)
        solid, wall_hp = self.solid, self.wall_hp
        heap = [(0, src) for src in sources]
        for src in sources:
            dist[src] = 0
        while heap:  # Dijkstra; the grid is only a few hundred cells
            d, (r, c) = heapq.heappop(heap)
            if d > dist[r, c]:
                continue
            for dr, dc in MOVES.values():
                nr, nc = r + dr, c + dc
                if not (0 <= nr < height and 0 <= nc < width) or solid[nr, nc]:
                    continue
                nd = d + (breakable_cost if wall_hp[nr, nc] > 0 else 1)
                if nd < dist[nr, nc]:
                    dist[nr, nc] = nd
                    heapq.heappush(heap, (nd, (nr, nc)))
        return dist

    def render_text(self) -> str:
        """ASCII view, handy for debugging and tests."""
        grid = np.where(self.solid, "#", np.where(self.wall_hp > 0, "b", " ")).astype("<U1")
        grid[self.flames > 0] = "*"
        grid[self.door] = "D" if self.door_open else "d"
        for bomb in self.bombs:
            grid[bomb.cell] = "o"
        for enemy in self.enemies:
            if enemy.alive:
                grid[enemy.cell] = "E"
        grid[self.player] = "P" if self.alive else "X"
        return "\n".join("".join(row) for row in grid)


def available_maps() -> list[str]:
    """Names of the map files shipped with the game."""
    return sorted(path.stem for path in MAP_DIR.glob("*.csv"))


def available_arenas() -> list[str]:
    """Names of the versus-only maps."""
    return sorted(path.stem for path in ARENA_DIR.glob("*.csv"))


__all__ = [
    "ACTION_NAMES",
    "BOMB",
    "DOWN",
    "LEFT",
    "NOOP",
    "RIGHT",
    "UP",
    "Engine",
    "EngineConfig",
    "MapLayout",
    "StepEvents",
    "available_arenas",
    "available_maps",
    "load_map",
]
