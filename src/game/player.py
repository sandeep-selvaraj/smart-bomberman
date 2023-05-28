"""Setting up the player character, interaction"""

from typing import Tuple, List
import pygame
from .constants import PlayerBomberman, PlayerStatus
from .utils.fileutils import import_from_spritesheet
from . import bomb
from . import level
from .settings import Game

class Player(pygame.sprite.Sprite):
    """
    Encapsulates bomberman ie, player character in game
    
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, position: Tuple, walls: pygame.sprite.Group):
        """ 
        Parameters
        ----------
        position: Tuple
            initial position of the player on map
        walls: pygame.sprite.Group
            group representing all the wall sprites in level
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
        self.rect = self.image.get_rect(topleft = position).inflate(-2,-2)
        self.direction = pygame.math.Vector2(0,0)
        self.speed = PlayerBomberman.SPEED.value
        self.status = PlayerStatus.IDLE
        self.bombs: List = []
        self.bomb_range = PlayerBomberman.BOMB_RANGE.value
        self.bomb_limit = PlayerBomberman.BOMB_LIMIT.value
        self.walls = walls

        # to ensure that holding down bomb deploy button doesnt spam bombs
        self.bomb_deploy_key_pressed = False

        self.level_shifted = [0,0]

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

        if level.Level.player_hit_skate:
            player_vel = 2
        else:
            player_vel = 1

        if keys[pygame.K_RIGHT]:
            self.direction = pygame.math.Vector2(player_vel,0)
        elif keys[pygame.K_LEFT]:
            self.direction = pygame.math.Vector2(-player_vel,0)
        elif keys[pygame.K_UP]:
            self.direction = pygame.math.Vector2(0,-player_vel)
        elif keys[pygame.K_DOWN]:
            self.direction = pygame.math.Vector2(0,player_vel)
        elif ( not keys[pygame.K_RIGHT] and not keys[pygame.K_LEFT]
               and not keys[pygame.K_UP] and not keys[pygame.K_DOWN]):
            # nested if here to ensure player stops to place the bomb, cant place bomb when moving
            self.direction = pygame.math.Vector2(0,0)
            if ( keys[pygame.K_x] and len(self.bombs) < self.bomb_limit
                                  and not self.bomb_deploy_key_pressed ):
                self.bomb_deploy_key_pressed = True
                temp_bomb = pygame.sprite.GroupSingle()
                temp_bomb.add(self.deploy_bomb())
                self.bombs.append(temp_bomb)
            elif not keys[pygame.K_x]:
                self.bomb_deploy_key_pressed = False

    def player_status(self):
        """sets the player status based on movement"""
        if self.direction.length() != 0:
            self.status = PlayerStatus.RUN
        else:
            self.status = PlayerStatus.IDLE

    def deploy_bomb(self) -> pygame.sprite.Sprite:
        """places the bomb on level"""
        bomb_deploy_pos = self._get_grid_aligned_bomb_position([self.rect.x, self.rect.y])
        return bomb.Bomb(bomb_deploy_pos, self.bomb_range, self.walls)

    def _clean_up_bombs_after_explosion(self):
        """remove bombs which have been exploded from players internal list"""
        for temp_bomb in self.bombs.copy():
            if temp_bomb.sprite.has_explosion_ended:
                self.bombs.remove(temp_bomb)

    def _get_grid_aligned_bomb_position(self, position):
        """grid align the bombs based on level shift and offset"""
        # pylint: disable=too-many-branches
        # calculate level offset based on overall level shift
        level_offset = [0,0]
        if (abs(self.level_shifted[0])%Game.TILE_SIZE.value) != 0:
            level_offset[0] = Game.TILE_SIZE.value-(abs(self.level_shifted[0])%Game.TILE_SIZE.value)
        if (abs(self.level_shifted[1])%Game.TILE_SIZE.value) != 0:
            level_offset[1] = Game.TILE_SIZE.value-(abs(self.level_shifted[1])%Game.TILE_SIZE.value)
        # add offset to current bomb position
        if self.level_shifted[0] < 0:
            position[0] -= level_offset[0]
        elif self.level_shifted[0] > 0:
            position[0] += level_offset[0]
        if self.level_shifted[1] < 0:
            position[1] -= level_offset[1]
        elif self.level_shifted[0] > 0:
            position[1] += level_offset[1]
        # grid alignment code below - based on tile size
        grid_aligned_pos = position
        if position[0] % Game.TILE_SIZE.value != 0:
            if position[0] % Game.TILE_SIZE.value < (Game.TILE_SIZE.value // 2):
                grid_aligned_pos[0] = position[0] - (position[0]%Game.TILE_SIZE.value)
            else:
                grid_aligned_pos[0] = ( Game.TILE_SIZE.value +
                                      ((position[0] // Game.TILE_SIZE.value)*Game.TILE_SIZE.value))
        if position[1] % Game.TILE_SIZE.value != 0:
            if position[1] % Game.TILE_SIZE.value < (Game.TILE_SIZE.value // 2):
                grid_aligned_pos[1] = position[1] - (position[1]%Game.TILE_SIZE.value)
            else:
                grid_aligned_pos[1] = ( Game.TILE_SIZE.value +
                                      ((position[1] // Game.TILE_SIZE.value)*Game.TILE_SIZE.value))
        # add the level offset back after grid alignment
        if self.level_shifted[0] < 0:
            grid_aligned_pos[0] += level_offset[0]
        elif self.level_shifted[0] > 0:
            grid_aligned_pos[0] -= level_offset[0]
        if self.level_shifted[1] < 0:
            grid_aligned_pos[1] += level_offset[1]
        elif self.level_shifted[0] > 0:
            grid_aligned_pos[1] -= level_offset[1]
        return grid_aligned_pos

    def update(self):
        """
        updates player state like position based on input
        """
        self.player_input()
        self.player_status()
        self.animate()
        self._clean_up_bombs_after_explosion()
