"""Package to create the environment for AI Agent training."""
from pathlib import Path
import dash
from dash import dcc
from dash import html
from dash.dependencies import Output, Input
import plotly.express as px
import threading
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import csv
from typing import List, Optional
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
# matplotlib.use('QTAgg')
plt.show()

class BombermanGameEnv(gymnasium.Env):
    """Custom game environment for the game."""
    def __init__(self, no_of_players: Optional[int] = 1):
        self.level_maps = _get_all_levels()
        # Create an instance of the Level class
        self.level = level.Level(self.level_maps[1 - 1], _SCREEN, 1, number_of_players=no_of_players)
        self.action_space = gymnasium.spaces.Discrete(6)  # Example: Six possible actions
        # initial_observation = {
        #     "grid": np.zeros((13, 31, 1)),  # Initialize the grid with zeros
        #     "player_position": 0,  # Initialize the player position
        #     "bomb_status": 0,
        #     "enemy_positions": np.zeros((3, 0, 0))  # Initialize the enemy positions with zeros
        # }
        initial_observation = gymnasium.spaces.Dict({
            "grid": gymnasium.spaces.Box(low=0, high=7, shape=(416,)),
            "player_position": gymnasium.spaces.Box(low=0, high=33, shape=(2,)),
            "bomb_position": gymnasium.spaces.Box(low=0, high=33, shape=(2,)),
            "enemy_positions": gymnasium.spaces.Box(low=0, high=33, shape=(3,2,)),
            "bomb_explosion_location": gymnasium.spaces.Box(low=0, high=33, shape=(5,2,)),
            "bomb_present": gymnasium.spaces.Discrete(2),
            "explosion": gymnasium.spaces.Discrete(2),
            'bombing_possibility': gymnasium.spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32)
        })

        self.observation_space = initial_observation
        # self.observation_space = gymnasium.spaces.Box(low=0, high=8, shape=(416,), dtype=int)
        # self.seed()
        # self.reset()
        self.policy_parameters = None
        self.current_step = 0
        self.max_episode_length = 7000
        self.dash_thread = threading.Thread(target=self.run_dash_app)
        self.dash_thread.start()
        self.recent_action = 0
        self.map_data = []

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
        self.level.update_by_agent(action)  # Update the level based on the action
        # print(action)
        self.recent_action = action
        reward = self.level.get_reward()  # Get the reward
        done = self.level.is_done()  # Check if the episode is done
        observation = self.level.get_observation()  # Get the new observation
        # self.render(None)
        self.render("human")
        self.map_data = self.level.map_data
        truncated = False
        self.current_step += 1
        if self.current_step > self.max_episode_length:
            truncated = True
            self.current_step = 0
        return observation, reward, done, truncated, {}

    def render(self, mode='human'):
        # pylint: disable=duplicate-code
        # pylint: disable=no-member
        if mode != 'human':
            self.level.run()
            # self.run_matplotlib_gui()
            # self.run_dash_app()
        else:
            pygame.init()
            pygame.display.set_caption("Smart-Bomberman-Training")
            font = pygame.font.Font(pygame.font.get_default_font(), 18)
            time_remaining = 0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()

            enemies_alive = self.level.get_enemy_count()
            if self.level.player_hit_gateway:
                pygame.time.wait(1000)
                _endgame_screen(font, time_remaining, enemies_alive)
                pygame.display.update()
            if self.level.player_hit_enemy or \
                    self.level.player_hit_explosion:  # or time_remaining == 0:
                pygame.time.wait(1000)
                _endgame_screen(font, time_remaining, enemies_alive)
                pygame.display.update()
                # pygame.quit()
            timer_text = font.render(f'Time Remaining: {time_remaining}', True, _WHITE_FONT_TEXT)
            _SCREEN.fill((128, 128, 128))  # fill bg with grey color
            _SCREEN.blit(timer_text, (10, 10))
            self.level.run()
            # if self.policy_parameters is not None and not self.thread_start:
            #     # weights = [layer for layer in self.policy_parameters]
            #
            #     self.thread_start = True
            _CLOCK.tick(60)
            # self.run_matplotlib_gui()
            pygame.display.update()

    def update_policy_parameters(self, policy_parameters):
        """Store the updated the weights of the neural network."""
        # Update the policy parameters in the environment
        # You can store the parameters in an instance variable
        neural_net = []
        for values in policy_parameters:
            neurons = []
            if len(values.shape) == 2:
                for cells in values:
                    neurons.append(np.amax(cells))
                #         neurons = np.array(neurons)
                neural_net.append(np.array(neurons))
            else:
                neurons = values
                neural_net.append(neurons)
        # self.policy_parameters = [layer for layer in policy_parameters]
        self.policy_parameters = neural_net

    def run_dash_app(self):
        app = dash.Dash(__name__)
        app.layout = html.Div([
            html.H1("Neuron Weights Visualization"),
            dcc.Graph(
                id='neuron-weights',
            ),
            dcc.Graph(
                id='heatmap',
            ),
            dcc.Interval(
                id='interval-component',
                interval=800,  # in milliseconds
                n_intervals=0
            )
        ])

        @app.callback(Output('neuron-weights', 'figure'),
                      Output('heatmap', 'figure'),
                      Output('neuron-weights', 'responsive'),
                      Output('neuron-weights', 'config'),
                      Output('neuron-weights', 'style'),
                      Input('interval-component', 'n_intervals'))
        def update_neuron_weights(n_intervals):
            # Update the figure
            fig = self.visualize_neuron_weights(self.policy_parameters)
            fig2 = self.visualize_agent_space()
            return fig, fig2, True, {'displayModeBar': False}, {'width': '100%', 'height': '100vh'}
        # @app.callback(
        #     Output('heatmap', 'figure'),
        #     Output('heatmap', 'responsive'),
        #     Output('heatmap', 'config'),
        #     Output('heatmap', 'style'),
        #     Input('interval-component', 'n_intervals')
        # )
        # def update_heatmap(n_intervals):
        #     fig = self.visualize_agent_space()
        #     return fig, True, {'displayModeBar': False}, {'width': '100%', 'height': '100vh'}
        app.run_server(debug=False, use_reloader=False)


    def visualize_agent_space(self):
        encoded_state = []
        for row in self.map_data:
            encoded_state_loc = []
            for column in row:
                if column == "X":
                    encoded_state_loc.append(6)
                elif column == "B_1" or column == "B_2":
                    encoded_state_loc.append(2)
                elif column == "E":
                    encoded_state_loc.append(4)
                elif column == "W":
                    encoded_state_loc.append(1)
                elif column == "#":
                    encoded_state_loc.append(7)
                elif column == "P":
                    encoded_state_loc.append(-1)
                else:
                    encoded_state_loc.append(5)
            encoded_state.append(encoded_state_loc)

        # z = [[.1, .3, .5, .7, .9],
        #      [1, .8, .6, .4, .2],
        #      [.2, 0, .5, .7, .9],
        #      [.9, .8, .4, .2, 0],
        #      [.3, .4, .5, .7, 1]]

        fig = px.imshow(encoded_state, aspect="auto", color_continuous_scale="Viridis")
        return fig

    # Redundant Matplotlib attempt for Visualization
    # def run_matplotlib_gui(self):
    #     plt.ion()
    #
    #     # while True:
    #     #     with self.weights_lock:
    #     if self.policy_parameters is not None:
    #         latest_weights = self.policy_parameters.copy()
    #         fig, ax = plt.subplots()
    #         self.visualize_neuron_weights_2()

    # def run_matplotlib_gui(self):
    #     # fig, ax = plt.subplots(figsize=(10, 6))
    #     # anim = animation.FuncAnimation(fig, self.update_neuron_weights_lib, interval=100)  # Update every 100ms

    # def draw_nn_visual(self):
    #     """To draw the neural network visual."""
    #
    #     # plt.ion()
    #     # if self.policy_parameters:
    #     #     display.clear_output()
    #     #     display.display(plt.gcf())
    #     #     ax.axis('off')
    #     #     neural_net_data = get_restructured_neural_net(self.policy_parameters)
    #     #     neural_net_shape = [len(val) for val in neural_net_data]
    #     #     # draw_neural_net(ax, .1, .9, .1, .9, neural_net_shape, neural_net_data)
    #     #     test_data = []
    #     #     test_data.append(np.array([0, 0.4, 0.5, 0.7]))
    #     #     test_data.append(np.array([0, 0.4, 0.7]))
    #     #     test_data.append(np.array([0.8]))
    #     #     draw_neural_net(ax, .1, .9, .1, .9, [4, 3, 1], test_data)
    #     #     plt.show(block=False)

    def visualize_neuron_weights(self, weights):
        action_dict = {0: "Up", 1: "Down", 2: "left", 3: "right", 5: "bomb", 4: "wait"}
        if weights is None:
            layout = go.Layout(
                shapes=[],
                xaxis=dict(range=[0, 1], title='Layers'),
                yaxis=dict(range=[0, 1], title='Neurons')
            )
            return go.Figure(data=[], layout=layout)

        num_layers = len(weights)
        num_neurons = [w.shape[0] for w in weights]

        # Set up the positions and sizes of the rectangles
        x_start = 0
        y_start = 0
        width = 1.0 / (num_layers + 1)
        height_unit = 1.0 / max(num_neurons)
        layer_gap = width * 0.2

        shapes = []

        # Iterate over each layer
        for layer_idx, w in enumerate(weights):
            num_neuron = num_neurons[layer_idx]
            layer_weights = w.T  # Transpose the weights to get the neuron weights

            # Calculate the color based on the weights
            color = get_color(layer_idx)

            # Set up the rectangle properties for the layer
            x = x_start + layer_idx * width + layer_idx * layer_gap  # Add layer gap
            y = y_start + (max(num_neurons) - num_neuron) * height_unit / 2  # Align the layer in the middle
            shape = go.layout.Shape(
                type="rect",
                x0=x,
                y0=y,
                x1=x + width,
                y1=y + num_neuron * height_unit,
                fillcolor=color,
                line=dict(width=0)
            )
            shapes.append(shape)

            for neuron_idx in range(num_neuron):
                neuron_weights = layer_weights[neuron_idx]
                try:
                    color = get_color(neuron_weights[neuron_idx])
                except IndexError:
                    color = get_color(neuron_weights)
                if layer_idx == (len(weights) - 1):
                    color = get_color_action(self.recent_action)
                x = x_start + layer_idx * width + layer_idx * layer_gap  # Add layer gap
                y = y_start + (max(num_neurons) - num_neuron) * height_unit / 2 + neuron_idx * height_unit
                shape = go.layout.Shape(
                    type="rect",
                    x0=x,
                    y0=y,
                    x1=x + width,
                    y1=y + height_unit,
                    fillcolor=color,
                    line=dict(width=0)
                )
                shapes.append(shape)

        final_layer_idx = num_layers
        final_num_neurons = num_neurons[-1]
        final_x = x_start + final_layer_idx * width + final_layer_idx * layer_gap
        final_y = y_start + (max(num_neurons) - final_num_neurons) * height_unit / 2

        shapes.append(shape)
        text_color = get_color_action(self.recent_action)
        layout = go.Layout(
            shapes=shapes,
            xaxis=dict(range=[0, 1.3], showticklabels=False),
            yaxis=dict(range=[0, 1], title='Neurons', showticklabels=False),
            legend=dict(
                traceorder="normal",
                font=dict(family="sans-serif", size=12, color="black"),
                bgcolor="LightSteelBlue",
                bordercolor="Black",
                borderwidth=2
            ),
            annotations=[
                go.layout.Annotation(
                    x=final_x + width,  # Adjust the x-coordinate for the text
                    y=final_y + final_num_neurons * height_unit / 2,  # Align the text vertically with the last layer
                    text=action_dict[self.recent_action].capitalize(),
                    showarrow=False,
                    font=dict(size=25, color=text_color)
                )
            ]
        )
        fig = go.Figure(data=[], layout=layout)
        return fig


    # Variant of Visualizing neural network - Redundant or can be improved
    def visualize_neuron_weights_2(self):
        # weights: List of arrays containing the weights for each layer
        # display.clear_output(wait=True)
        # display.display(plt.gcf())
        # plt.clf()
        weights = self.policy_parameters
        num_layers = len(weights)

        fig, ax = plt.subplots(figsize=(10, 6))
        cmap = plt.cm.get_cmap('coolwarm')

        num_neurons = [w.shape[0] for w in weights]

        # Set up the positions and sizes of the rectangles
        x_start = 0
        y_start = 0
        width = 1.0 / (num_layers + 1)  # Add 1 to account for the output layer
        height_unit = 1.0 / max(num_neurons)

        # Iterate over each layer
        for layer_idx, w in enumerate(weights):
            num_neuron = num_neurons[layer_idx]
            layer_weights = w.T

            # Calculate the color based on the weights
            color = cmap(layer_weights.mean())

            # Set up the rectangle properties for the layer
            x = x_start + (layer_idx + 1) * width  # Add 1 to shift the output layer
            y = y_start + (max(num_neurons) - num_neuron) * height_unit / 2  # Align the layer in the middle
            rect = plt.Rectangle((x, y), width, num_neuron * height_unit, facecolor=color)

            ax.add_patch(rect)

            # Iterate over each neuron in the layer
            for neuron_idx in range(num_neuron):
                neuron_weights = layer_weights[neuron_idx]

                # Calculate the color based on the weights
                color = cmap(neuron_weights.mean())

                # Set up the rectangle properties for the neuron
                x = x_start + (layer_idx + 1) * width  # Add 1 to shift the output layer
                y = y_start + (max(num_neurons) - num_neuron) * height_unit / 2 + neuron_idx * height_unit
                rect = plt.Rectangle((x, y), width, height_unit, facecolor=color)

                # Add the rectangle to the plot
                ax.add_patch(rect)

        # Set the axis limits and labels
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel('Layers')
        ax.set_ylabel('Neurons')

        # Show the plot
        plt.pause(0.001)

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


def get_color(value):
    """Color for the corresponding neuron value."""
    if value == 0:
        return "yellow"
    elif 0 < value <= 0.05:
        return "green"
    elif 0.05 < value <= 0.1:
        return "red"
    elif 0.1 < value <= 0.15:
        return "blue"
    elif 0.15 < value <= 0.2:
        return "purple"
    elif 0.2 < value <= 0.25:
        return "orange"
    elif 0.25 < value <= 0.3:
        return "cyan"
    elif 0.3 < value <= 0.35:
        return "magenta"
    elif 0.35 < value <= 0.4:
        return "lime"
    elif 0.4 < value <= 0.45:
        return "pink"
    elif 0.45 < value <= 0.5:
        return "teal"
    elif 0.5 < value <= 0.55:
        return "olive"
    elif 0.55 < value <= 0.6:
        return "brown"
    elif 0.6 < value <= 0.65:
        return "navy"
    elif 0.65 < value <= 0.7:
        return "maroon"
    elif 0.7 < value <= 0.75:
        return "gold"
    elif 0.75 < value <= 0.8:
        return "indigo"
    elif 0.8 < value <= 0.85:
        return "silver"
    elif 0.85 < value <= 0.9:
        return "turquoise"
    elif 0.9 < value <= 0.95:
        return "coral"
    elif 0.95 < value <= 1:
        return "darkgreen"
    else:
        return "black"


def get_color_action(value):
    """Color for the corresponding action"""
    if value == 0:
        return "green"
    if value == 1:
        return "indigo"
    if value == 2:
        return "blue"
    if value == 3:
        return "olive"
    if value == 4:
        return "red"
    if value == 5:
        return "purple"