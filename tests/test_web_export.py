"""The Python half of the web port: the shared generator and the exported files."""

import json

import numpy as np

from game.ai.engine import load_map
from game.ai.web_export import WEB_MAPS, SeedRng, export_maps, match_setup, new_match


def test_seed_rng_is_reproducible_and_streams_differ():
    a, b, other = SeedRng(7, 1), SeedRng(7, 1), SeedRng(7, 2)
    first = [a.next_u32() for _ in range(5)]
    assert first == [b.next_u32() for _ in range(5)]
    assert first != [other.next_u32() for _ in range(5)]
    assert all(0 <= x < 2**32 for x in first)


def test_seed_rng_draws_cover_their_range():
    rng = SeedRng(3)
    draws = [rng.integers(4) for _ in range(2000)]
    assert set(draws) == {0, 1, 2, 3}
    assert sorted(rng.permutation(5)) == [0, 1, 2, 3, 4]
    assert 0.45 < np.mean([rng.random() for _ in range(4000)]) < 0.55


def test_match_setup_uses_every_map_and_both_corners():
    setups = [match_setup(seed) for seed in range(300)]
    assert {name for name, _ in setups} == set(WEB_MAPS)
    assert {swap for _, swap in setups} == {True, False}


def test_new_match_is_deterministic():
    one, two = new_match(11), new_match(11)
    for _ in range(50):
        one.step_versus([0, 0])
        two.step_versus([0, 0])
    assert one.render_text() == two.render_text()


def test_exported_maps_round_trip(tmp_path):
    maps = json.loads(export_maps(tmp_path).read_text())
    for name in WEB_MAPS:
        layout = load_map(name)
        rows = maps[name]
        assert len(rows) == layout.shape[0] and {len(row) for row in rows} == {layout.shape[1]}
        assert rows[layout.player[0]][layout.player[1]] == "P"
        assert sum(row.count("E") for row in rows) == len(layout.enemies)
