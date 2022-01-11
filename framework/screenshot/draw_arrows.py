from math import sin, cos, pi
from enum import IntEnum


class Direction(IntEnum):
    RIGHT = 0
    BOTTOM_RIGHT = 1
    BOTTOM = 2
    BOTTOM_LEFT = 3
    LEFT = 4
    TOP_LEFT = 5
    TOP = 6
    TOP_RIGHT = 7


class CoordinateArrow:
    """
    Drawing arrows depending on the coordinates
    """

    def get_arrow_coordinate(self, at_coordinates, length, tip_width, tip_height: float,
                             from_: Direction):
        at_x, at_y = at_coordinates
        arrow = self._base(length, tip_width, tip_height / 2)
        self._rotate(arrow, from_)
        self._move(arrow, at_x, at_y)
        return tuple([tuple(l[0] + l[1]) for l in arrow])

    @staticmethod
    def _rotate(base, d):
        """
        Rotation depending on the selected side.
        """
        sin_ang = sin(d.value * pi / 4)
        cos_ang = cos(d.value * pi / 4)

        for l_idx, line in enumerate(base):
            for p_idx, point in enumerate(line):
                x, y = point
                base[l_idx][p_idx][0] = x * cos_ang - y * sin_ang
                base[l_idx][p_idx][1] = x * sin_ang + y * cos_ang

    @staticmethod
    def _move(base, x0, y0):
        for l_idx, line in enumerate(base):
            for p_idx, point in enumerate(line):
                x, y = point
                base[l_idx][p_idx][0] = x + x0
                base[l_idx][p_idx][1] = y + y0

    @staticmethod
    def _base(l, sl, sw):
        return (
            ([0, 0], [l, 0]),
            ([0, 0], [sl, sw]),
            ([0, 0], [sl, -sw]),
        )