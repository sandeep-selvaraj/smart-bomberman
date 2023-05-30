"""Setting up the bomb item used by bomberman"""

from typing import List
import pygame
from .utils.fileutils import import_from_spritesheet
from .constants import BombItem, TileType
from .settings import Game
from . import explosion
from . import level

class Bomb(pygame.sprite.Sprite):
    """
    Encapsulates the bomb item used by the player character in game
    
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, position: List, bomb_range: int,
                 walls: pygame.sprite.Group, display_surface: pygame.Surface):
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
        self.display_surface = display_surface

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
        # pylint: disable=line-too-long
        """get the position of tiles where a bomb explosion is valid"""
        bomb_pos = [self.rect.x, self.rect.y]
        self.explosion_tiles_pos.append(bomb_pos) #center explosion tile
        top_tile_check = True
        bottom_tile_check = True
        left_tile_check = True
        right_tile_check = True
        for i in range(1, self.range+1):
            # top explosion tile
            if ( top_tile_check and
                self._can_explosion_happen_on_tile([bomb_pos[0]-i*Game.TILE_SIZE.value,bomb_pos[1]])):
                self.explosion_tiles_pos.append([bomb_pos[0]-i*Game.TILE_SIZE.value,bomb_pos[1]])
            else:
                top_tile_check = False
            # bottom explosion tile
            if ( bottom_tile_check and
                self._can_explosion_happen_on_tile([bomb_pos[0]+i*Game.TILE_SIZE.value,bomb_pos[1]])):
                self.explosion_tiles_pos.append([bomb_pos[0]+i*Game.TILE_SIZE.value,bomb_pos[1]])
            else:
                bottom_tile_check = False
            # right explosion tile
            if ( right_tile_check and
                self._can_explosion_happen_on_tile([bomb_pos[0],bomb_pos[1]+i*Game.TILE_SIZE.value])):
                self.explosion_tiles_pos.append([bomb_pos[0],bomb_pos[1]+i*Game.TILE_SIZE.value])
            else:
                right_tile_check = False
            # left explosion tile
            if ( left_tile_check and
                self._can_explosion_happen_on_tile([bomb_pos[0],bomb_pos[1]-i*Game.TILE_SIZE.value])):
                self.explosion_tiles_pos.append([bomb_pos[0],bomb_pos[1]-i*Game.TILE_SIZE.value])
            else:
                left_tile_check = False

    def _can_explosion_happen_on_tile(self, explosion_pos: List):
        """
        detemine tile explosion behavior based on 
        1. whether it is a destroyable tile or not
        2. whether it breaks after 2 explosions or not
        3. whether it hides a bomb 
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
                if wall.tile_type == TileType.TWO_EXPLOSION:
                    wall.update_tile_type(TileType.TWO_EXPLOSION, TileType.ONE_EXPLOSION_BOMB)
                elif wall.does_wall_contain_bomb:
                    level.Level.level_bombs.add(
                        Bomb(  [wall.rect.x, wall.rect.y],
                                2,
                                self.walls,
                                self.display_surface
                             ))
                    self.walls.remove(wall)
                else:
                    self.walls.remove(wall)
                return True
        return True

    def render_and_update_explosions(self, level_shift: List):
        """
        render and update explosions caused by bombs placed in the level
        ----------
        Parameters
        ----------
        level_shift: List
            amount the level has shifted in x and y direction
        """
        for expl in self.explosions:
            expl.draw(self.display_surface)
            expl.update(level_shift)

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
        self.render_and_update_explosions(level_shift)
