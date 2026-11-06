"""Train and evaluate PPO agents on the headless Bomberman environment."""
from __future__ import annotations

import json
import time
from collections import Counter, deque
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from .env import BombermanEnv

RUNS_DIR = Path(__file__).resolve().parents[3] / "runs"
MapSpec = str | Sequence[str]


def _parse_maps(maps: MapSpec) -> list[str]:
    if isinstance(maps, str):
        return [name.strip() for name in maps.split(",") if name.strip()]
    return list(maps)


def _env_factory(maps: list[str], seed: int, rank: int) -> Callable[[], BombermanEnv]:
    def _init() -> BombermanEnv:
        from stable_baselines3.common.monitor import Monitor

        env = BombermanEnv(maps=maps)
        env.reset(seed=seed + rank)
        return Monitor(env)  # type: ignore[return-value]
    return _init


def evaluate(model: Any, maps: MapSpec, episodes: int = 100, deterministic: bool = False,
             seed: int = 10_000) -> dict[str, Any]:
    """Run a policy (a PPO model, or ``"random"``) and summarise the outcomes."""
    map_names = _parse_maps(maps)
    env = BombermanEnv(maps=map_names)
    if isinstance(model, (str, Path)) and str(model) != "random":
        from stable_baselines3 import PPO
        model = PPO.load(str(model), device="cpu")
    results: list[dict[str, Any]] = []
    for episode in range(episodes):
        obs, _ = env.reset(seed=seed + episode, options={"map_index": episode % len(map_names)})
        done, total = False, 0.0
        while not done:
            if model == "random":
                action = env.action_space.sample()
            else:
                action, _ = model.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(action)
            total += reward
            done = terminated or truncated
        results.append({**info["episode_stats"], "return": total})
    return summarise(results)


def summarise(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-episode stats, overall and per map."""
    def agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rows)
        return {
            "episodes": n,
            "win_rate": sum(r["won"] for r in rows) / n,
            "death_rate": sum(r["died"] for r in rows) / n,
            "timeout_rate": sum(not r["won"] and not r["died"] for r in rows) / n,
            "kills_per_ep": float(np.mean([r["kills"] for r in rows])),
            "walls_per_ep": float(np.mean([r["walls"] for r in rows])),
            "mean_steps": float(np.mean([r["steps"] for r in rows])),
            "mean_return": float(np.mean([r["return"] for r in rows])),
            "deaths_by": dict(Counter(r["killed_by"] for r in rows if r["died"])),
        }
    summary = agg(results)
    maps = sorted({r["map"] for r in results})
    if len(maps) > 1:
        summary["per_map"] = {m: agg([r for r in results if r["map"] == m]) for m in maps}
    return summary


def train(maps: MapSpec = "map_2", timesteps: int = 300_000, n_envs: int = 8, seed: int = 0,
          run_name: str | None = None, eval_every: int = 25_000, eval_episodes: int = 30,
          learning_rate: float = 3e-4, ent_coef: float = 0.01, n_steps: int = 256,
          init_from: str | None = None, verbose: int = 0) -> Path:
    """Train PPO and save ``final.zip``, ``best.zip`` (by eval win rate) and metrics.

    Returns the run directory.
    """
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv

    torch.set_num_threads(1)
    map_names = _parse_maps(maps)
    run_name = run_name or f"ppo_{'+'.join(map_names)}_s{seed}_{time.strftime('%Y%m%d-%H%M%S')}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {k: v for k, v in locals().items()
              if k in ("timesteps", "n_envs", "seed", "eval_every", "eval_episodes",
                       "learning_rate", "ent_coef", "n_steps", "init_from")}
    config["maps"] = map_names

    vec_env = SubprocVecEnv([_env_factory(map_names, seed * 1000, i) for i in range(n_envs)],
                            start_method="spawn")
    if init_from:
        model = PPO.load(init_from, env=vec_env, device="cpu", seed=seed,
                         learning_rate=learning_rate, ent_coef=ent_coef)
    else:
        model = PPO("MultiInputPolicy", vec_env, learning_rate=learning_rate, n_steps=n_steps,
                    batch_size=512, n_epochs=4, gamma=0.99, gae_lambda=0.95, ent_coef=ent_coef,
                    policy_kwargs={"net_arch": [256, 256]}, seed=seed, device="cpu",
                    verbose=verbose, tensorboard_log=str(run_dir / "tb"))

    history: list[dict[str, Any]] = []
    best = {"win_rate": -1.0}

    class Progress(BaseCallback):
        """Track training-episode outcomes and run periodic evaluations."""

        def __init__(self):
            super().__init__()
            self.recent: deque = deque(maxlen=200)
            self.next_eval = eval_every
            self.start = time.time()

        def _on_step(self) -> bool:
            for info in self.locals["infos"]:
                if "episode_stats" in info:
                    self.recent.append(info["episode_stats"])
            if self.num_timesteps >= self.next_eval:
                self.next_eval += eval_every
                self._evaluate()
            return True

        def _evaluate(self) -> None:
            result = evaluate(self.model, map_names, episodes=eval_episodes, seed=50_000)
            train_win = (sum(s["won"] for s in self.recent) / len(self.recent)) if self.recent else 0.0
            row = {"timesteps": self.num_timesteps, "minutes": round((time.time() - self.start) / 60, 2),
                   "train_win_rate": round(train_win, 3),
                   **{k: result[k] for k in ("win_rate", "death_rate", "timeout_rate",
                                             "kills_per_ep", "walls_per_ep", "mean_return")}}
            history.append(row)
            self.logger.record("eval/win_rate", result["win_rate"])
            self.logger.record("eval/death_rate", result["death_rate"])
            print(f"[{run_name}] {row['timesteps']:>8} steps  eval win {row['win_rate']:.0%}  "
                  f"died {row['death_rate']:.0%}  kills {row['kills_per_ep']:.2f}  "
                  f"walls {row['walls_per_ep']:.1f}  return {row['mean_return']:.2f}  "
                  f"({row['minutes']} min)", flush=True)
            if result["win_rate"] >= best["win_rate"]:
                best.update(result)
                self.model.save(run_dir / "best.zip")

    model.learn(total_timesteps=timesteps, callback=Progress(), progress_bar=False)
    model.save(run_dir / "final.zip")
    vec_env.close()
    (run_dir / "metrics.json").write_text(json.dumps({"config": config, "history": history}, indent=2))
    return run_dir


def watch(model: str = "random", maps: MapSpec = "map_2", episodes: int = 3,
          deterministic: bool = False, fps: int = 8, save_frames: str | None = None) -> None:
    """Play episodes in a pygame window, or save PNG frames with ``save_frames``."""
    map_names = _parse_maps(maps)
    env = BombermanEnv(maps=map_names, render_mode="rgb_array" if save_frames else "human")
    env.metadata = {**env.metadata, "render_fps": fps}
    policy: Any = model
    if model != "random":
        from stable_baselines3 import PPO
        policy = PPO.load(model, device="cpu")
    out = Path(save_frames) if save_frames else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    try:
        for episode in range(episodes):
            obs, _ = env.reset(seed=episode, options={"map_index": episode % len(map_names)})
            done, frame = False, 0
            while not done:
                if out:
                    _save_png(env.render(), out / f"ep{episode}_{frame:04d}.png")
                action = env.action_space.sample() if policy == "random" else \
                    policy.predict(obs, deterministic=deterministic)[0]
                obs, _, terminated, truncated, info = env.step(action)
                done, frame = terminated or truncated, frame + 1
            if out:
                _save_png(env.render(), out / f"ep{episode}_{frame:04d}.png")
            print(f"episode {episode}: {info['episode_stats']}")
    except KeyboardInterrupt:
        pass
    finally:
        env.close()


def _save_png(rgb: np.ndarray, path: Path) -> None:
    import pygame
    pygame.image.save(pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2))), str(path))
