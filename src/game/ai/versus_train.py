"""Train Two-Fuse by league self-play, run duels, and rank agents by Elo."""

from __future__ import annotations

import itertools
import json
import os
import shutil
import time
from collections import Counter, deque
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np
from gymnasium import spaces

from .engine import load_map
from .policies import ModelPolicy, OpponentSampler, Policy, make_policy
from .train import RUNS_DIR, MapSpec, _parse_maps
from .versus_engine import VersusConfig, VersusEngine
from .versus_env import STATE_SIZE, VersusEnv, warm_start_policy

CHAMPION = Path(__file__).resolve().parents[3] / "models" / "two_fuse.zip"
SINGLE_PLAYER_MODEL = CHAMPION.with_name("ppo_map1_map2.zip")
DEFAULT_MAPS = "arena_1,map_2,map_3"


# --------------------------------------------------------------------- duels
def play_match(
    a: Policy, b: Policy, layout_name: str, seed: int, swap: bool, config: VersusConfig | None = None
) -> dict[str, Any]:
    """One match, ``a`` as player 0 and ``b`` as player 1."""
    engine = VersusEngine(load_map(layout_name), config, rng=np.random.default_rng(seed), swap=swap)
    while not engine.finished:
        engine.step_versus([a.act(engine, 0), b.act(engine, 1)])
    return {
        "winner": engine.winner,
        "steps": engine.steps,
        "map": layout_name,
        "killed_by": [fighter.killed_by for fighter in engine.players],
    }


def duel(a: Policy, b: Policy, maps: MapSpec = DEFAULT_MAPS, games: int = 40, seed: int = 0) -> dict[str, Any]:
    """Head-to-head record of ``a`` against ``b``, alternating maps and starting corners."""
    names = _parse_maps(maps)
    wins, losses, draws, steps = 0, 0, 0, []
    deaths: Counter[str] = Counter()
    for game in range(games):
        result = play_match(a, b, names[game % len(names)], seed + game, swap=bool(game // len(names) % 2))
        wins += result["winner"] == 0
        losses += result["winner"] == 1
        draws += result["winner"] is None
        steps.append(result["steps"])
        if result["killed_by"][0]:
            deaths[result["killed_by"][0]] += 1
    return {
        "a": a.name,
        "b": b.name,
        "games": games,
        "win_rate": wins / games,
        "loss_rate": losses / games,
        "draw_rate": draws / games,
        "mean_steps": float(np.mean(steps)),
        "a_deaths_by": dict(deaths),
    }


def elo_ratings(names: Sequence[str], scores: dict[tuple[int, int], tuple[float, int]]) -> dict[str, float]:
    """Fit Elo ratings (a Bradley-Terry model) to pairwise results.

    ``scores[(i, j)] = (points of i, games)`` with a win worth 1 and a draw 0.5.
    Ratings are centred on 1000.
    """
    ratings = np.zeros(len(names))
    for _ in range(2000):
        grad = np.zeros_like(ratings)
        for (i, j), (points, games) in scores.items():
            expected = games / (1 + 10 ** ((ratings[j] - ratings[i]) / 400))
            grad[i] += points - expected
            grad[j] -= points - expected
        ratings += 4.0 * grad / max(1, *(games for _, games in scores.values()))
        ratings -= ratings.mean()
    return {name: round(float(r) + 1000, 1) for name, r in zip(names, ratings, strict=True)}


def tournament(players: Sequence[Policy], maps: MapSpec = DEFAULT_MAPS, games: int = 12, seed: int = 0) -> list[dict]:
    """Round robin between ``players``; returns them ranked by Elo."""
    scores: dict[tuple[int, int], tuple[float, int]] = {}
    for i, j in itertools.combinations(range(len(players)), 2):
        record = duel(players[i], players[j], maps, games, seed)
        points = games * (record["win_rate"] + 0.5 * record["draw_rate"])
        scores[(i, j)] = (points, games)
        print(f"  {players[i].name:>24} vs {players[j].name:<24} {record['win_rate']:.0%} won", flush=True)
    ratings = elo_ratings([p.name for p in players], scores)
    return sorted(
        ({"name": name, "elo": elo} for name, elo in ratings.items()), key=lambda row: row["elo"], reverse=True
    )


# ------------------------------------------------------------------ training
def _env_factory(maps: list[str], league_dir: Path, seed: int, rank: int, config: VersusConfig) -> Callable:
    def _init():
        import torch
        from stable_baselines3.common.monitor import Monitor

        torch.set_num_threads(1)
        env = VersusEnv(maps=maps, opponent=OpponentSampler(league_dir), engine_config=config)
        env.reset(seed=seed + rank)
        return Monitor(env)

    return _init


def train_versus(
    maps: MapSpec = DEFAULT_MAPS,
    timesteps: int = 3_000_000,
    n_envs: int = 8,
    seed: int = 0,
    run_name: str | None = None,
    init_from: str | None = str(SINGLE_PLAYER_MODEL),
    snapshot_every: int = 100_000,
    eval_every: int = 100_000,
    eval_games: int = 30,
    learning_rate: float = 2e-4,
    ent_coef: float = 0.01,
    n_steps: int = 256,
    sudden_death_start: int = 150,
    tournament_size: int = 8,
    tournament_games: int = 12,
    verbose: int = 0,
) -> Path:
    """Train Two-Fuse with league self-play and crown the Elo champion.

    ``init_from`` is a single-player model to warm-start from (its weights are
    transplanted), a Battle-mode model to continue training, or empty for a
    fresh start. The run directory gets ``league/`` (snapshots), ``final.zip``,
    ``two_fuse.zip`` (the tournament winner) and ``metrics.json``.
    """
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv

    torch.set_num_threads(1)
    map_names = _parse_maps(maps)
    run_name = run_name or f"versus_s{seed}_{time.strftime('%Y%m%d-%H%M%S')}"
    run_dir = RUNS_DIR / run_name
    league_dir = run_dir / "league"
    league_dir.mkdir(parents=True, exist_ok=True)
    config = VersusConfig(sudden_death_start=sudden_death_start)
    settings = {k: v for k, v in locals().items() if isinstance(v, (int, float, str)) and k != "run_name"}

    vec_env = SubprocVecEnv(
        [_env_factory(map_names, league_dir, seed * 1000, i, config) for i in range(n_envs)], start_method="spawn"
    )
    continuing = bool(init_from) and _is_versus_model(str(init_from))
    if continuing and init_from:
        model = PPO.load(init_from, env=vec_env, device="cpu", learning_rate=learning_rate, ent_coef=ent_coef)
    else:
        model = PPO(
            "MultiInputPolicy",
            vec_env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            batch_size=512,
            n_epochs=4,
            gamma=0.99,
            gae_lambda=0.95,
            ent_coef=ent_coef,
            policy_kwargs={"net_arch": [256, 256]},
            seed=seed,
            device="cpu",
            verbose=verbose,
            tensorboard_log=str(run_dir / "tb"),
        )
        if init_from:
            warm_start_policy(str(init_from), model)

    def snapshot(steps: int) -> None:
        tmp = league_dir / "tmp_snapshot.zip"  # write then rename, so workers never load a half-written file
        model.save(tmp)
        os.replace(tmp, league_dir / f"snap_{steps:09d}.zip")

    snapshot(0)
    history: list[dict[str, Any]] = []
    heuristic = make_policy("heuristic", seed=123)

    class Progress(BaseCallback):
        """Save league snapshots and report progress against the scripted bot."""

        def __init__(self):
            super().__init__()
            self.recent: deque = deque(maxlen=300)
            self.next_snapshot = snapshot_every
            self.next_eval = eval_every
            self.start = time.time()

        def _on_step(self) -> bool:
            for info in self.locals["infos"]:
                if "episode_stats" in info:
                    self.recent.append(info["episode_stats"])
            if self.num_timesteps >= self.next_snapshot:
                self.next_snapshot += snapshot_every
                snapshot(self.num_timesteps)
            if self.num_timesteps >= self.next_eval:
                self.next_eval += eval_every
                self._evaluate()
            return True

        def _evaluate(self) -> None:
            me = ModelPolicy(self.model, deterministic=True, name="current")
            record = duel(me, heuristic, map_names, eval_games, seed=50_000)
            league = [s for s in self.recent if s["opponent"].startswith("snap_")]
            row = {
                "timesteps": self.num_timesteps,
                "minutes": round((time.time() - self.start) / 60, 2),
                "train_win_rate": _rate(self.recent, "won"),
                "league_win_rate": _rate(league, "won"),
                "vs_heuristic": record["win_rate"],
                "vs_heuristic_draws": record["draw_rate"],
                "deaths_by": record["a_deaths_by"],
            }
            history.append(row)
            self.logger.record("eval/vs_heuristic", record["win_rate"])
            print(
                f"[{run_name}] {row['timesteps']:>9} steps  vs heuristic {row['vs_heuristic']:.0%} "
                f"(draws {row['vs_heuristic_draws']:.0%})  train win {row['train_win_rate']:.0%}  "
                f"vs league {row['league_win_rate']:.0%}  deaths {row['deaths_by']}  ({row['minutes']} min)",
                flush=True,
            )

    model.learn(total_timesteps=timesteps, callback=Progress(), progress_bar=False)
    model.save(run_dir / "final.zip")
    snapshot(model.num_timesteps)
    vec_env.close()

    print("tournament:", flush=True)
    snaps = sorted(league_dir.glob("snap_*.zip"))[-tournament_size:]
    players: list[Policy] = [ModelPolicy(path) for path in snaps]
    players += [make_policy("heuristic", seed=7), make_policy("random", seed=7)]
    ranking = tournament(players, map_names, tournament_games)
    best = next(row["name"] for row in ranking if row["name"].startswith("snap_"))
    shutil.copy(league_dir / f"{best}.zip", run_dir / "two_fuse.zip")
    for row in ranking:
        print(f"  {row['elo']:>7}  {row['name']}{'  <- champion' if row['name'] == best else ''}")
    metrics = {"config": settings, "history": history, "ranking": ranking, "champion": best}
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return run_dir


def _rate(stats: Sequence[dict[str, Any]], key: str) -> float:
    return round(sum(s[key] for s in stats) / len(stats), 3) if stats else 0.0


def _is_versus_model(path: str) -> bool:
    from stable_baselines3 import PPO

    space = cast(spaces.Dict, PPO.load(path, device="cpu").observation_space)
    return space["state"].shape == (STATE_SIZE,)
