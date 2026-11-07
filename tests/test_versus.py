"""Rule tests for Battle mode (human vs Two-Fuse) and its training helpers."""

import numpy as np
import pytest

from game.ai.engine import BOMB, DOWN, LEFT, NOOP, RIGHT, UP, MapLayout, available_arenas, load_map
from game.ai.policies import HeuristicPolicy, RandomPolicy, camper, wanderer
from game.ai.versus_engine import VersusConfig, VersusEngine, mirror_spawn
from game.ai.versus_env import BASE_STATE_SIZE, VersusEnv, warm_start_policy
from game.ai.versus_train import SINGLE_PLAYER_MODEL, duel, elo_ratings

QUIET = {"enemy_move_every": 1000}  # enemies that never move, so tests stay deterministic


def make_layout(rows):
    """ASCII layout: # solid, b breakable, P first start, Q second start, E enemy."""
    height, width = len(rows), len(rows[0])
    solid = np.zeros((height, width), dtype=bool)
    hp = np.zeros((height, width), dtype=np.int8)
    starts, enemies = {}, []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            solid[r, c] = ch == "#"
            hp[r, c] = ch == "b"
            if ch in "PQ":
                starts[ch] = (r, c)
            elif ch == "E":
                enemies.append((r, c))
    return MapLayout("test", solid, hp, starts["P"], enemies, None, starts.get("Q"))


def engine_for(rows, **config):
    defaults = {"sudden_death_start": 10_000, **QUIET}
    return VersusEngine(make_layout(rows), VersusConfig(**{**defaults, **config}), rng=np.random.default_rng(0))


def test_arenas_load_with_both_starts():
    assert "arena_1" in available_arenas()
    layout = load_map("arena_1")
    assert layout.rival is not None and layout.rival != layout.player


@pytest.mark.parametrize("name", ["map_1", "map_2", "map_3"])
def test_mirror_spawn_is_a_free_cell(name):
    layout = load_map(name)
    cell = mirror_spawn(layout)
    assert not layout.solid[cell] and layout.wall_hp[cell] == 0 and cell != layout.player


def test_swap_exchanges_starting_corners():
    layout = make_layout(["#####", "#P Q#", "#####"])
    assert VersusEngine(layout, swap=True).players[0].cell == layout.rival


def test_fighters_do_not_block_each_other():
    engine = engine_for(["#####", "#P Q#", "#####"])
    engine.step_versus([RIGHT, LEFT])
    assert engine.players[0].cell == engine.players[1].cell == (1, 2)


def test_bomb_limit_is_per_player():
    engine = engine_for(["#######", "#P   Q#", "#######"])
    events = engine.step_versus([BOMB, BOMB])
    assert events.players[0].bomb_placed and events.players[1].bomb_placed
    assert {bomb.owner for bomb in engine.bombs} == {0, 1}
    engine.step_versus([RIGHT, LEFT])
    assert engine.step_versus([BOMB, NOOP]).players[0].invalid_action


def test_kill_is_credited_to_the_bomber():
    engine = engine_for(["########", "#   PQ #", "########"], bomb_fuse=3)
    engine.step_versus([BOMB, NOOP])
    engine.step_versus([LEFT, NOOP])
    events = engine.step_versus([LEFT, NOOP])  # 0 is two tiles away when it blows, 1 stayed next to it
    assert events.done and events.winner == 0
    assert events.players[1].killed_by == "opponent_bomb" and events.players[0].killed_opponent


def test_own_bomb_kill_is_suicide():
    engine = engine_for(["#######", "#P   Q#", "#######"], bomb_fuse=2)
    engine.step_versus([BOMB, NOOP])
    events = engine.step_versus([NOOP, NOOP])
    assert events.winner == 1 and events.players[0].killed_by == "own_bomb"
    assert not events.players[1].killed_opponent


def test_dying_on_the_same_step_is_a_draw():
    engine = engine_for(["#######", "#P Q  #", "#######"], bomb_fuse=2)
    engine.step_versus([RIGHT, NOOP])  # 0 at (1, 2), next to 1 at (1, 3)
    engine.step_versus([BOMB, NOOP])
    events = engine.step_versus([NOOP, NOOP])
    assert events.done and events.draw and events.winner is None


def test_enemies_are_hazards_for_both():
    engine = engine_for(["######", "#PE Q#", "######"])
    events = engine.step_versus([RIGHT, NOOP])
    assert events.winner == 1 and events.players[0].killed_by == "enemy"


def test_sudden_death_closes_from_the_border_and_ends_every_match():
    engine = engine_for(["#######", "#P    #", "#  #  #", "#    Q#", "#######"], sudden_death_start=3)
    first = engine.closing_order[0]
    assert first == (1, 1)  # the spiral starts at the top-left of the outermost open ring
    engine.players[0].cell = (2, 2)  # out of the way of the first cells
    for _ in range(3):
        engine.step_versus([NOOP, NOOP])
    assert engine.solid[first]
    while not engine.finished:
        engine.step_versus([NOOP, NOOP])
    assert engine.steps < engine.config.max_steps
    assert "crushed" in {fighter.killed_by for fighter in engine.players}


def test_sudden_death_squeezes_both_corners_alike():
    engine = VersusEngine(load_map("arena_1"))
    height, width = engine.shape
    order = engine.closing_order
    for first, second in zip(order[0:40:2], order[1:40:2], strict=True):
        assert second == (height - 1 - first[0], width - 1 - first[1])


def test_closing_cells_count_as_danger():
    engine = engine_for(["#######", "#P    #", "#    Q#", "#######"], sudden_death_start=4, sudden_death_warning=6)
    danger = engine.danger_map()
    assert danger[engine.closing_order[0]] > 0
    assert np.isinf(engine.escape_distances()[engine.closing_order[0]]) or engine.escape_distances()[(1, 1)] > 0


def test_env_observation_and_episode_stats():
    env = VersusEnv("arena_1", opponent="random")
    obs, _ = env.reset(seed=0)
    assert env.observation_space.contains(obs)
    done, info = False, {}
    while not done:
        obs, _, terminated, truncated, info = env.step(env.action_space.sample())
        done = terminated or truncated
    stats = info["episode_stats"]
    assert stats["won"] + stats["lost"] + stats["draw"] == 1


def test_warm_start_reproduces_the_single_player_policy():
    from stable_baselines3 import PPO

    env = VersusEnv("arena_1", opponent="random")
    model = PPO("MultiInputPolicy", env, policy_kwargs={"net_arch": [256, 256]}, device="cpu")
    warm_start_policy(str(SINGLE_PLAYER_MODEL), model)
    old = PPO.load(str(SINGLE_PLAYER_MODEL), device="cpu")
    rng = np.random.default_rng(0)
    old_obs = {k: rng.random((1, *space.shape), dtype=np.float32) for k, space in old.observation_space.items()}
    new_obs = {k: rng.random((1, *space.shape), dtype=np.float32) for k, space in env.observation_space.items()}
    new_obs["local"][:, :7] = old_obs["local"]
    new_obs["state"][:, :BASE_STATE_SIZE] = old_obs["state"]
    old_probs = old.policy.get_distribution(old.policy.obs_to_tensor(old_obs)[0]).distribution.probs
    new_probs = model.policy.get_distribution(model.policy.obs_to_tensor(new_obs)[0]).distribution.probs
    assert np.allclose(old_probs.detach().numpy(), new_probs.detach().numpy(), atol=1e-5)


@pytest.mark.parametrize("bot", [camper, wanderer])
def test_passive_bots_never_attack(bot):
    policy = bot(seed=0)
    engine = VersusEngine(load_map("arena_1"), rng=np.random.default_rng(0))
    while not engine.finished:
        action = policy.act(engine, 1)
        assert action != BOMB
        engine.step_versus([NOOP, action])


def test_heuristic_bot_beats_random():
    record = duel(HeuristicPolicy(seed=0), RandomPolicy(seed=0), "arena_1,map_2", games=6)
    assert record["win_rate"] >= 5 / 6


def test_elo_ranks_the_stronger_player_higher():
    ratings = elo_ratings(["strong", "weak", "middle"], {(0, 1): (9.0, 10), (0, 2): (7.0, 10), (2, 1): (7.0, 10)})
    assert ratings["strong"] > ratings["middle"] > ratings["weak"]


def test_unknown_difficulty_is_rejected():
    from game.ai.versus_game import two_fuse

    with pytest.raises(ValueError):
        two_fuse("legendary")


def test_up_and_down_are_the_engine_moves():
    engine = engine_for(["#####", "#P  #", "#  Q#", "#####"])
    engine.step_versus([DOWN, UP])
    assert engine.players[0].cell == (2, 1) and engine.players[1].cell == (1, 3)
