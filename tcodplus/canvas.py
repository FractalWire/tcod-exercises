import abc
from typing import Union, List, Dict, Callable, NamedTuple
import tcod
import tcod.event
import time
import textwrap
import copy


class IDrawable(abc.ABC):
    @abc.abstractmethod
    def draw(self, dest: 'Canvas') -> None:
        pass


class IFocusable(abc.ABC):
    @abc.abstractmethod
    def isfocused(self, event: tcod.event.MouseMotion) -> bool:
        pass

    @property
    @abc.abstractmethod
    def focus_dispatcher(self) -> 'EventDispatcher':
        pass


class IUpdatable(abc.ABC):
    @property
    @abc.abstractmethod
    def should_update(self) -> bool:
        pass

    @should_update.setter
    @abc.abstractmethod
    def should_update(self, value: bool) -> None:
        pass

    @abc.abstractmethod
    def update(self) -> None:
        pass


Geometry = NamedTuple('Geometry', [(
    'abs_x', int), ('abs_y', int), ('x', int), ('y', int), ('width', int), ('height', int)])


def relative_geometry(dest: 'Canvas', rel_x: Union[int, float],
                      rel_y: Union[int, float], rel_width: Union[int, float],
                      rel_height: Union[int, float]) -> List[int]:
    if dest != None:
        if dest.geometry == None:
            return Geometry(0, 0, 0, 0, 0, 0)
        d_abs_x, d_abs_y, _, _, d_width, d_height = dest.geometry
        x = rel_x if isinstance(rel_x, int) else int(rel_x*d_width)
        y = rel_y if isinstance(rel_y, int) else int(rel_y*d_height)
        abs_x = d_abs_x + x
        abs_y = d_abs_y + y
        width = rel_width if isinstance(rel_width, int) \
            else int(rel_width*d_width)
        height = rel_height if isinstance(rel_height, int) \
            else int(rel_height*d_height)

        return Geometry(abs_x, abs_y, x, y, width, height)

    return Geometry(0, 0, 0, 0, rel_width, rel_height)


class Canvas(IDrawable):
    def __init__(self, x: Union[int, float] = 0, y: Union[int, float] = 0,
                 width: Union[int, float] = 0, height: Union[int, float] = 0,
                 fg_alpha: float = 1, bg_alpha: float = 1,
                 console: tcod.console.Console = None) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self._geom = None
        if console != None:
            self._geom = Geometry(0, 0, 0, 0, console.width, console.height)

        self.childs = list()
        self._focused_childs = list()
        self.console = console
        self.fg_alpha = fg_alpha
        self.bg_alpha = bg_alpha
        self.visible = True

    @property
    def geometry(self):
        return self._geom

    @property
    def focused_childs(self):
        return self._focused_childs

    def draw(self, dest: 'Canvas') -> None:
        x, y, width, height = self.geometry[2:]
        self.console.blit(dest.console, x, y, 0, 0, width, height,
                          self.fg_alpha, self.bg_alpha)

    def update_mouse_focused(self, event: tcod.event.Event) -> List['Canvas']:
        focusable_childs = [c for c in self.childs if isinstance(c, IFocusable)]
        focused = [c for c in focusable_childs if c.isfocused(event)]

        childs_focus_gain = [c for c in focused
                             if c not in self._focused_childs]
        if len(childs_focus_gain) > 0:
            evt_mousefocusgain = MouseFocusChange(event,"MOUSEFOCUSGAIN")
            for c in childs_focus_gain:
                c.focus_dispatcher.dispatch(evt_mousefocusgain)

        childs_focus_lost = [c for c in focusable_childs
                             if c in self._focused_childs and c not in focused]
        if len(childs_focus_lost) > 0:
            evt_mousefocuslost = MouseFocusChange(event,"MOUSEFOCUSLOST")
            for c in childs_focus_lost:
                c.focus_dispatcher.dispatch(evt_mousefocuslost)

        for c in self.childs:
            focused += c.update_mouse_focused(event)

        self._focused_childs = focused
        return focused

    def update_geometry(self, dest: 'Canvas') -> bool:

        geom_new = relative_geometry(
            dest, self.x, self.y, self.width, self.height)

        geom_old = self.geometry

        if geom_new != geom_old:
            if geom_old == None \
                    or (geom_new.width != geom_old.width
                        or geom_new.height != geom_old.height):
                self.console = tcod.console_new(geom_new.width, geom_new.height)
            self._geom = geom_new
            return True

        return False

    def refresh(self) -> bool:

        up = False
        for c in self.childs:
            # update childs geometry
            up = c.update_geometry(self) or up

            # update childs
            if isinstance(c, IUpdatable):
                if c.should_update:
                    c.update()
                    up = True

            # refresh childs
            up = c.refresh() or up

        # draw
        if up:
            self.console.clear()
            for c in self.childs:
                if c.visible:
                    c.draw(self)

        return up


class CanvasDispatcher:
    def __init__(self) -> None:
        self.ev_keydown = []
        self.ev_keyup = []
        self.ev_mousemotion = []
        self.ev_mousebuttondown = []
        self.ev_mousebuttonup = []
        self.ev_mousewheel = []
        self.ev_textinput = []
        self.ev_mousefocuslost = []
        self.ev_mousefocusgain = []

    def dispatch(self, event: tcod.event.Event) -> None:
        if event.type:
            event_list = getattr(self, f"ev_{event.type.lower()}")
            for ev in event_list:
                ev(event)


class Tooltip(Canvas, IUpdatable):
    def __init__(self, value: str = "", x: int = 0, y: int = 0,
                 fg_color: tcod.Color = tcod.white,
                 bg_color: tcod.Color = tcod.black,
                 fg_alpha: float = 1, bg_alpha: float = 0.7,
                 max_width: int = -1, max_height: int = -1,
                 delay:float = 0., fade_duration :float = 0.) -> None:
        super().__init__()
        self._value = value
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.fg_alpha = fg_alpha
        self.bg_alpha = bg_alpha
        self.max_width = max_width
        self.max_height = max_height
        self._delay = delay
        self._fade_duration = fade_duration
        self._last_time = 0

        self._should_update = False

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val) -> None:
        self._last_time = time.perf_counter()
        self._value = val

    @property
    def should_update(self) -> bool:
        return self._should_update

    @should_update.setter
    def should_update(self, value: bool) -> None:
        self._should_update = value

    def update_geometry(self, dest: Canvas) -> bool:
        up = super().update_geometry(dest)
        if up:
            self.should_update = True
        return up

    def update(self) -> None:
        if len(self.value) > 0:
            dt = time.perf_counter() - self._last_time
            if dt < self._delay:
                pass
            elif dt > (self._delay + self._fade_duration + 0.5) :
                self.should_update = False
            else :
                lines = []
                width = height = 0
                if self.max_width > 0:
                    lines = textwrap.wrap(self.value, self.max_width)
                    width = min(self.max_width, max(len(L) for L in lines))
                    lines = [" "*((width-len(e)-1)//2) +
                             e for e in lines]
                else:
                    lines = [self.value]
                    width = len(self.value)
                if self.max_height > 0:
                    lines = lines[:self.max_height]
                    height = min(self.max_height, len(lines))
                else:
                    height = len(lines)
                width += 2
                height += 2

                self.console = tcod.console_new(width, height)
                self.console.bg[:] = self.bg_color
                self.console.fg[:] = self.fg_color
                self.console.ch[[0, -1], :] = 196
                self.console.ch[:, [0, -1]] = 179
                self.console.ch[[[0, -1], [-1, 0]],
                                [0, -1]] = [[218, 217], [192, 191]]

                for i, e in enumerate(lines):
                    self.console.print_(1, i+1, e)

    def draw(self, dest: Canvas) -> None:
        if len(self.value) > 0:
            if self.x + self.console.width > dest.console.width:
                self.x = self.x - 1 - self.console.width

            dt = time.perf_counter() - self._last_time
            fade = 1
            if self._fade_duration > 0:
                fade = (dt - self._delay) / self._fade_duration
            if dt > self._delay:
                if fade > 1:
                    fade = 1
                self.console.blit(dest.console, self.x+1, self.y,
                                  fg_alpha=self.fg_alpha * fade,
                                  bg_alpha=self.bg_alpha * fade)


class MouseFocusChange:
    def __init__(self, event: tcod.event.MouseMotion, type_: str):
        if type_ not in ["MOUSEFOCUSGAIN", "MOUSEFOCUSLOST"]:
            raise ValueError("type_ must be MOUSEFOCUSGAIN or MOUSEFOCUSLOST")
        self.type = type_
        self.sdl_event = event.sdl_event
        self.pixel = event.pixel
        self.pixel_motion = event.pixel_motion
        self.tile = event.tile
        self.tile_motion = event.tile_motion
        self.state = event.state
