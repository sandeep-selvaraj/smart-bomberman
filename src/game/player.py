"""Setting up the player character, interaction"""

from typing import Tuple
import pygame
from .settings import PlayerBomberman

class Player(pygame.sprite.Sprite):
    """
    Encapsulates bomberman ie, player character in game
    
    """

    def __init__(self, position: Tuple):
        """ 
        Parameters
        ----------
        position: Tuple
            initial position of the player on map
        """
        # pylint: disable=no-member
        # pylint: disable=c-extension-no-member
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill('red')
        self.rect = self.image.get_rect(topleft = position)
        self.direction = pygame.math.Vector2(0,0)
        self.speed = PlayerBomberman.SPEED.value

    def player_input(self):
        """
        handles player input for interaction
        """
        # pylint: disable=no-member
        # pylint: disable=c-extension-no-member
        keys = pygame.key.get_pressed()

        if keys[pygame.K_RIGHT]:
            self.direction = pygame.math.Vector2(1,0)
        elif keys[pygame.K_LEFT]:
            self.direction = pygame.math.Vector2(-1,0)
        elif keys[pygame.K_UP]:
            self.direction = pygame.math.Vector2(0,-1)
        elif keys[pygame.K_DOWN]:
            self.direction = pygame.math.Vector2(0,1)
        else:
            self.direction = pygame.math.Vector2(0,0)

    def update(self):
        """
        updates player state like position based on input
        """
        self.player_input()
