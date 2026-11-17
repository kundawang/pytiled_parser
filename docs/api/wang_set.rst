.. _wang_set_api:
Wang Set
========

This module contains a number of classes related to Wang Sets.

Wang Sets are the underlying data used by Tiled's terrain system. It is unlikely this module will
ever need touched for creating an implementation in a game engine. It is primarily data used by the
editor during map creation.

See `Tiled's docs about terrain <https://doc.mapeditor.org/en/stable/manual/terrain/>`_
and also the `TMX Reference <https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#wangsets>`_
and the `JSON Reference <https://doc.mapeditor.org/en/stable/reference/json-map-format/#wang-set>`_

WangSet
^^^^^^^

.. autoclass:: pytiled_parser.wang_set.WangSet

WangColor
^^^^^^^^^

.. autoclass:: pytiled_parser.wang_set.WangColor

WangTile
^^^^^^^^

.. autoclass:: pytiled_parser.wang_set.WangTile

.. _wang_tile_picker_api:
Wang Tile Picker
================

This module implements automatically choosing a tile out of a WangSet given edge/corner
color constraints, including the rotation/flip needed to make the tile match. It is meant
for map/level generators working on top of parsed Wang Sets.

find_wang_tile
^^^^^^^^^^^^^^

.. autofunction:: pytiled_parser.wang_tile_picker.find_wang_tile

find_wang_tile_candidates
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: pytiled_parser.wang_tile_picker.find_wang_tile_candidates

transform_wang_id
^^^^^^^^^^^^^^^^^

.. autofunction:: pytiled_parser.wang_tile_picker.transform_wang_id

WangTileConstraints
^^^^^^^^^^^^^^^^^^^

.. autoclass:: pytiled_parser.wang_tile_picker.WangTileConstraints

WangTileMatch
^^^^^^^^^^^^^

.. autoclass:: pytiled_parser.wang_tile_picker.WangTileMatch

WangTileTransform
^^^^^^^^^^^^^^^^^

.. autoclass:: pytiled_parser.wang_tile_picker.WangTileTransform