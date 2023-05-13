"""Setting up the player character, interaction"""

from typing import Tuple
import pygame
from .constants import PlayerBomberman, PlayerStatus
from .utils.fileutils import import_from_spritesheet

class Player(pygame.sprite.Sprite):
    """
    Encapsulates bomberman ie, player character in game
    
    """
    # pylint: disable=too-many-instance-attributes

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

        #animation inits
        self.build_player_animation_spritesheet()
        self.frame_index = 0
        self.animation_speed = PlayerBomberman.ANIMATION_SPEED.value
        self.image = self.animations[PlayerStatus.IDLE][self.frame_index]

        #reduce the size of the bounding box of player for easier player manueverability
        self.rect = self.image.get_rect(topleft = position).inflate(-2, -2)
        self.direction = pygame.math.Vector2(0,0)
        self.speed = PlayerBomberman.SPEED.value
        self.status = PlayerStatus.IDLE

    def build_player_animation_spritesheet(self):
        """creates an internal dictionary of player state animations"""
        self.animations = {PlayerStatus.IDLE: [], PlayerStatus.RUN: []}
        player_sprites = import_from_spritesheet('graphics/player.png',
                                                    PlayerBomberman.SPRITE_WIDTH.value,
                                                    PlayerBomberman.SPRITE_HEIGHT.value
                                                 )

        self.animations[PlayerStatus.IDLE].append(player_sprites[1])
        self.animations[PlayerStatus.RUN] = player_sprites

    def animate(self):
        """runs the player animations based on player status"""
        animation = self.animations[self.status]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0

        self.image = animation[int(self.frame_index)]


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

    def player_status(self):
        """sets the player status based on movement"""
        if self.direction.length() != 0:
            self.status = PlayerStatus.RUN
        else:
            self.status = PlayerStatus.IDLE

    def update(self):
        """
        updates player state like position based on input
        """
        self.player_input()
        self.player_status()
        self.animate()
