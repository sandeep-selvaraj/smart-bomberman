"""Package to create the environment for AI Agent training."""
from pathlib import Path
import csv
from typing import List
import gymnasium
import pygame
from .. import level
from ..settings import GameWindow

# pylint: disable=duplicate-code
_SCREEN = pygame.display.set_mode((GameWindow.SCREEN_WIDTH.value, GameWindow.SCREEN_HEIGHT.value))
_MAP_FOLDER = "maps"
_CLOCK = pygame.time.Clock()
_TIMER_DURATION = 300
_WHITE_FONT_TEXT = (255, 255, 255)


class BombermanGameEnv(gymnasium.Env):
    """Custom game environment for the game."""
    def __init__(self):
        self.level_maps = _get_all_levels()
        # Create an instance of the Level class
        self.level = level.Level(self.level_maps[1 - 1], _SCREEN, 1)
        self.action_space = gymnasium.spaces.Discrete(6)  # Example: Six possible actions
        self.observation_space = gymnasium.spaces.Box(low=0, high=255, shape=(416,), dtype=int)
        # self.observation_space = gymnasium.spaces.Dict({
        #     "player_position": gymnasium.spaces.Box(low=0, high=33, shape=(2,)),
        #     "bomb_position": gymnasium.spaces.Box(low=0, high=33, shape=(2,)),
        #     "enemy_positions": gymnasium.spaces.Box(low=0, high=33, shape=(2,))
        # })
        # self.seed()
        # self.reset()
        self.policy_parameters = None
        self.current_step = 0
        self.max_episode_length = 3000

    def seed(self, seed=None):
        """Seeding parameters."""
        # self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self, seed=None, options=None):
        # pylint: disable=arguments-differ
        # self.level.load_level()  # Load a new level
        self.level.reset()  # Reset the level
        # return self.level.initial_obs()
        return self.level.get_observation(), {}  # Return the initial observation

    def step(self, action):
        # assert self.action_space.contains(action), "Invalid action"
        # action_dict = {0: "Up", 1: "Down", 2: "left", 3:"right", 5: "bomb", 4:"wait"}
        observation = self.level.get_observation()  # Get the new observation
        self.level.update_by_agent(action)  # Update the level based on the action
        reward = self.level.get_reward()  # Get the reward
        done = self.level.is_done()  # Check if the episode is done
        self.render() # rendering on/off
        # print(reward)
        truncated = False
        self.current_step += 1
        if self.current_step > self.max_episode_length:
            truncated = True
            self.current_step = 0
        return observation, reward, done, truncated, {}

    def render(self, mode='human'):
        # pylint: disable=duplicate-code
        # pylint: disable=no-member
        if mode == 'human':
            pass
        pygame.init()
        pygame.display.set_caption("Smart-Bomberman-Training")
        font = pygame.font.Font(pygame.font.get_default_font(), 18)
        time_remaining = 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()

        enemies_alive = self.level.get_enemy_count()
        if self.level.player_hit_gateway:
            # pygame.time.wait(1000)
            _endgame_screen(font, time_remaining, enemies_alive)
            pygame.display.update()
        if self.level.player_hit_enemy or \
                self.level.player_hit_explosion:  # or time_remaining == 0:
            # pygame.time.wait(1000)
            _endgame_screen(font, time_remaining, enemies_alive)
            pygame.display.update()
        timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
        _SCREEN.fill((128, 128, 128))  # fill bg with grey color
        _SCREEN.blit(timer_text, (10, 10))
        self.level.run()
        self.draw_nn_visual()
        _CLOCK.tick(60)

        pygame.display.update()

    def update_policy_parameters(self, policy_parameters):
        """Store the updated the weights of the neural network."""
        # Update the policy parameters in the environment
        # You can store the parameters in an instance variable
        self.policy_parameters = policy_parameters

    def draw_nn_visual(self):
        """To draw the neural network visual."""

        # plt.ion()
        # if self.policy_parameters:
        #     display.clear_output()
        #     display.display(plt.gcf())
        #     ax.axis('off')
        #     neural_net_data = get_restructured_neural_net(self.policy_parameters)
        #     neural_net_shape = [len(val) for val in neural_net_data]
        #     # draw_neural_net(ax, .1, .9, .1, .9, neural_net_shape, neural_net_data)
        #     test_data = []
        #     test_data.append(np.array([0, 0.4, 0.5, 0.7]))
        #     test_data.append(np.array([0, 0.4, 0.7]))
        #     test_data.append(np.array([0.8]))
        #     draw_neural_net(ax, .1, .9, .1, .9, [4, 3, 1], test_data)
        #     plt.show(block=False)

    def close(self):
        # pylint: disable=no-member
        pygame.quit()


def _get_all_levels() -> List:
    """Read  and store different maps."""
    # pylint: disable=duplicate-code
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
    # pylint: disable=duplicate-code
    _SCREEN.fill("black")
    # text_to_render = ""
    if enemies_alive > 0:
        text_to_render = "GAMEOVER"
    else:
        text_to_render = "You have killed all the enemies!! <3"
    gameover_text = font.render(text_to_render, True, _WHITE_FONT_TEXT)
    if time_remaining == 0:
        time_up_text = font.render("You ran out of time!", True, _WHITE_FONT_TEXT)
        _SCREEN.blit(time_up_text, (150, 200))
    _SCREEN.blit(gameover_text,  (150, 150))
