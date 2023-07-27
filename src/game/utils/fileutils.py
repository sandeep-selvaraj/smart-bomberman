"""utility code related to file reading/writing like sprite, spritesheet loading"""
# pylint: disable=cyclic-import
from typing import List
import pygame

def import_sprite(path: str) -> pygame.Surface:
    """
    reads a single sprite from the specified location

    Parameters
    ----------
    path: str
        path of the sprite
    """
    return pygame.image.load(path)

def import_from_spritesheet(path: str, sprite_width: int,
                            sprite_height: int) -> List[pygame.Surface]:
    """
    reads and returns a list of sprite(in surface format) corresponding to the 
    individual sprites in the sprite sheet
    
    Parameters
    ----------
    path: str
        path of the sprite sheet
    sprite_width: int
        width of the individual sprite in the spritesheet
    sprite_height: int
        height of the individual sprite in the spritesheet
    """
    sprite_sheet = import_sprite(path)
    #sprite_width = PlayerBomberman.SPRITE_WIDTH
    #sprite_height = PlayerBomberman.SPRITE_HEIGHT

    num_frames = sprite_sheet.get_width() // sprite_width

    sprite_list = []

    for i in range(num_frames):
        frame_rect = pygame.Rect(i * sprite_width, 0, sprite_width, sprite_height)
        frame_surface = pygame.Surface(frame_rect.size)
        frame_surface.blit(sprite_sheet, (0,0), frame_rect)
        frame_surface.set_colorkey((0,0,0))
        sprite_list.append(frame_surface)

    return sprite_list
