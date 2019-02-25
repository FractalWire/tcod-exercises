from __future__ import annotations
from typing import Union, Tuple, Optional
from enum import IntEnum, auto
import tcod


class Origin(IntEnum):
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    CENTER = auto()


class Outbound(IntEnum):
    ALLOWED = auto()
    PARTIAL = auto()
    STRICT = auto()


class Border(IntEnum):
    NONE = 0
    EMPTY = auto()
    SOLID = auto()
    DOUBLE = auto()
    DOTTED = auto()
    DASHED = auto()
    PATTERN1 = auto()
    PATTERN2 = auto()
    PATTERN3 = auto()


def draw_border(console: tcod.console.Console, style: Style) -> None:

    if style.border != Border.NONE:
        ch = ch = (ord(' '),)*6
        if style.border == Border.SOLID:
            ch = (196, 179, 218, 191, 192, 217)
        elif style.border == Border.DOUBLE:
            ch = (205, 186, 201, 187, 200, 188)
        elif style.border == Border.EMPTY:
            ch = (ord(' '),)*6
        elif style.border == Border.DOTTED:
            ch = (ord('.'),)*6
        elif style.border == Border.DASHED:
            ch = (ord('-'), ord('|')) + (ord('+'),)*4
        elif style.border == Border.PATTERN1:
            ch = (176,)*6
        elif style.border == Border.PATTERN2:
            ch = (177,)*6
        elif style.border == Border.PATTERN3:
            ch = (178,)*6

        h, v, tl, tr, bl, br = ch

        bg = style.bg_color if style.border_bg_color is None \
            else style.border_bg_color
        fg = style.fg_color if style.border_fg_color is None \
            else style.border_fg_color

        console.ch[[0, -1], :] = h
        console.ch[:, [0, -1]] = v
        console.ch[[[0, -1], [-1, 0]], [0, -1]] = [[tl, br], [bl, tr]]

        console.bg[[0, -1], :] = bg
        console.bg[:, [0, -1]] = bg

        console.fg[[0, -1], :] = fg
        console.fg[:, [0, -1]] = fg


def transform_coords(x: int, y: int, x_max: int, y_max: int,
                     width: int, height: int,
                     origin: Origin, outbound: Outbound) -> Tuple[int, int]:
    if outbound == Outbound.PARTIAL:
        x, y = x % x_max, y % y_max

    var = {
        Origin.TOP_LEFT: (0, 0),
        Origin.TOP_RIGHT: (-width, 0),
        Origin.BOTTOM_LEFT: (0, -height),
        Origin.BOTTOM_RIGHT: (-width, -height),
        Origin.CENTER: (-width//2, -width//2),
    }
    x = x + var[origin][0]
    y = y + var[origin][1]

    if outbound == Outbound.STRICT:
        x = sorted([0-var[origin][0], x, x_max-width-var[origin][0]])[1]
        y = sorted([0-var[origin][1], y, y_max-height-var[origin][1]])[1]

    return (x, y)


class Style:
    """The various styles applicable to a Canvas

    Args :
        x: Union[int,float]: the relative x position of a Canvas in respect to
            his hypotetical parent
        y: Union[int,float]: the relative y position of a Canvas in respect to
            his hypotetical parent
        width: Union[int,float]: the relative width of a Canvas in respect to
            his hypotetical parent
        height: Union[int,float]: the relative height of a Canvas in respect
            to his hypotetical parent
        origin: Origin: the point of origin from where the Canvas should be
            drawn. Does not affect the internal origin of the Canvas (top-left)
        outbound: Outbound: if True the origin can be set out-of-bound of
            his parent. If False, the Canvas' origin will be restricted to the
            parent's geometry, negative value will also stay in-bound starting
            from the bottom-right corner of the parent.
        bg_alpha: float: the alpha value for the background
        fg_alpha: float: the alpha value for the foreground
        bg_color: tcod.Color: the color for the background
        fg_color: tcod.Color: the color for the foreground
        key_color: Optional[tcod.Color]: a color to set as transparent. If None,
            no transparent color  will be set
        # has_border: bool: Wether or not the Canvas has border
        border_style: Border:
        visible: bool: Wether or not a Canvas should be visible. Note: if a
            Canvas is IUpdatable, it might still update itself if visible is set
            to False.

    """

    def __init__(self, **kwargs):
        self.x: Union[int, float] = 0
        self.y: Union[int, float] = 0
        self.width: Union[int, float] = 0
        self.height: Union[int, float] = 0
        self.min_width: Optional[int] = None
        self.max_width: Optional[int] = None
        self.min_height: Optional[int] = None
        self.max_height: Optional[int] = None

        self.origin = Origin.TOP_LEFT
        self.outbound = Outbound.ALLOWED

        self.bg_alpha = 1.
        self.fg_alpha = 1.
        self._bg_color = tcod.black
        self._fg_color = tcod.white
        self._key_color: Optional[tcod.Color] = None

        # self.has_border = False
        self.border = Border.NONE
        self._border_bg_color: Optional[tcod.Color] = None
        self._border_fg_color: Optional[tcod.Color] = None

        self.visible = True

        self.update(kwargs)

    def update(self, kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise AttributeError(f"{k} is not a valid Style attribute.")
            setattr(self, k, v)

    @property
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value: Tuple[int, int, int]):
        self._bg_color = tcod.Color(*value)

    @property
    def fg_color(self):
        return self._fg_color

    @fg_color.setter
    def fg_color(self, value: Tuple[int, int, int]):
        self._fg_color = tcod.Color(*value)

    @property
    def key_color(self):
        return self._key_color

    @key_color.setter
    def key_color(self, value: Tuple[int, int, int]):
        self._key_color = tcod.Color(*value)

    @property
    def border_bg_color(self):
        return self._border_bg_color

    @border_bg_color.setter
    def border_bg_color(self, value: Tuple[int, int, int]):
        self._border_bg_color = tcod.Color(*value)

    @property
    def border_fg_color(self):
        return self._border_fg_color

    @border_fg_color.setter
    def border_fg_color(self, value: Tuple[int, int, int]):
        self._border_fg_color = tcod.Color(*value)
