"""Main file to run the game."""
import sys

import pygame

from . import settings

_SCREEN = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))

def start_game():
    """Run the game."""
    # pylint: disable=no-member
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        _SCREEN.fill("black")
