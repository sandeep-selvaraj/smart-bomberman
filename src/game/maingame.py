"""Main file to run the game."""
import sys
from pathlib import Path
from typing import List
import csv
import pygame
from . import level
from .settings import GameWindow
from .constants import ItemType, GameFinalState
from .ai.ppo.train_agent_ppo import train
from .ai.ppo.infer_agent_ppo import infer 
from .ai.ppo.train_agent_ppo import train_opt
from .ai.ppo.infer_agent_ppo import infermultiplayer
#from .ai.ppo.evolve import run, infer

_SCREEN = pygame.display.set_mode((GameWindow.SCREEN_WIDTH.value, GameWindow.SCREEN_HEIGHT.value))
_MAP_FOLDER = "maps"
_CLOCK = pygame.time.Clock()
_TIMER_DURATION = 200
_WHITE_FONT_TEXT = (255, 255, 255)
_ITEM_COLOR = [(0, 0, 255), (255, 255, 0), (255, 0, 0)]

class MainGame:
    def __init__(self, level_number: int):
        self.level_number = level_number
        self.game_final_state = GameFinalState.NONE
        self.type_run = "play"
    
    def start_game(self, type_run='play'):
        """Run the game."""
        # pylint: disable=no-member
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        self.type_run = type_run
        pygame.init()
        pygame.display.set_caption("Smart-Bomberman")
        level_maps = self._get_all_levels()
        self.level_map = level.Level(level_maps[self.level_number - 1], _SCREEN, self.level_number, self.type_run)
        self.initial_time = pygame.time.get_ticks()
        font = pygame.font.Font(pygame.font.get_default_font(), 18)
        extra_time = 0
        item_start = [0, 0, 0]
        item_seconds = [0, 0, 0]
        item_text = [font.render('', True, 0), font.render('', True, 0), font.render('', True, 0)]
        item_duration = 15
        if self.type_run == 'play':
            while True:
                self.render_frame(font, extra_time, item_start, item_seconds, item_text, item_duration)
        elif self.type_run == 'train':
            #train_opt(self)
            train(self)
            #run(self)
        elif self.type_run == 'infer':
            infer(self)
        elif self.type_run == 'multi':
            infermultiplayer(self)
    
    def render_frame(self, font, extra_time, item_start, item_seconds, item_text, item_duration):
        #print("render inside")
        current_time = pygame.time.get_ticks()
        elapsed_time = (current_time-self.initial_time) // 1000
        self.time_remaining = max(0, _TIMER_DURATION + extra_time - elapsed_time)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        enemies_alive = self.level_map.get_enemy_count()
        if self.level_map.player_hit_gateway:
            pygame.time.wait(1000)
            self._endgame_screen(font, self.time_remaining, enemies_alive)
            self.game_final_state = GameFinalState.WIN
            pygame.display.update()
            return
        if self.level_map.player_hit_enemy or self.level_map.player_hit_explosion or self.time_remaining == 0:
            pygame.time.wait(1000)
            self._endgame_screen(font, self.time_remaining, enemies_alive)
            self.game_final_state = GameFinalState.LOSE
            pygame.display.update()
            return
        if self.level_map.player_hit_item:
            if self.level_map.item_class == ItemType.EXTRA_TIME.value:
                extra_time += 30
            for i in ItemType:
                if self.level_map.item_class == i.value:
                    item_start[i.value] = pygame.time.get_ticks()
                elif self.level_map.item_class == ItemType.EXTRA_TIME.value:
                    continue
            self.level_map.player_hit_item = False
        timer_text = font.render(f'Time Remaining: {self.time_remaining}', True, _WHITE_FONT_TEXT)
        for i in ItemType:
            if i.value == ItemType.EXTRA_TIME.value:
                continue
            item_seconds[i.value] = (pygame.time.get_ticks() - item_start[i.value])  // 1000
            if item_start[i.value] == 0:
                item_text[i.value] = font.render('', True, 0)
            else:
                if item_seconds[i.value] > item_duration:
                    if i.value == ItemType.SKATE.value:
                        level.Level.player_hit_skate = False
                    elif i.value == ItemType.INVINCIBLE.value:
                        self.level_map.player_hit_invincible = False
                    item_start[i.value] = 0
                remain = item_duration - item_seconds[i.value]
                item_text[i.value] = font.render(f'{i.name}: {remain}', True, _ITEM_COLOR[i.value])
        _SCREEN.fill((128, 128, 128)) #fill bg with grey color
        _SCREEN.blit(timer_text, (10, 10))
        for i in ItemType:
            if i.value == ItemType.EXTRA_TIME.value:
                continue
            _SCREEN.blit(item_text[i.value], (220+120*i.value, 10))
        self.level_map.run()
        _CLOCK.tick(60)
        pygame.display.update()

    def reset_game(self):
        self.initial_time = pygame.time.get_ticks()
        level_maps = self._get_all_levels()
        self.level_map = level.Level(level_maps[self.level_number - 1], _SCREEN, self.level_number, self.type_run)
        self.game_final_state = GameFinalState.NONE

    def _get_all_levels(self) -> List:
        """Read  and store different maps."""
        map_path = Path.cwd().joinpath(_MAP_FOLDER)
        available_level_files = list(map_path.iterdir())
        all_maps = []
        for level_file in available_level_files:
            with open(level_file, newline='', encoding="utf-8-sig") as file:
                reader = csv.reader(file)
                all_maps.append(list(reader))
        return all_maps


    def _endgame_screen(self, font, time_remaining, enemies_alive):
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
