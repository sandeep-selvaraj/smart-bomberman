"""Main file to run the multiplayer game."""
import sys
import os
from pathlib import Path
from typing import List, Tuple
import csv
import pygame
from stable_baselines3 import PPO
from .multiplayer_level import MultiplayerLevel
from ..settings import GameWindow
from ..constants import ItemType

_SCREEN = pygame.display.set_mode((GameWindow.SCREEN_WIDTH.value, GameWindow.SCREEN_HEIGHT.value))
_MAP_FOLDER = "maps"
_CLOCK = pygame.time.Clock()
_TIMER_DURATION = 300
_WHITE_FONT_TEXT = (255, 255, 255)


def start_game_multiplayer(level_number: int, model1: str, model2: str,ai_training: bool = False):
    """Run the game."""
    # pylint: disable=no-member
    model_1 = PPO.load(f"Training/{model1}")
    model_2 = PPO.load(f"Training/{model2}")
    timeline_players = {}
    pygame.init()
    level_maps = _get_all_levels()
    level_map = MultiplayerLevel(level_maps[level_number - 1], _SCREEN, level_number, number_of_players=2)
    font = pygame.font.Font(pygame.font.get_default_font(), 18)
    extra_time = 0
    if ai_training:
        pygame.display.set_caption("Smart-Bomberman-Training")
        time_remaining, _ = _render_the_game(extra_time, level_map, font)
        time_remaining = 300
    else:
        pygame.display.set_caption("Smart-Bomberman-Multiplayer")
    while True:
        time_remaining = max(0, _TIMER_DURATION + extra_time - pygame.time.get_ticks() // 1000)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        if not level_map.player_alive and 'player_1' not in timeline_players:
            timeline_players["player_1"] = 300 - time_remaining
        if not level_map.player2_alive and 'player_2' not in timeline_players:
            timeline_players["player_2"] = 300 - time_remaining
        if level_map.both_players_died() or time_remaining == 0:
            pygame.time.wait(1000)
            _endgame_screen(font, time_remaining, 2, timeline_players)
            pygame.display.update()
            continue
        if level_map.player_hit_item:
            extra_time += 50
            level_map.player_hit_item = False
        timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
        _SCREEN.fill((128, 128, 128))  # fill bg with grey color
        _SCREEN.blit(timer_text, (10, 10))
        if level_map.player_alive:
            observation_player1 = level_map.get_observation(1)
            player1_action, _ = model_1.predict(observation_player1)
        if level_map.player2_alive:
            observation_player2 = level_map.get_observation(2)
            player2_action, _ = model_2.predict(observation_player2)
        level_map.run(player1_action, player2_action)
        # level_map.run(5, 5)
        _CLOCK.tick(60)
        pygame.display.update()
    else:
        pygame.display.set_caption("Smart-Bomberman")
        while True:
            time_remaining, contine_game = _render_the_game(extra_time, level_map, font)
            if not contine_game:
                continue
            timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
            _SCREEN.fill((128, 128, 128))  # fill bg with grey color
            _SCREEN.blit(timer_text, (10, 10))
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


def _endgame_screen(font, time_remaining, enemies_alive, players_remark):
    """Endgame screen once player is killed."""
    _SCREEN.fill("black")
    text_to_render = ""
    player_1_text = ""
    player_2_text = ""
    if enemies_alive > 0:
        text_to_render = "GAMEOVER"
        player_1_text = f"Player 1 lasted: {players_remark['player_1']} seconds"
        player_2_text = f"Player 2 lasted: {players_remark['player_2']} seconds"
    else:
        text_to_render = "You have killed all the enemies!! <3"
    gameover_text = font.render(text_to_render, True, _WHITE_FONT_TEXT)
    player_1_stats = font.render(player_1_text, True, _WHITE_FONT_TEXT)
    player_2_stats = font.render(player_2_text, True, _WHITE_FONT_TEXT)
    if time_remaining == 0:
        time_up_text = font.render("You ran out of time!", True, _WHITE_FONT_TEXT)
        _SCREEN.blit(time_up_text, (150, 200))
    _SCREEN.blit(gameover_text,  (150, 150))
    _SCREEN.blit(player_1_stats, (150, 250))
    _SCREEN.blit(player_2_stats, (150, 300))


def _render_the_game(extra_time: int, level_map, font) -> Tuple[int, bool]:
    # pylint: disable=no-member
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
        return time_remaining, False
    if level_map.player_hit_enemy or level_map.player_hit_explosion or time_remaining == 0:
        pygame.time.wait(1000)
        _endgame_screen(font, time_remaining, enemies_alive)
        pygame.display.update()
        return time_remaining, False
    if level_map.player_hit_item:
        if level_map.item_class == ItemType.EXTRA_TIME.value:
            extra_time += 50
            time_remaining += extra_time
        level_map.player_hit_item = False
    return time_remaining, True