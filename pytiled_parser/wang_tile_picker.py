"""Automatic Wang tile selection.

This module implements picking a [WangTile][pytiled_parser.wang_set.WangTile] out of a
[WangSet][pytiled_parser.wang_set.WangSet] given a set of edge/corner color constraints,
so that map generators don't have to choose terrain tiles by hand.

Colors are referenced by their index within
[WangSet.wang_colors][pytiled_parser.wang_set.WangSet], exactly like Tiled stores
them in a Wang ID: ``0`` means "no color set" and ``1..N`` refer to the colors of
the set.

Wang IDs (and therefore constraints) are ordered the same way Tiled orders them:
``[top, top_right, right, bottom_right, bottom, bottom_left, left, top_left]``.
"""

import random
from typing import List, Mapping, Optional, Sequence, Union

import attr

from pytiled_parser.wang_set import WangSet

#: Positions within a Wang ID that belong to edges.
EDGE_POSITIONS = (0, 2, 4, 6)

#: Positions within a Wang ID that belong to corners.
CORNER_POSITIONS = (1, 3, 5, 7)

_POSITION_NAMES = (
    "top",
    "top_right",
    "right",
    "bottom_right",
    "bottom",
    "bottom_left",
    "left",
    "top_left",
)

_SUPPORTED_WANG_TYPES = ("corner", "edge", "mixed")


class WangPickerError(Exception):
    """Base class for all errors raised by the Wang tile picker."""


class UnsupportedWangTypeError(WangPickerError, ValueError):
    """Raised when a WangSet has a wang_type the picker does not support."""


class InvalidWangColorError(WangPickerError, ValueError):
    """Raised when a color index is not valid for the given WangSet."""


class DuplicateTileIdError(WangPickerError, ValueError):
    """Raised when a WangSet contains the same tile ID more than once."""


class InvalidWangIdError(WangPickerError, ValueError):
    """Raised when a WangTile has a malformed Wang ID."""


@attr.s(auto_attribs=True)
class WangTileConstraints:
    """Color constraints for the eight sides/corners of a tile.

    Every attribute is optional. Any direction left as ``None`` is unconstrained,
    which allows for empty constraints (everything ``None``) and partial adjacency
    (only some neighbors known). A value of ``0`` explicitly requires that direction
    to have no color set on the picked tile.

    Attributes:
        top: Color index required on the top edge.
        top_right: Color index required on the top right corner.
        right: Color index required on the right edge.
        bottom_right: Color index required on the bottom right corner.
        bottom: Color index required on the bottom edge.
        bottom_left: Color index required on the bottom left corner.
        left: Color index required on the left edge.
        top_left: Color index required on the top left corner.
    """

    top: Optional[int] = None
    top_right: Optional[int] = None
    right: Optional[int] = None
    bottom_right: Optional[int] = None
    bottom: Optional[int] = None
    bottom_left: Optional[int] = None
    left: Optional[int] = None
    top_left: Optional[int] = None


@attr.s(auto_attribs=True)
class WangTileTransform:
    """The rotation/flip to apply to a tile so its Wang colors match a request.

    Attributes:
        rotation: Clockwise rotation in degrees, one of 0, 90, 180, 270.
        flip_horizontal: Whether to mirror the tile horizontally. The flip is
            applied before the rotation.
    """

    rotation: int = 0
    flip_horizontal: bool = False


@attr.s(auto_attribs=True)
class WangTileMatch:
    """A tile plus the transform needed to satisfy a set of constraints.

    Attributes:
        tile_id: The ID of the matching tile within its tileset.
        transform: The
            [WangTileTransform][pytiled_parser.wang_tile_picker.WangTileTransform]
            to apply to the tile.
        wang_id: The Wang ID of the tile *after* the transform has been applied, in
            Tiled's order: top, top right, right, bottom right, bottom, bottom left,
            left, top left. Every constrained direction of the request is equal to
            the value at the same position here.
    """

    tile_id: int
    transform: WangTileTransform
    wang_id: List[int]


ConstraintsLike = Union[WangTileConstraints, Sequence[Optional[int]], None]


def _normalize_constraints(constraints: ConstraintsLike) -> List[Optional[int]]:
    if constraints is None:
        return [None] * 8
    if isinstance(constraints, WangTileConstraints):
        return [getattr(constraints, name) for name in _POSITION_NAMES]
    values = list(constraints)
    if len(values) != 8:
        raise ValueError(
            f"Constraints given as a sequence must have exactly 8 entries, "
            f"got {len(values)}"
        )
    return values


def _validate_color(color: int, color_count: int, context: str) -> None:
    if not isinstance(color, int) or isinstance(color, bool):
        raise InvalidWangColorError(f"{context}: color {color!r} is not an integer")
    if color < 0 or color > color_count:
        raise InvalidWangColorError(
            f"{context}: color {color} is out of range, the WangSet has "
            f"{color_count} colors so valid values are 0..{color_count}"
        )


def transform_wang_id(
    wang_id: Sequence[int], transform: WangTileTransform
) -> List[int]:
    """Apply a [WangTileTransform][pytiled_parser.wang_tile_picker.WangTileTransform]
    to a Wang ID and return the resulting Wang ID.

    Args:
        wang_id: The 8 color indexes of the tile, in Tiled's order.
        transform: The transform to apply. The horizontal flip is applied first,
            then the clockwise rotation.

    Returns:
        The transformed Wang ID as a new list of 8 color indexes.
    """
    if len(wang_id) != 8:
        raise InvalidWangIdError(
            f"A Wang ID must have exactly 8 entries, got {len(wang_id)}"
        )
    rotation = transform.rotation % 360
    if rotation % 90 != 0:
        raise ValueError(
            f"Rotation must be a multiple of 90 degrees, got {transform.rotation}"
        )

    result = list(wang_id)
    if transform.flip_horizontal:
        # Mirror across the vertical axis: position k takes the value of -k.
        result = [result[-i % 8] for i in range(8)]
    quarter_turns = rotation // 90
    if quarter_turns:
        # Each quarter turn moves every position two slots forward.
        result = [result[(i - 2 * quarter_turns) % 8] for i in range(8)]
    return result


def find_wang_tile_candidates(
    wang_set: WangSet, constraints: ConstraintsLike = None
) -> List[WangTileMatch]:
    """Find every tile/transform combination in a WangSet matching the constraints.

    Args:
        wang_set: The [WangSet][pytiled_parser.wang_set.WangSet] to search.
        constraints: The color constraints to match. Accepts a
            [WangTileConstraints][pytiled_parser.wang_tile_picker.WangTileConstraints],
            a sequence of 8 optional color indexes in Tiled's Wang ID order, or
            ``None`` for no constraints at all.

    Returns:
        A list of [WangTileMatch][pytiled_parser.wang_tile_picker.WangTileMatch], in a
        deterministic order (Wang tile order, then transform order). May be empty if
        nothing matches. Wang tiles whose Wang ID is all zeros carry no terrain
        information and are never returned as candidates.

    Raises:
        UnsupportedWangTypeError: If the WangSet's type is not one of
            ``corner``, ``edge`` or ``mixed``.
        InvalidWangColorError: If a constraint (or a Wang ID in the set) references
            a color that does not exist in the WangSet.
        DuplicateTileIdError: If two Wang tiles in the set share a tile ID.
        InvalidWangIdError: If a Wang tile's Wang ID does not have 8 entries.
        WangPickerError: If a constraint targets a direction the WangSet's type
            does not use (corners of an ``edge`` set or edges of a ``corner`` set).
    """
    wang_type = wang_set.wang_type.lower()
    if wang_type not in _SUPPORTED_WANG_TYPES:
        raise UnsupportedWangTypeError(
            f"Unsupported WangSet type {wang_set.wang_type!r}, "
            f"supported types are: {', '.join(_SUPPORTED_WANG_TYPES)}"
        )

    if wang_type == "edge":
        allowed_positions = EDGE_POSITIONS
    elif wang_type == "corner":
        allowed_positions = CORNER_POSITIONS
    else:
        allowed_positions = tuple(range(8))

    wanted = _normalize_constraints(constraints)
    color_count = len(wang_set.wang_colors)
    for position, color in enumerate(wanted):
        if color is None:
            continue
        if position not in allowed_positions:
            raise WangPickerError(
                f"WangSet {wang_set.name!r} is of type {wang_type!r} and does not "
                f"use the {_POSITION_NAMES[position]!r} direction"
            )
        _validate_color(color, color_count, f"constraint {_POSITION_NAMES[position]!r}")

    seen_tile_ids = set()
    for wang_tile in wang_set.wang_tiles.values():
        if wang_tile.tile_id in seen_tile_ids:
            raise DuplicateTileIdError(
                f"WangSet {wang_set.name!r} contains tile ID "
                f"{wang_tile.tile_id} more than once"
            )
        seen_tile_ids.add(wang_tile.tile_id)

    matches = []
    for wang_tile in wang_set.wang_tiles.values():
        wang_id = wang_tile.wang_id
        if len(wang_id) != 8:
            raise InvalidWangIdError(
                f"Tile {wang_tile.tile_id} has a Wang ID with {len(wang_id)} "
                f"entries, expected 8"
            )
        for color in wang_id:
            _validate_color(color, color_count, f"tile {wang_tile.tile_id}")
        if all(color == 0 for color in wang_id):
            # An all-zero Wang ID is the "empty" tile; it carries no terrain
            # information and is never a meaningful candidate.
            continue
        for flip_horizontal in (False, True):
            for rotation in (0, 90, 180, 270):
                transform = WangTileTransform(
                    rotation=rotation, flip_horizontal=flip_horizontal
                )
                transformed = transform_wang_id(wang_id, transform)
                if all(
                    wanted[position] is None
                    or transformed[position] == wanted[position]
                    for position in allowed_positions
                ):
                    matches.append(
                        WangTileMatch(
                            tile_id=wang_tile.tile_id,
                            transform=transform,
                            wang_id=transformed,
                        )
                    )
    return matches


def find_wang_tile(
    wang_set: WangSet,
    constraints: ConstraintsLike = None,
    weights: Optional[Mapping[int, float]] = None,
    seed: Optional[int] = None,
) -> Optional[WangTileMatch]:
    """Pick a single tile from a WangSet matching the given constraints.

    All candidates returned by
    [find_wang_tile_candidates][pytiled_parser.wang_tile_picker.find_wang_tile_candidates]
    are equally valid matches; one of them is chosen at random, weighted by the
    caller supplied weights. Given the same WangSet, constraints, weights and seed,
    the choice is fully reproducible.

    Args:
        wang_set: The [WangSet][pytiled_parser.wang_set.WangSet] to search.
        constraints: The color constraints to match, see
            [find_wang_tile_candidates][pytiled_parser.wang_tile_picker.find_wang_tile_candidates].
        weights: An optional mapping of tile ID to selection weight. Tiles without
            an entry get a weight of 1.0. Weights must be non-negative and at least
            one candidate must have a positive weight.
        seed: Seed for the random number generator. Use the same seed to reproduce
            a previous choice.

    Returns:
        A [WangTileMatch][pytiled_parser.wang_tile_picker.WangTileMatch], or ``None``
        if no tile in the set can satisfy the constraints.

    Raises:
        ValueError: If a weight is negative or every candidate has a zero weight.
        WangPickerError: For the same validation errors as
            [find_wang_tile_candidates][pytiled_parser.wang_tile_picker.find_wang_tile_candidates].
    """
    candidates = find_wang_tile_candidates(wang_set, constraints)
    if not candidates:
        return None

    if weights is None:
        weights = {}
    resolved_weights = []
    for candidate in candidates:
        weight = weights.get(candidate.tile_id, 1.0)
        if weight < 0:
            raise ValueError(
                f"Weight for tile {candidate.tile_id} must be non-negative, "
                f"got {weight}"
            )
        resolved_weights.append(weight)
    if sum(resolved_weights) <= 0:
        raise ValueError("At least one candidate tile must have a positive weight")

    rng = random.Random(seed)
    return rng.choices(candidates, weights=resolved_weights, k=1)[0]
