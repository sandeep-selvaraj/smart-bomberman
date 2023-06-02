"""Main file to run the game."""
import sys
from pathlib import Path
from typing import List
import csv
import pygame
from . import level
from .settings import GameWindow
from .constants import ItemType

_SCREEN = pygame.display.set_mode((GameWindow.SCREEN_WIDTH.value, GameWindow.SCREEN_HEIGHT.value))
_MAP_FOLDER = "maps"
_CLOCK = pygame.time.Clock()
_TIMER_DURATION = 300
_WHITE_FONT_TEXT = (255, 255, 255)
_ITEM_COLOR = [(0, 0, 255), (255, 255, 0), (255, 0, 0)]


def start_game(level_number: int):
    """Run the game."""
    # pylint: disable=no-member
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    pygame.init()
    pygame.display.set_caption("Smart-Bomberman")
    level_maps = _get_all_levels()
    level_map = level.Level(level_maps[level_number - 1], _SCREEN, level_number)
    font = pygame.font.Font(pygame.font.get_default_font(), 18)
    extra_time = 0
    item_start = [0, 0, 0]
    item_seconds = [0, 0, 0]
    item_text = [0, 0, 0]
    item_duration = 15
    while True:
        time_remaining = max(0, _TIMER_DURATION + extra_time - pygame.time.get_ticks() // 1000)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        enemies_alive = level_map.get_enemy_count()
        if level_map.player_hit_gateway:
            pygame.time.wait(1000)
            _endgame_screen(font, time_remaining, enemies_alive)
            pygame.display.update()
            continue
        if level_map.player_hit_enemy or level_map.player_hit_explosion or time_remaining == 0:
            pygame.time.wait(1000)
            _endgame_screen(font, time_remaining, enemies_alive)
            pygame.display.update()
            continue
        if level_map.player_hit_item:
            if level_map.item_class == ItemType.EXTRA_TIME.value:
                extra_time += 30
            for i in ItemType:
                if level_map.item_class == i.value:
                    item_start[i.value] = pygame.time.get_ticks()
                elif level_map.item_class == ItemType.EXTRA_TIME.value:
                    continue
            level_map.player_hit_item = False
        timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
        for i in ItemType:
            if i.value == ItemType.EXTRA_TIME.value:
                continue
            item_seconds[i.value] = (pygame.time.get_ticks() - item_start[i.value])  // 1000
            if item_start[i.value] == 0:
                item_text[i.value] = font.render('', True, _WHITE_FONT_TEXT)
            else:
                if item_seconds[i.value] > item_duration:
                    if i.value == ItemType.SKATE.value:
                        level.Level.player_hit_skate = False
                    elif i.value == ItemType.INVINCIBLE.value:
                        level_map.player_hit_invincible = False
                    item_start[i.value] = 0
                remain = item_duration - item_seconds[i.value]
                item_text[i.value] = font.render(f'{i.name}: {remain}', True, _ITEM_COLOR[i.value])
        _SCREEN.fill((128, 128, 128)) #fill bg with grey color
        _SCREEN.blit(timer_text, (10, 10))
        for i in ItemType:
            if i.value == ItemType.EXTRA_TIME.value:
                continue
            _SCREEN.blit(item_text[i.value], (220+120*i.value, 10))
        level_map.run()
        _CLOCK.tick(60)
        pygame.display.update()


def _get_all_levels() -> List:
    """Read  and store different maps."""
    map_path = Path.cwd().joinpath(_MAP_FOLDER)
    available_level_files = list(map_path.iterdir())
    all_maps = []
    for level_file in available_level_files:
        with open(level_file, newline='', encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            all_maps.append(list(reader))
    return all_maps


def _endgame_screen(font, time_remaining, enemies_alive):
    """Endgame screen once player is killed."""
    _SCREEN.fill("black")
    text_to_render = ""
    if enemies_alive > 0:
        text_to_render = "GAMEOVER"
    else:
        text_to_render = "You have killed all the enemies!! <3"
    gameover_text = font.render(text_to_render, True, _WHITE_FONT_TEXT)
    if time_remaining == 0:
        time_up_text = font.render("You ran out of time!", True, _WHITE_FONT_TEXT)
        _SCREEN.blit(time_up_text, (150, 200))
    _SCREEN.blit(gameover_text,  (150, 150))
