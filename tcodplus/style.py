from __future__ import annotations
from collections.abc import Mapping
from typing import Union, Tuple, Optional, Any, Dict
from enum import IntEnum, auto
import tcod


class Display(IntEnum):
    NONE = 0
    INITIAL = auto()


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


def origin_coords(x: int, y: int, x_max: int, y_max: int,
                  width: int, height: int,
                  origin: Origin) -> Tuple[int, int]:
    """origin_coords returns the coordinate to as if it was a TOP_LEFT origin

    Returns:
        Tuple[int]: the transformed coordinates (x,y)
    """
    var = {
        Origin.TOP_LEFT: (0, 0),
        Origin.TOP_RIGHT: (-width, 0),
        Origin.BOTTOM_LEFT: (0, -height),
        Origin.BOTTOM_RIGHT: (-width, -height),
        Origin.CENTER: (-width//2, -width//2),
    }
    x = x + var[origin][0]
    y = y + var[origin][1]

    return (x, y)


def bounded_coords(x: int, y: int, x_max: int, y_max: int,
                   width: int, height: int,
                   outbound: Outbound) -> Tuple[int, int]:
    """bounded_coords returns the coordinates based on the outbound style

    Outbound.PARTIAL makes the negative coordinate start from the opposite side.
    A coordinate > coordinate_max will be restricted to [0, max_coordinate]

    Outbound.STRICT makes the coordinates 'stick' to a side if
    0 > coordinate > max_coordinate

    Returns:
        Tuple[int]: the bounded coordinates (x,y)
    """
    if outbound == Outbound.PARTIAL:
        x, y = x % x_max, y % y_max

    elif outbound == Outbound.STRICT:
        x = sorted([0, x, x_max-width])[1]
        y = sorted([0, y, y_max-height])[1]

    return (x, y)


OptionalColor = Optional[Tuple[int, int, int]]


def _get_optional_color(value: OptionalColor) -> tcod.Color():
    return None if value is None else tcod.Color(*value)


class Style:
    """The various styles applicable to a Canvas

    Args :
        x: Union[str,int,float]: the relative x position of a Canvas in respect
            to his hypotetical parent
        y: Union[str,int,float]: the relative y position of a Canvas in respect
            to his hypotetical parent
        width: Union[str,int,float]: the relative width of a Canvas in respect
            to his hypotetical parent
        height: Union[str,int,float]: the relative height of a Canvas in respect
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

    def __init__(self, other: Any = None, **kwargs):
        # TODO: outsource default args. Right now double memory usage for styles
        self._default_attrs = dict()
        self._non_default_attrs = set()

        self._is_modified = False
        self._lock_attrs = False

        # Following attrs will be default

        self.x: Union[str, int, float] = "auto"
        self.y: Union[str, int, float] = "auto"
        self.width: Union[str, int, float] = "auto"
        self.height: Union[str, int, float] = "auto"
        self.min_width: Optional[int] = None
        self.max_width: Optional[int] = None
        self.min_height: Optional[int] = None
        self.max_height: Optional[int] = None

        self.origin = Origin.TOP_LEFT
        self.outbound = Outbound.ALLOWED

        self.bg_alpha = 1.
        self.fg_alpha = 1.
        self._bg_color: OptionalColor = None  # Probably no Optional here...
        self._fg_color: OptionalColor = None
        self._key_color: OptionalColor = None

        # TODO: really need some better default handling !!!
        self.bg_color = tcod.black  # Important for deafault registration
        self.fg_color = tcod.white

        # self.has_border = False
        self.border = Border.NONE
        self._border_bg_color: OptionalColor = None
        self._border_fg_color: OptionalColor = None

        self.border_bg_color = None
        self.border_fg_color = None

        self.display = Display.INITIAL
        self.visible = True

        self._lock_attrs = True  # following update will be non-default
        self.update(other, **kwargs)

    def __setattr__(self: Style, name: str, value: Any) -> None:
        if name[0] != "_":
            if self._lock_attrs:
                if not hasattr(self, name):
                    raise AttributeError(f"{name} is not a valid "
                                         f"Style attribute.")
                else:
                    self._non_default_attrs.add(name)
                    self._is_modified = True
            else:
                self._default_attrs[name] = value
        super().__setattr__(name, value)

    def __copy__(self) -> Style:
        return type(self)(self.non_defaults)

    def __or__(self, other: Union[Style, Mapping]) -> Style:
        # only get the non-default style that are not non-default for self
        if isinstance(other, Mapping):
            d_other = {k: other[k]
                       for k in other.keys() - self._non_default_attrs}
        else:
            d_other = {k: getattr(other, k)
                       for k in other._non_default_attrs - self._non_default_attrs}
        d_combined = {**self.non_defaults, **d_other}
        return type(self)(**d_combined)

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.non_defaults})"

    @property
    def is_modified(self):
        return self._is_modified

    @property
    def non_defaults(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self._non_default_attrs}

    def update(self, other: Any = None, **kwargs) -> None:
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def copy(self) -> Style:
        return self.__copy__()

    def reset_defaults(self, *args: str) -> None:
        if not args:
            args = self._default_attrs
        for arg in args:
            if isinstance(getattr(self, arg), property):
                arg = f"_{arg}"
            setattr(self, arg, self._default_attrs[arg])
            self._non_default_attrs -= {arg}

    @property
    def bg_color(self) -> None:
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value: OptionalColor) -> None:
        self._bg_color = _get_optional_color(value)

    @property
    def fg_color(self) -> None:
        return self._fg_color

    @fg_color.setter
    def fg_color(self, value: OptionalColor) -> None:
        self._fg_color = _get_optional_color(value)

    @property
    def key_color(self) -> None:
        return self._key_color

    @key_color.setter
    def key_color(self, value: OptionalColor) -> None:
        self._key_color = _get_optional_color(value)

    @property
    def border_bg_color(self) -> None:
        return self._border_bg_color

    @border_bg_color.setter
    def border_bg_color(self, value: OptionalColor) -> None:
        self._border_bg_color = _get_optional_color(value)

    @property
    def border_fg_color(self) -> None:
        return self._border_fg_color

    @border_fg_color.setter
    def border_fg_color(self, value: OptionalColor) -> None:
        self._border_fg_color = _get_optional_color(value)
