"""Tests for the automatic Wang tile picker"""
from pathlib import Path

import pytest

from pytiled_parser import parse_tileset
from pytiled_parser.common_types import Color
from pytiled_parser.wang_set import WangColor, WangSet, WangTile
from pytiled_parser.wang_tile_picker import (
    DuplicateTileIdError,
    InvalidWangColorError,
    InvalidWangIdError,
    UnsupportedWangTypeError,
    WangPickerError,
    WangTileConstraints,
    WangTileTransform,
    find_wang_tile,
    find_wang_tile_candidates,
    transform_wang_id,
)

TEST_DATA = Path(__file__).parent / "test_data"
TERRAIN_TILESET = TEST_DATA / "tilesets" / "terrain" / "tileset.json"

# A fully asymmetric Wang ID: all 8 rotations/flips of it are distinct.
ASYMMETRIC_WANG_ID = [1, 1, 2, 1, 3, 1, 4, 2]

ALL_TRANSFORMS = [
    WangTileTransform(rotation=rotation, flip_horizontal=flip)
    for flip in (False, True)
    for rotation in (0, 90, 180, 270)
]


def make_wang_set(wang_tiles, wang_type="mixed", color_count=4):
    colors = [
        WangColor(
            color=Color(255, 255, 255, 255),
            name=f"color {index}",
            probability=1.0,
            tile=-1,
        )
        for index in range(color_count)
    ]
    return WangSet(
        name="test set",
        tile=-1,
        wang_type=wang_type,
        wang_colors=colors,
        wang_tiles={wang_tile.tile_id: wang_tile for wang_tile in wang_tiles},
    )


@pytest.fixture(scope="module")
def terrain_wang_set():
    return parse_tileset(TERRAIN_TILESET).wang_sets[0]


def test_transform_rotation():
    wang_id = [1, 1, 0, 2, 0, 1, 1, 1]
    # 90 degrees clockwise moves the left edge to the top.
    assert transform_wang_id(wang_id, WangTileTransform(rotation=90)) == [
        1, 1, 1, 1, 0, 2, 0, 1,
    ]
    assert transform_wang_id(wang_id, WangTileTransform(rotation=180)) == [
        0, 1, 1, 1, 1, 1, 0, 2,
    ]
    assert transform_wang_id(wang_id, WangTileTransform(rotation=270)) == [
        0, 2, 0, 1, 1, 1, 1, 1,
    ]
    # Four quarter turns are the identity.
    assert transform_wang_id(wang_id, WangTileTransform(rotation=360)) == wang_id


def test_transform_flip():
    wang_id = [1, 1, 0, 2, 0, 1, 1, 1]
    flipped = transform_wang_id(wang_id, WangTileTransform(flip_horizontal=True))
    assert flipped == [1, 1, 1, 1, 0, 2, 0, 1]
    # Flipping twice is the identity.
    assert (
        transform_wang_id(flipped, WangTileTransform(flip_horizontal=True)) == wang_id
    )


def test_transform_asymmetric_wang_id_has_eight_distinct_variants():
    variants = {
        tuple(transform_wang_id(ASYMMETRIC_WANG_ID, transform))
        for transform in ALL_TRANSFORMS
    }
    assert len(variants) == 8


def test_transform_invalid_rotation():
    with pytest.raises(ValueError):
        transform_wang_id(ASYMMETRIC_WANG_ID, WangTileTransform(rotation=45))


def test_transform_invalid_wang_id_length():
    with pytest.raises(InvalidWangIdError):
        transform_wang_id([1, 2, 3, 4], WangTileTransform())


def test_exact_match(terrain_wang_set):
    constraints = [1, 1, 0, 2, 0, 1, 1, 1]  # Wang ID of tile 0, as stored.
    candidates = find_wang_tile_candidates(terrain_wang_set, constraints)
    assert candidates
    for candidate in candidates:
        assert candidate.wang_id == constraints
    identity_matches = [
        candidate
        for candidate in candidates
        if candidate.tile_id == 0 and candidate.transform == WangTileTransform()
    ]
    assert len(identity_matches) == 1


def test_rotation_match(terrain_wang_set):
    # This is the Wang ID of tile 2, and also tile 0 rotated 90 degrees clockwise.
    constraints = [1, 1, 1, 1, 0, 2, 0, 1]
    candidates = find_wang_tile_candidates(terrain_wang_set, constraints)
    assert candidates
    for candidate in candidates:
        assert candidate.wang_id == constraints
    by_transform = {(c.tile_id, c.transform.rotation, c.transform.flip_horizontal) for c in candidates}
    assert (2, 0, False) in by_transform
    assert (0, 90, False) in by_transform


def test_flip_match():
    wang_set = make_wang_set([WangTile(tile_id=7, wang_id=ASYMMETRIC_WANG_ID)])
    transform = WangTileTransform(rotation=270, flip_horizontal=True)
    constraints = transform_wang_id(ASYMMETRIC_WANG_ID, transform)
    candidates = find_wang_tile_candidates(wang_set, constraints)
    assert len(candidates) == 1
    assert candidates[0].tile_id == 7
    assert candidates[0].transform == transform
    assert candidates[0].wang_id == constraints


def test_every_transform_is_findable():
    wang_set = make_wang_set([WangTile(tile_id=7, wang_id=ASYMMETRIC_WANG_ID)])
    for transform in ALL_TRANSFORMS:
        constraints = transform_wang_id(ASYMMETRIC_WANG_ID, transform)
        candidates = find_wang_tile_candidates(wang_set, constraints)
        assert len(candidates) == 1
        assert candidates[0].transform == transform


def test_empty_constraints(terrain_wang_set):
    candidates = find_wang_tile_candidates(terrain_wang_set)
    # 40 Wang tiles, none of them all-zero, 8 transforms each.
    assert len(candidates) == 40 * 8
    match = find_wang_tile(terrain_wang_set, seed=5)
    assert match is not None
    assert match in candidates


def test_partial_constraints(terrain_wang_set):
    constraints = WangTileConstraints(top=2, left=2)
    candidates = find_wang_tile_candidates(terrain_wang_set, constraints)
    assert candidates
    for candidate in candidates:
        assert candidate.wang_id[0] == 2
        assert candidate.wang_id[6] == 2


def test_constraints_as_sequence(terrain_wang_set):
    constraints = [2, None, None, None, None, None, 2, None]
    assert find_wang_tile_candidates(
        terrain_wang_set, constraints
    ) == find_wang_tile_candidates(terrain_wang_set, WangTileConstraints(top=2, left=2))
    with pytest.raises(ValueError):
        find_wang_tile_candidates(terrain_wang_set, [1, 2, 3])


def test_weighted_selection_is_reproducible():
    wang_id = [1, 1, 1, 1, 2, 2, 2, 2]
    wang_set = make_wang_set(
        [
            WangTile(tile_id=10, wang_id=wang_id),
            WangTile(tile_id=20, wang_id=list(wang_id)),
        ]
    )
    constraints = list(wang_id)

    first = find_wang_tile(wang_set, constraints, seed=42)
    second = find_wang_tile(wang_set, constraints, seed=42)
    assert first == second

    # A zero weight excludes a candidate entirely.
    for seed in range(20):
        match = find_wang_tile(wang_set, constraints, weights={20: 0.0}, seed=seed)
        assert match.tile_id == 10
        match = find_wang_tile(wang_set, constraints, weights={10: 0.0}, seed=seed)
        assert match.tile_id == 20

    # With equal weights both tiles get picked across a range of seeds.
    picked = {
        find_wang_tile(wang_set, constraints, seed=seed).tile_id
        for seed in range(200)
    }
    assert picked == {10, 20}


def test_invalid_weights():
    wang_set = make_wang_set([WangTile(tile_id=10, wang_id=[1, 1, 1, 1, 2, 2, 2, 2])])
    with pytest.raises(ValueError):
        find_wang_tile(wang_set, weights={10: -1.0}, seed=1)
    with pytest.raises(ValueError):
        find_wang_tile(wang_set, weights={10: 0.0}, seed=1)


def test_no_candidates_returns_none(terrain_wang_set):
    constraints = [2, 3, 2, 3, 2, 3, 2, 3]
    assert find_wang_tile_candidates(terrain_wang_set, constraints) == []
    assert find_wang_tile(terrain_wang_set, constraints, seed=1) is None


def test_invalid_constraint_color(terrain_wang_set):
    with pytest.raises(InvalidWangColorError):
        find_wang_tile_candidates(terrain_wang_set, WangTileConstraints(top=99))
    with pytest.raises(InvalidWangColorError):
        find_wang_tile_candidates(terrain_wang_set, WangTileConstraints(top=-1))


def test_invalid_wang_id_color():
    wang_set = make_wang_set(
        [WangTile(tile_id=1, wang_id=[1, 1, 1, 1, 9, 1, 1, 1])], color_count=2
    )
    with pytest.raises(InvalidWangColorError):
        find_wang_tile_candidates(wang_set)


def test_duplicate_tile_ids():
    wang_set = make_wang_set([WangTile(tile_id=1, wang_id=[1, 1, 1, 1, 1, 1, 1, 1])])
    # Forge a duplicate: two dict entries whose WangTile has the same tile_id.
    wang_set.wang_tiles[2] = WangTile(tile_id=1, wang_id=[2, 2, 2, 2, 2, 2, 2, 2])
    with pytest.raises(DuplicateTileIdError):
        find_wang_tile_candidates(wang_set)


def test_all_zero_wang_id_is_skipped():
    wang_set = make_wang_set(
        [
            WangTile(tile_id=5, wang_id=[0, 0, 0, 0, 0, 0, 0, 0]),
            WangTile(tile_id=6, wang_id=[1, 1, 1, 1, 1, 1, 1, 1]),
        ]
    )
    candidates = find_wang_tile_candidates(wang_set)
    assert candidates
    assert {candidate.tile_id for candidate in candidates} == {6}
    # An all-zero request can not be satisfied either.
    assert find_wang_tile(wang_set, [0] * 8, seed=1) is None


def test_unsupported_wang_type():
    wang_set = make_wang_set(
        [WangTile(tile_id=1, wang_id=[1, 1, 1, 1, 1, 1, 1, 1])], wang_type="hexagonal"
    )
    with pytest.raises(UnsupportedWangTypeError):
        find_wang_tile_candidates(wang_set)


def test_invalid_wang_id_length():
    wang_set = make_wang_set([WangTile(tile_id=1, wang_id=[1, 2, 3, 4])])
    with pytest.raises(InvalidWangIdError):
        find_wang_tile_candidates(wang_set)


def test_edge_type_set():
    wang_set = make_wang_set(
        [WangTile(tile_id=1, wang_id=[1, 0, 2, 0, 1, 0, 2, 0])],
        wang_type="edge",
        color_count=2,
    )
    candidates = find_wang_tile_candidates(
        wang_set, WangTileConstraints(top=1, right=2)
    )
    assert candidates
    for candidate in candidates:
        assert candidate.wang_id[0] == 1
        assert candidate.wang_id[2] == 2
    # Corner constraints are meaningless for an edge set.
    with pytest.raises(WangPickerError):
        find_wang_tile_candidates(wang_set, WangTileConstraints(top_right=1))


def test_corner_type_set():
    wang_set = make_wang_set(
        [WangTile(tile_id=1, wang_id=[0, 1, 0, 2, 0, 1, 0, 2])],
        wang_type="corner",
        color_count=2,
    )
    candidates = find_wang_tile_candidates(
        wang_set, WangTileConstraints(top_right=1, bottom_left=1)
    )
    assert candidates
    for candidate in candidates:
        assert candidate.wang_id[1] == 1
        assert candidate.wang_id[5] == 1
    # Edge constraints are meaningless for a corner set.
    with pytest.raises(WangPickerError):
        find_wang_tile_candidates(wang_set, WangTileConstraints(top=1))
