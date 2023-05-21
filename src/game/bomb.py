"""Setting up the bomb item used by bomberman"""

from typing import Tuple, List
import pygame
from .utils.fileutils import import_from_spritesheet
from .constants import BombItem
from .settings import Game
from . import explosion

class Bomb(pygame.sprite.Sprite):
    """
    Encapsulates the bomb item used by the player character in game
    
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, position: Tuple, bomb_range: int, walls: pygame.sprite.Group):
        """ 
        Parameters
        ----------
        position: Tuple
            initial position of the bomb on map
        walls: pygame.sprite.Group
            group representing all the wall sprites in level
        """
        super().__init__()

        #animation inits
        self.build_bomb_animations()
        self.animation_speed = BombItem.ANIMATION_SPEED.value
        self.frame_index = 0
        self.image = self.animations[self.frame_index]
        self.rect = self.image.get_rect(topleft = position)
        self.start_time = pygame.time.get_ticks()
        self.range = bomb_range
        self.explosion_tiles_pos: List = []
        self.explosions: List = []
        self.elapsed_time = 0
        self.has_bomb_exploded = False
        self.has_explosion_ended = False
        self.walls = walls

    def build_bomb_animations(self):
        """
        creates an internal list of bomb's pre explosion state animation
        """
        self.animations = []
        bomb_sprites = import_from_spritesheet('graphics/bomb.png',
                                                    BombItem.SPRITE_WIDTH.value,
                                                    BombItem.SPRITE_HEIGHT.value
                                                 )
        self.animations = bomb_sprites

    def animate(self):
        """plays the bomb animation"""
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.animations):
            self.frame_index = 0
        self.image = self.animations[int(self.frame_index)]

    def _get_bomb_explosion_tiles(self):
        """get the position of tiles where a bomb explosion is valid"""
        bomb_pos = [self.rect.x, self.rect.y]
        self.explosion_tiles_pos.append(bomb_pos) #center explosion tile
        for i in range(1, self.range+1):
            # top explosion tile
            if self._can_explosion_happen_on_tile([bomb_pos[0]-i*Game.TILE_SIZE.value,bomb_pos[1]]):
                self.explosion_tiles_pos.append([bomb_pos[0]-i*Game.TILE_SIZE.value,bomb_pos[1]])
            # bottom explosion tile
            if self._can_explosion_happen_on_tile([bomb_pos[0]+i*Game.TILE_SIZE.value,bomb_pos[1]]):
                self.explosion_tiles_pos.append([bomb_pos[0]+i*Game.TILE_SIZE.value,bomb_pos[1]])
            # right explosion tile
            if self._can_explosion_happen_on_tile([bomb_pos[0],bomb_pos[1]+i*Game.TILE_SIZE.value]):
                self.explosion_tiles_pos.append([bomb_pos[0],bomb_pos[1]+i*Game.TILE_SIZE.value])
            # left explosion tile
            if self._can_explosion_happen_on_tile([bomb_pos[0],bomb_pos[1]-i*Game.TILE_SIZE.value]):
                self.explosion_tiles_pos.append([bomb_pos[0],bomb_pos[1]-i*Game.TILE_SIZE.value])

    def _can_explosion_happen_on_tile(self, explosion_pos: List):
        """
        detemine if an explosion can occur on a tile or not based on whether is a destroyable
        tile or not 
        ----------
        Parameters
        ----------
        explosion_pos: List
            coordinates of the bomb explosion
        """
        for wall in self.walls:
            if wall.rect.x == explosion_pos[0] and wall.rect.y == explosion_pos[1]:
                if not wall.destroyable:
                    return False
                self.walls.remove(wall)
                return True
        return True

    def update(self, level_shift: List):
        """
        updates bomb state
        ----------
        Parameters
        ----------
        level_shift: List
            amount the level has shifted in x and y direction
        """
        self.animate()
        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]

        self.elapsed_time = (pygame.time.get_ticks() - self.start_time) // 1000
        if ( self.elapsed_time >= BombItem.EXPLOSION_TIME_DURATION.value and
             not self.has_bomb_exploded ):
            # bomb explodes here
            self.has_bomb_exploded = True
            self._get_bomb_explosion_tiles()
            for _, exp_tile_pos in enumerate(self.explosion_tiles_pos):
                a_explosion: pygame.sprite.GroupSingle = pygame.sprite.GroupSingle()
                a_explosion.add(explosion.Explosion(exp_tile_pos))
                self.explosions.append(a_explosion)
        if ( self.elapsed_time >= BombItem.EXPLOSION_END_TIME_DURATION.value and
             not self.has_explosion_ended ):
            # bomb explosion ends here
            self.has_explosion_ended = True
