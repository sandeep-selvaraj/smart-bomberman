"""Draw the headless engine with the game's own sprites."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from .engine import Engine

TILE = 32
HUD = 32
GRAPHICS = Path(__file__).resolve().parents[2] / "graphics"


class Renderer:
    """Pygame view of an ``Engine``. In headless mode it only produces RGB arrays."""

    def __init__(
        self,
        grid_shape: tuple[int, int],
        headless: bool = False,
        hud: int = HUD,
        caption: str = "Smart-Bomberman - agent",
    ):
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame

        self.pygame = pygame
        pygame.init()
        height, width = grid_shape
        self.hud = hud
        size = (width * TILE, height * TILE + hud)
        if headless:
            self.screen = pygame.Surface(size)
        else:
            self.screen = pygame.display.set_mode(size)
            pygame.display.set_caption(caption)
        self.headless = headless
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(pygame.font.get_default_font(), 16)
        self.sprites = self._load_sprites()

    def _frame(self, name: str, index: int = 0) -> Any:
        sheet = self.pygame.image.load(str(GRAPHICS / f"{name}.png"))
        surface = self.pygame.Surface((TILE, TILE))
        surface.blit(sheet, (0, 0), self.pygame.Rect(index * TILE, 0, TILE, TILE))
        surface.set_colorkey((0, 0, 0))
        return surface

    def _load_sprites(self) -> dict[str, Any]:
        load = self.pygame.image.load
        door = self.pygame.transform.scale(load(str(GRAPHICS / "blackhole_1.png")), (TILE, TILE))
        return {
            "wall": load(str(GRAPHICS / "wall.png")),
            "breakable": load(str(GRAPHICS / "destrWall.png")),
            "cracked": load(str(GRAPHICS / "destrWall_1.png")),
            "explosion": load(str(GRAPHICS / "explosion.png")),
            "bomb": self._frame("bomb"),
            "enemy": self._frame("enemy", 1),
            "player": self._frame("player"),
            "door": door,
        }

    def draw(self, engine: Engine, fps: int = 8) -> np.ndarray | None:
        """Draw one frame. Returns an RGB array in headless mode."""
        pygame = self.pygame
        if not self.headless:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
        screen, sprites = self.screen, self.sprites
        screen.fill((128, 128, 128))
        height, width = engine.shape

        def at(cell):
            return cell[1] * TILE, cell[0] * TILE + HUD

        for r in range(height):
            for c in range(width):
                if engine.solid[r, c]:
                    screen.blit(sprites["wall"], at((r, c)))
                elif engine.wall_hp[r, c] > 0:
                    key = "cracked" if engine.wall_hp[r, c] == 1 and engine.layout.wall_hp[r, c] == 2 else "breakable"
                    screen.blit(sprites[key], at((r, c)))
        door = sprites["door"]
        if not engine.door_open:
            door = door.copy()
            door.set_alpha(80)
        screen.blit(door, at(engine.door))
        for bomb in engine.bombs:
            screen.blit(sprites["bomb"], at(bomb.cell))
        for r, c in np.argwhere(engine.flames > 0):
            screen.blit(sprites["explosion"], at((r, c)))
        for enemy in engine.enemies:
            if enemy.alive:
                screen.blit(sprites["enemy"], at(enemy.cell))
        if engine.alive:
            screen.blit(sprites["player"], at(engine.player))

        status = "WON" if engine.won else ("DEAD" if not engine.alive else "")
        hud = (
            f"{engine.layout.name}   step {engine.steps}/{engine.config.max_steps}   "
            f"enemies {engine.enemies_alive}/{engine.initial_enemies}   "
            f"door {'open' if engine.door_open else 'closed'}   {status}"
        )
        screen.blit(self.font.render(hud, True, (255, 255, 255)), (8, 8))

        if self.headless:
            return np.transpose(pygame.surfarray.array3d(screen), (1, 0, 2))
        pygame.display.flip()
        self.clock.tick(fps)
        return None

    def close(self) -> None:
        """Shut pygame down."""
        self.pygame.quit()
