"""Parse Tiled Maps and Tilesets

See: https://www.mapeditor.org/

This library is for parsing JSON formatted Tiled Map Editormaps and tilesets to be
    used as maps and levels for 2D top-down (orthogonal, hexogonal, or isometric)
    or side-scrolling games in a strictly typed fashion.

PyTiled Parser is not tied to any particular graphics library or game engine.
"""

# pylint: disable=too-few-public-methods

from .common_types import Color, OrderedPair, Size
from .exception import UnknownFormat
from .layer import Chunk, ImageLayer, Layer, LayerGroup, ObjectLayer, TileLayer
from .parser import parse_map, parse_world, parse_tileset
from .properties import Properties, Property
from .tiled_map import TiledMap
from .tileset import Frame, Grid, Tile, Tileset, Transformations
from .wang_tile_picker import (
    DuplicateTileIdError,
    InvalidWangColorError,
    InvalidWangIdError,
    UnsupportedWangTypeError,
    WangPickerError,
    WangTileConstraints,
    WangTileMatch,
    WangTileTransform,
    find_wang_tile,
    find_wang_tile_candidates,
    transform_wang_id,
)
from .world import World, WorldMap

__all__ = [
    "Color",
    "OrderedPair",
    "Size",
    "UnknownFormat",
    "Chunk",
    "ImageLayer",
    "Layer",
    "LayerGroup",
    "ObjectLayer",
    "TileLayer",
    "parse_map",
    "parse_world",
    "parse_tileset",
    "Properties",
    "Property",
    "TiledMap",
    "Frame",
    "Grid",
    "Tile",
    "Tileset",
    "Transformations",
    "DuplicateTileIdError",
    "InvalidWangColorError",
    "InvalidWangIdError",
    "UnsupportedWangTypeError",
    "WangPickerError",
    "WangTileConstraints",
    "WangTileMatch",
    "WangTileTransform",
    "find_wang_tile",
    "find_wang_tile_candidates",
    "transform_wang_id",
    "World",
    "WorldMap",
]
