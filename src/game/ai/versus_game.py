"""Human vs Two-Fuse: Battle mode in a pygame window.

Two-Fuse is the trained Battle-mode agent. Like the villain it is named after,
it flips a coin before every round, and the coin decides who starts in which
corner.

The match runs on a fixed tick rate. Every tick, your latest key press (or the
arrow key you are holding) becomes your action and Two-Fuse picks one too, so
neither side moves faster or gets more decisions than the other.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from .engine import BOMB, DOWN, LEFT, NOOP, RIGHT, UP, MapLayout, load_map
from .policies import HeuristicPolicy, ModelPolicy, Policy, make_policy
from .render import TILE, Renderer
from .versus_engine import VersusConfig, VersusEngine
from .versus_train import CHAMPION

NAME = "TWO-FUSE"
WHITE = (255, 255, 255)
HUD_HEIGHT = 52
TAUNTS = {
    "start": [
        "Heads I win. Tails you lose.",
        "Let's leave it to chance. And fuses.",
        "Two sides to every coin. One way out of this arena.",
        "I never decide. The coin does.",
    ],
    "two_fuse": [
        "The coin never lies.",
        "Two sides, one winner. Not you.",
        "Unlucky. Then again, luck had nothing to do with it.",
        "Flip again? It lands the same way.",
    ],
    "human": [
        "A lucky flip. Nothing more.",
        "Fine. Best of the next coin toss.",
        "Even a fair coin lands wrong sometimes.",
    ],
    "draw": ["Even chance, even ending.", "We both lose the toss.", "Edge of the coin. How rare."],
    "sudden": ["The walls have a dark side too.", "The arena is choosing for us now."],
}


def two_fuse(difficulty: str = "normal", model: str | Path = CHAMPION) -> Policy:
    """Two-Fuse at a difficulty: easy is the scripted bot, normal and hard are the trained model."""
    if difficulty == "easy":
        return HeuristicPolicy(wander=0.25)
    if difficulty not in ("normal", "hard"):
        raise ValueError(f"difficulty must be easy, normal or hard, not {difficulty!r}")
    if not Path(model).exists():
        print(f"no trained Two-Fuse at {model}; falling back to the scripted bot")
        return HeuristicPolicy(wander=0.05 if difficulty == "hard" else 0.15)
    return ModelPolicy(model, deterministic=difficulty == "hard", name="two_fuse")


class VersusRenderer(Renderer):
    """Pygame view of a ``VersusEngine``, with a score HUD and banners."""

    def __init__(self, grid_shape: tuple[int, int], headless: bool = False, tps: int = 7):
        self.tps = tps
        super().__init__(grid_shape, headless, hud=HUD_HEIGHT, caption=f"Smart-Bomberman - you vs {NAME}")
        pygame = self.pygame
        rival = self.sprites["player"].copy()  # Two-Face style: the right half is scarred purple
        rival.fill((185, 90, 255), pygame.Rect(TILE // 2, 0, TILE // 2, TILE), special_flags=pygame.BLEND_RGB_MULT)
        self.sprites["rival"] = rival
        self.big_font = pygame.font.Font(pygame.font.get_default_font(), 30)
        self.small_font = pygame.font.Font(pygame.font.get_default_font(), 13)

    def draw_versus(
        self,
        engine: VersusEngine,
        names: tuple[str, str],
        score: tuple[int, int],
        taunt: str = "",
        banner: tuple[str, str] | None = None,
        fps: int = 60,
    ) -> np.ndarray | None:
        """Draw one frame. Returns an RGB array in headless mode."""
        self.screen.fill((128, 128, 128))
        self._draw_board(engine)
        self._draw_hud(engine, names, score, taunt)
        if banner:
            self._draw_banner(engine, *banner)
        if self.headless:
            return np.transpose(self.pygame.surfarray.array3d(self.screen), (1, 0, 2))
        self.pygame.display.flip()
        self.clock.tick(fps)
        return None

    def _at(self, cell: tuple[int, int]) -> tuple[int, int]:
        return cell[1] * TILE, cell[0] * TILE + self.hud

    def _tint(self, cell: tuple[int, int], rgba: tuple[int, int, int, int]) -> None:
        overlay = self.pygame.Surface((TILE, TILE), self.pygame.SRCALPHA)
        overlay.fill(rgba)
        self.screen.blit(overlay, self._at(cell))

    def _draw_board(self, engine: VersusEngine) -> None:
        screen, sprites, at = self.screen, self.sprites, self._at
        closed = engine.solid & ~engine.layout.solid  # walls added by sudden death
        for r, c in np.argwhere(engine.solid):
            screen.blit(sprites["wall"], at((r, c)))
        for r, c in np.argwhere(closed):
            self._tint((r, c), (120, 0, 40, 120))
        for r, c in np.argwhere(engine.wall_hp > 0):
            cracked = engine.wall_hp[r, c] == 1 and engine.layout.wall_hp[r, c] == 2
            screen.blit(sprites["cracked" if cracked else "breakable"], at((r, c)))
        closing = engine.closing_map()
        for r, c in np.argwhere((closing > 0) & ~engine.solid):
            self._tint((r, c), (230, 30, 30, int(60 + 140 * closing[r, c])))
        for bomb in engine.bombs:
            screen.blit(sprites["bomb"], at(bomb.cell))
        for r, c in np.argwhere(engine.flames > 0):
            screen.blit(sprites["explosion"], at((r, c)))
        for enemy in engine.enemies:
            if enemy.alive:
                screen.blit(sprites["enemy"], at(enemy.cell))
        for fighter, key in zip(engine.players, ("player", "rival"), strict=True):
            if fighter.alive:
                screen.blit(sprites[key], at(fighter.cell))

    def _draw_hud(self, engine: VersusEngine, names: tuple[str, str], score: tuple[int, int], taunt: str) -> None:
        pygame, screen = self.pygame, self.screen
        width = engine.shape[1] * TILE
        pygame.draw.rect(screen, (30, 30, 40), pygame.Rect(0, 0, width, self.hud))
        screen.blit(self.font.render(f"{names[0]}  {score[0]} - {score[1]}  {names[1]}", True, WHITE), (8, 6))
        if engine.sudden_death:
            label = self.font.render("SUDDEN DEATH", True, (255, 90, 90))
        else:
            seconds = -(-(engine.config.sudden_death_start - engine.steps) // self.tps)
            label = self.font.render(f"sudden death in {seconds}s", True, WHITE)
        screen.blit(label, (width - label.get_width() - 8, 6))
        if taunt:
            screen.blit(self.small_font.render(f'{NAME}: "{taunt}"', True, (205, 150, 255)), (8, 30))

    def _draw_banner(self, engine: VersusEngine, title: str, subtitle: str) -> None:
        height, width = engine.shape[0] * TILE, engine.shape[1] * TILE
        box = self.pygame.Surface((width, 96), self.pygame.SRCALPHA)
        box.fill((10, 10, 20, 215))
        top = self.hud + (height - 96) // 2
        self.screen.blit(box, (0, top))
        for text, font, y in ((title, self.big_font, top + 14), (subtitle, self.small_font, top + 60)):
            surface = font.render(text, True, WHITE)
            self.screen.blit(surface, ((width - surface.get_width()) // 2, y))


class _Quit(Exception):
    pass


def play_versus(
    arena: str = "arena_1",
    difficulty: str = "normal",
    model: str = str(CHAMPION),
    rounds: int = 3,
    tps: int = 7,
    enemies: bool = True,
    player: str = "human",
    seed: int | None = None,
    save_gif: str | None = None,
) -> None:
    """Play best-of-``rounds`` Battle mode against Two-Fuse.

    ``player`` is ``human`` (arrow keys, X or Space to bomb), or a policy spec
    (``heuristic``, ``random``, a model path) to watch a bot take your seat.
    ``save_gif`` records a bot-vs-Two-Fuse match without opening a window.
    """
    human = player == "human"
    if save_gif and human:
        raise ValueError("save_gif needs a bot in the player seat, e.g. --player heuristic")
    layout = load_map(arena)
    match = _Match(
        renderer=VersusRenderer(layout.shape, headless=bool(save_gif), tps=tps),
        layout=layout,
        config=VersusConfig(enemies=enemies),
        rng=np.random.default_rng(seed),
        opponent=two_fuse(difficulty, model),
        me=None if human else make_policy(player, deterministic=False),
        names=("YOU" if human else player.upper()[:10], NAME),
        rounds=rounds,
        tps=tps,
    )
    try:
        match.run()
    except (_Quit, KeyboardInterrupt):
        pass
    finally:
        match.renderer.close()
    if save_gif and match.frames:
        _write_gif(match.frames, Path(save_gif), tps)
        print(f"saved {len(match.frames)} frames to {save_gif}")


class _Match:
    """Best-of-N rounds, either live in a window or recorded headless."""

    def __init__(
        self,
        renderer: VersusRenderer,
        layout: MapLayout,
        config: VersusConfig,
        rng: np.random.Generator,
        opponent: Policy,
        me: Policy | None,
        names: tuple[str, str],
        rounds: int,
        tps: int,
    ):
        self.renderer, self.layout, self.config, self.rng = renderer, layout, config, rng
        self.opponent, self.me, self.names = opponent, me, names
        self.need, self.tps = rounds // 2 + 1, tps
        self.recording = renderer.headless
        self.frames: list[np.ndarray] = []
        self.score = [0, 0]
        self.taunt = ""
        pygame = renderer.pygame
        self.keys = {pygame.K_UP: UP, pygame.K_DOWN: DOWN, pygame.K_LEFT: LEFT, pygame.K_RIGHT: RIGHT}
        self.bomb_keys = (pygame.K_x, pygame.K_SPACE)

    def run(self) -> None:
        """Play matches until the window closes (or one match when a bot plays or we record)."""
        round_no = 0
        while True:
            round_no += 1
            engine = self._play_round(round_no)
            if engine.winner is None:
                title, self.taunt = "DRAW", self._pick("draw")
            else:
                self.score[engine.winner] += 1
                title = f"{self.names[engine.winner]} TAKES ROUND {round_no}"
                self.taunt = self._pick("two_fuse" if engine.winner == 1 else "human")
            cause = engine.players[0].killed_by or engine.players[1].killed_by
            detail = f"{cause.replace('_', ' ')}  |  " if cause else ""
            if max(self.score) < self.need:
                self._show(engine, (title, f"{detail}any key for the next coin flip"), 2.5)
                continue
            winner = self.names[0 if self.score[0] > self.score[1] else 1]
            final = (f"{winner} WINS {max(self.score)}-{min(self.score)}", "any key for a rematch, Esc to quit")
            self._show(engine, final, 3.0)
            if self.recording or self.me is not None:
                return
            self.score, round_no = [0, 0], 0

    def _play_round(self, round_no: int) -> VersusEngine:
        swap = bool(self.rng.random() < 0.5)  # Two-Fuse's coin flip
        engine = VersusEngine(self.layout, self.config, rng=self.rng, swap=swap)
        self.taunt = self._pick("start")
        corner = "bottom-right" if swap else "top-left"
        flip = f"Round {round_no}: {'TAILS' if swap else 'HEADS'}"
        self._show(engine, (flip, f"The coin puts you {corner}. Any key to fight."), 2.0)
        queue: list[int] = []
        next_tick = time.monotonic()
        while not engine.finished:
            if not self.recording:
                self._read_input(queue)
            if self.recording or time.monotonic() >= next_tick:
                next_tick += 1 / self.tps
                warned = engine.sudden_death
                engine.step_versus([self._my_action(engine, queue), self.opponent.act(engine, 1)])
                if engine.sudden_death and not warned:
                    self.taunt = self._pick("sudden")
                if self.recording:
                    self.frames.append(self._draw(engine))
            if not self.recording:
                self._draw(engine)
        return engine

    def _read_input(self, queue: list[int]) -> None:
        pygame = self.renderer.pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                raise _Quit
            if event.type == pygame.KEYDOWN and self.me is None and len(queue) < 3:
                if event.key in self.keys:
                    queue.append(self.keys[event.key])
                elif event.key in self.bomb_keys:
                    queue.append(BOMB)

    def _my_action(self, engine: VersusEngine, queue: list[int]) -> int:
        """A bot's choice, else the next queued key press, else the arrow key being held."""
        if self.me is not None:
            return self.me.act(engine, 0)
        if queue:
            return queue.pop(0)
        held = self.renderer.pygame.key.get_pressed()
        return next((action for key, action in self.keys.items() if held[key]), NOOP)

    def _draw(self, engine: VersusEngine, banner: tuple[str, str] | None = None) -> Any:
        score = (self.score[0], self.score[1])
        return self.renderer.draw_versus(engine, self.names, score, self.taunt, banner)

    def _show(self, engine: VersusEngine, banner: tuple[str, str], seconds: float) -> None:
        """Hold a banner until a key press (a bot seat moves on by itself after ``seconds``)."""
        if self.recording:
            self.frames.extend([self._draw(engine, banner)] * max(1, int(seconds * self.tps)))
            return
        pygame = self.renderer.pygame
        shown = time.monotonic()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    raise _Quit
                if event.type == pygame.KEYDOWN and time.monotonic() - shown > 0.6:
                    return
            if self.me is not None and time.monotonic() - shown > seconds:
                return
            self._draw(engine, banner)

    def _pick(self, kind: str) -> str:
        options = TAUNTS[kind]
        return options[int(self.rng.integers(len(options)))]


def _write_gif(frames: list[np.ndarray], path: Path, fps: int) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    images = [Image.fromarray(frame) for frame in frames]
    images[0].save(path, save_all=True, append_images=images[1:], duration=int(1000 / fps), loop=0, optimize=True)
