"""Rule tests for the headless engine and the Gymnasium environment."""
import numpy as np
import pytest

from game.ai.engine import BOMB, DOWN, LEFT, NOOP, RIGHT, UP, Engine, EngineConfig, MapLayout, available_maps
from game.ai.env import BombermanEnv


def make_layout(rows, name="test"):
    """Build a layout from ASCII: # solid, b breakable, P player, E enemy, D door."""
    height, width = len(rows), len(rows[0])
    solid = np.zeros((height, width), dtype=bool)
    hp = np.zeros((height, width), dtype=np.int8)
    player, enemies, door = None, [], None
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            solid[r, c] = ch == "#"
            hp[r, c] = ch == "b"
            if ch == "P":
                player = (r, c)
            elif ch == "E":
                enemies.append((r, c))
            elif ch == "D":
                door = (r, c)
    return MapLayout(name, solid, hp, player, enemies, door or (0, 0))  # default: unreachable


def run(engine, actions):
    events = None
    for action in actions:
        events = engine.step(action)
    return events


def test_all_shipped_maps_load():
    for name in available_maps():
        env = BombermanEnv(name)
        obs, _ = env.reset(seed=0)
        assert env.observation_space.contains(obs)


def test_player_blocked_by_walls_and_bombs():
    engine = Engine(make_layout(["#####", "#P b#", "#####"]))
    assert engine.step(UP).invalid_action
    engine.step(RIGHT)
    assert engine.step(RIGHT).invalid_action  # breakable wall
    engine.step(BOMB)
    engine.step(LEFT)
    assert engine.step(RIGHT).invalid_action  # own bomb


def test_bomb_destroys_wall_and_kills_player_standing_in_blast():
    config = EngineConfig(bomb_fuse=3)
    engine = Engine(make_layout(["######", "#Pb  #", "######"]), config)
    run(engine, [BOMB, NOOP])
    events = engine.step(NOOP)
    assert events.walls_destroyed == 1 and events.player_died and events.killed_by == "bomb"


def test_blast_range_is_one_tile():
    config = EngineConfig(bomb_fuse=4)
    engine = Engine(make_layout(["#####", "#P  #", "## ##", "#####"]), config)
    run(engine, [RIGHT, BOMB, DOWN, NOOP, NOOP])  # hiding right below the bomb is still within range 1
    assert not engine.alive
    engine = Engine(make_layout(["######", "#P   #", "#### #", "######"]), config)
    run(engine, [BOMB, RIGHT, RIGHT, NOOP])  # two tiles away is outside range 1
    assert engine.alive


def test_chain_reaction_detonates_neighbouring_bomb():
    config = EngineConfig(bomb_fuse=5, bomb_limit=2)
    engine = Engine(make_layout(["#######", "#P    #", "#######"]), config)
    run(engine, [BOMB, RIGHT, BOMB, RIGHT, RIGHT])  # second bomb would go off one step later
    assert len(engine.bombs) == 0


def test_door_only_counts_after_all_enemies_dead():
    engine = Engine(make_layout(["#####", "#PD #", "#  E#", "#####"]), EngineConfig(enemy_move_every=1000))
    assert not engine.step(RIGHT).reached_door
    engine.enemies[0].alive = False
    engine.step(LEFT)
    assert engine.step(RIGHT).reached_door


def test_enemy_contact_kills_player():
    engine = Engine(make_layout(["#####", "#PE #", "#####"]), EngineConfig(enemy_move_every=1000))
    events = engine.step(RIGHT)
    assert events.player_died and events.killed_by == "enemy"


def test_enemy_killed_by_bomb_gives_reward():
    config = EngineConfig(bomb_fuse=2, enemy_move_every=1000)
    layout = make_layout(["#######", "#   E #", "#P#####", "#######"])
    engine = Engine(layout, config)
    engine.player = (1, 3)
    run(engine, [BOMB])
    engine.player = (2, 1)  # teleport out of the blast to isolate the enemy kill
    events = engine.step(NOOP)
    assert events.enemies_killed == 1 and engine.door_open


@pytest.mark.parametrize("name", available_maps())
def test_distance_map_reaches_door(name):
    env = BombermanEnv(name)
    env.reset(seed=0)
    dist = env.engine.distance_map([env.engine.door])
    assert np.isfinite(dist[env.engine.player])
