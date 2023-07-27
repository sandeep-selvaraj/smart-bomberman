"""Setting up the Enemy character."""

import math
import pygame
from .utils.fileutils import import_from_spritesheet
from .constants import EnemyStatus, EnemyBomberman
# from .algorithms import a_star


class Enemy(pygame.sprite.Sprite):
    """
    Defining enemy characteristics.

    Parameters
    ----------
    postion [Tuple] : To place the enemy on a certain point
    """

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=superfluous-parens
    # pylint: disable=unused-argument
    # pylint: disable=line-too-long

    def __init__(self, position, level_number):
        pygame.sprite.Sprite.__init__(self)
        self.build_enemy_animation()
        self.image = self.animations[EnemyStatus.IDLE][0]
        self.rect = self.image.get_rect(topleft=position)
        self.direction = -1
        self.current_location = (None, None)
        self.hit_by_bomb = False
        self.set_life(level_number)
        self.pause = 0
        self.prev_move = 1 # 0 for horizontal 1 for vertical
        self.timer = 150

    def build_enemy_animation(self):
        """Animate the enemy movements."""
        self.animations = {EnemyStatus.IDLE: [], EnemyStatus.MOVE: []}
        enemy_sprites = import_from_spritesheet('graphics/enemy.png',
                                                EnemyBomberman.SPRITE_HEIGHT.value,
                                                EnemyBomberman.SPRITE_WIDTH.value
                                                )
        color_different_enemy = import_from_spritesheet('graphics/enemy_later.png',
                                                        EnemyBomberman.SPRITE_HEIGHT.value,
                                                        EnemyBomberman.SPRITE_WIDTH.value
                                                        )
        self.animations[EnemyStatus.IDLE].append(enemy_sprites[1])
        self.animations[EnemyStatus.MOVE].append(color_different_enemy[1])

    def enemy_movement(self, path_to_player, h_ava, v_ava):
        """Adding directions specific positioning of the enemy."""
        # _ = path_to_player  # To be removed
        # if path_to_player:
        #     x_direction, y_direction = path_to_player
        #     x_current, y_current = self.current_location
        #     y_difference = (y_direction - y_current)
        #     if y_difference != 0:
        #         self.rect.y += y_difference
        #     else:
        #         self.rect.x += (x_direction - x_current)
        # else:
        #     self.rect.x += self.direction
        if self.timer > 75:
            if h_ava:
                self.rect.x += self.direction
                self.prev_move = 0
            elif (not h_ava and not v_ava):
                if (self.prev_move == 0):
                    self.rect.x += self.direction
                    self.prev_move = 0
                else:
                    self.rect.y += self.direction
                    self.prev_move = 1
            else:
                self.rect.y += self.direction
                self.prev_move = 1
        else:
            if v_ava:
                self.rect.y += self.direction
                self.prev_move = 1
            elif (not h_ava and not v_ava):
                if (self.prev_move == 0):
                    self.rect.x += self.direction
                    self.prev_move = 0
                else:
                    self.rect.y += self.direction
                    self.prev_move = 1
            else:
                self.rect.x += self.direction
                self.prev_move = 0
        

    def enemy_collision(self):
        """Reverse the enemy once it collides with a wall"""
        self.direction *= -1

    def enemy_hit_by_bomb(self):
        """Update flag if enemy is hit by bomb."""
        # self.pause = True
        if self.life == 0:
            self.hit_by_bomb = True

    def get_location_on_map(self) -> list:
        """Get player location on the map."""
        return [math.ceil(self.rect.x / EnemyBomberman.SPRITE_HEIGHT.value), \
            math.ceil(self.rect.y / EnemyBomberman.SPRITE_WIDTH.value)]

    def set_pause(self, time_frame):
        """Pause the enemy sprite once it hits the bomb."""
        self.life -= 1
        self.pause = 3 * time_frame
        if self.life == 0:
            self.change_color()

    def is_paused(self) -> bool:
        """Check if the enemy paused after hitting the bomb."""
        if self.pause:
            return True
        return False

    def set_life(self, level_number: int):
        """Set enemy lives based on difficulty of level."""
        if level_number > 0:
            self.life = 0 #1
        else:
            self.life = 0

    def change_color(self):
        """Change enemy color once it's come in contact with bomb."""
        self.image = self.animations[EnemyStatus.MOVE][0]

    def update(self, level_shift, unavailable_move, acc_shift) -> None:
        """
        Updating the status of the enemy on the map per frame.

        Parameters
        ----------
        level_shift [Tuple] : The position of the enemy
        """
        ava_list = []
        vertical_avail = False
        horizontal_avail = False

        self.timer = self.timer - 1
        self.rect.x += level_shift[0]
        self.rect.y += level_shift[1]


        self.current_location = self.get_location_on_map()
        self.current_location[0] = self.current_location[0]+((-1)*math.ceil(acc_shift[0]/32))

        ava_list.append((self.current_location[1]+1,self.current_location[0]))
        ava_list.append((self.current_location[1]-1,self.current_location[0]))
        ava_list.append((self.current_location[1],self.current_location[0]+1))
        ava_list.append((self.current_location[1],self.current_location[0]-1))

        if (((ava_list[0] not in unavailable_move) or (ava_list[1] not in unavailable_move)) and self.rect.x-acc_shift[0] == self.current_location[0]*32 and self.rect.y-acc_shift[1] == self.current_location[1]*32):
            vertical_avail = True
        if (((ava_list[2] not in unavailable_move) or (ava_list[3] not in unavailable_move)) and self.rect.x-acc_shift[0] == self.current_location[0]*32 and self.rect.y-acc_shift[1] == self.current_location[1]*32):
            horizontal_avail = True

        # path = a_star.get_path(mapdata, player_location, self.current_location)
        next_path = None
        # if path:
        #     *_, next_path, _ = path
        if self.pause:
            self.pause -= 1
        if self.hit_by_bomb and not self.pause:
            self.kill()

        if self.pause == 0:
            self.enemy_movement(next_path, horizontal_avail, vertical_avail)
        if (self.timer == 0):
            self.timer = 150
