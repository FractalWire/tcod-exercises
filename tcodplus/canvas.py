import abc
from typing import Union, List, Dict, Callable, NamedTuple, Tuple
import tcod
import tcod.event
import time
import textwrap
from tcodplus import interfaces
from tcodplus import event as tcp_event


Geometry = NamedTuple('Geometry', [('abs_x', int), ('abs_y', int),
                                   ('x', int), ('y', int),
                                   ('width', int), ('height', int)])


def relative_geometry(dest: 'Canvas', rel_x: Union[int, float],
                      rel_y: Union[int, float], rel_width: Union[int, float],
                      rel_height: Union[int, float]) -> List[int]:
    if dest != None:
        if dest.geometry == None:
            return Geometry(0, 0, 0, 0, 0, 0)
        d_abs_x, d_abs_y, _, _, d_width, d_height = dest.geometry
        x = rel_x if isinstance(rel_x, int) else round(rel_x*d_width)
        y = rel_y if isinstance(rel_y, int) else round(rel_y*d_height)
        abs_x = d_abs_x + x
        abs_y = d_abs_y + y
        width = rel_width if isinstance(rel_width, int) \
            else round(rel_width*d_width)
        height = rel_height if isinstance(rel_height, int) \
            else round(rel_height*d_height)

        return Geometry(abs_x, abs_y, x, y, width, height)

    return Geometry(0, 0, 0, 0, rel_width, rel_height)


class Canvas(interfaces.IDrawable):
    def __init__(self, x: Union[int, float] = 0, y: Union[int, float] = 0,
                 width: Union[int, float] = 0, height: Union[int, float] = 0,
                 fg_alpha: float = 1, bg_alpha: float = 1,
                 bg_color: Tuple[int, int, int] = tcod.black,
                 fg_color: Tuple[int, int, int] = tcod.white,
                 key_color: Tuple[int, int, int] = None) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self._geom = None

        self.childs = list()
        self._focused_childs = tcp_event.MouseFocus([], [], [])

        self.console = None
        self.bg_color = tcod.Color(*bg_color)
        self.fg_color = tcod.Color(*fg_color)
        self.bg_alpha = bg_alpha
        self.fg_alpha = fg_alpha
        self.key_color = tcod.Color(*key_color) if key_color else None
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
                          self.fg_alpha, self.bg_alpha, self.key_color)

    def update_mouse_focused(self, event: tcod.event.MouseMotion) -> None:
        focusable_childs = [c for c in self.childs if isinstance(
            c, interfaces.IMouseFocusable)]
        focused = [c for c in focusable_childs if c.ismousefocused(event)]

        childs_focus_gain = [c for c in focused
                             if c not in self._focused_childs.focused]
        childs_focus_lost = [c for c in focusable_childs
                             if c in self._focused_childs.focused
                             and c not in focused]

        self._focused_childs = tcp_event.MouseFocus(focused,
                                                    childs_focus_lost,
                                                    childs_focus_gain)

        for c in self.childs:
            c.update_mouse_focused(event)

    def get_mouse_focused(self) -> None:
        focused, focus_lost, focus_gain = [list(elt)
                                           for elt in self._focused_childs]
        for c in self.childs:
            c_focused = c.get_mouse_focused()
            focused += c_focused.focused
            focus_lost += c_focused.focus_lost
            focus_gain += c_focused.focus_gain

        return tcp_event.MouseFocus(focused, focus_lost, focus_gain)

    def get_kbd_focusable(self) -> None:
        focusable_childs = [c for c in self.childs
                            if isinstance(c, interfaces.IKeyboardFocusable)]
        for c in self.childs:
            focusable_childs += c.get_kbd_focusable()
        return focusable_childs

    def init_console(self, width: int, height: int) -> tcod.console.Console:
        console = tcod.console.Console(width, height)
        console.clear(bg=self.bg_color, fg=self.fg_color)
        return console

    def update_geometry(self, dest: 'Canvas') -> bool:

        geom_new = relative_geometry(
            dest, self.x, self.y, self.width, self.height)

        geom_old = self.geometry

        if geom_new != geom_old:
            if geom_old == None \
                    or (geom_new.width != geom_old.width
                        or geom_new.height != geom_old.height):
                self.console = self.init_console(geom_new.width,
                                                 geom_new.height)
            self._geom = geom_new
            return True

        return False

    def refresh(self) -> bool:

        up = False

        # refresh childs
        for c in self.childs:
            up_geom = c.update_geometry(self)
            if isinstance(c, interfaces.IUpdatable):
                c.should_update = c.should_update or up_geom
            up = any([c.refresh(), up, up_geom])

        if up:
            self.console.clear(bg=self.bg_color, fg=self.fg_color)

        # update self if necessary
        if isinstance(self, interfaces.IUpdatable) \
                and (self.should_update or up):
            self.update()
            up = True

        # draw childs if necessary
        if up:
            for c in self.childs:
                if c.visible:
                    c.draw(self)

        return up


class RootCanvas(Canvas):
    def __init__(self, width: Union[int, float] = 0,
                 height: Union[int, float] = 0, title: str = "",
                 font: str = "",
                 flags: int = tcod.FONT_LAYOUT_TCOD | tcod.FONT_TYPE_GREYSCALE,
                 bg_color: tcod.color.Color = tcod.black,
                 fg_color: tcod.color.Color = tcod.white) -> None:
        super().__init__(width=width, height=height,
                         bg_color=bg_color, fg_color=fg_color)
        self._geom = Geometry(0, 0, 0, 0, width, height)

        tcod.console_set_custom_font(font, flags)
        self.console = tcod.console_init_root(width, height, title)
        self.console.bg_color = bg_color
        self.console.fg_color = fg_color
        self.console.clear()

        self.title = title
        self.mouse_focused_offspring = tcp_event.MouseFocus([], [], [])
        self.kbd_focused_offspring = None

    def update_mouse_focused(self, event: tcod.event.MouseMotion) -> None:
        if not event.state:
            super().update_mouse_focused(event)
            self.mouse_focused_offspring = self.get_mouse_focused()

    def update_kbd_focus(self) -> bool:
        focusable_childs = self.get_kbd_focusable()
        old_i, new_i = tcp_event.KeyboardFocusAdmin.update_focus(
            focusable_childs)
        if new_i != old_i:
            if old_i != -1:
                lost = self.kbd_focused_offspring
                ev_keyboardfocuslost = tcp_event.KeyboardFocusChange(
                    "KEYBOARDFOCUSLOST")
                lost.focus_dispatcher.dispatch(ev_keyboardfocuslost)
            if new_i != -1:
                gain = focusable_childs[new_i]
                ev_keyboardfocusgain = tcp_event.KeyboardFocusChange(
                    "KEYBOARDFOCUSGAIN")
                gain.focus_dispatcher.dispatch(ev_keyboardfocusgain)
                self.kbd_focused_offspring = gain
            return True
        return False

    def cycle_fwd_kbd_focus(self) -> bool:
        focusable_childs = self.get_kbd_focusable()
        next_ind = tcp_event.KeyboardFocusAdmin.next(focusable_childs)
        has_changed = self.update_kbd_focus()
        return has_changed

    def cycle_bkwd_kbd_focus(self) -> bool:
        focusable_childs = self.get_kbd_focusable()
        prev_ind = tcp_event.KeyboardFocusAdmin.previous(focusable_childs)
        has_changed = self.update_kbd_focus()
        return has_changed

    def handle_focus_event(self, event: tcod.event.Event) -> None:
        kbd_focus_changed = False
        if event.type == "MOUSEMOTION" and not event.state:
            self.update_mouse_focused(event)
        elif event.type == "KEYDOWN":
            if event.sym == tcod.event.K_TAB:
                kbd_focus_changed = self.cycle_bkwd_kbd_focus() \
                    if event.mod & tcod.event.KMOD_SHIFT \
                    else self.cycle_fwd_kbd_focus()

        if event.type == "MOUSEMOTION":
            ev_mousefocuslost = tcp_event.MouseFocusChange(
                event, "MOUSEFOCUSLOST")
            for c in self.mouse_focused_offspring.focus_lost:
                c.focus_dispatcher.dispatch(ev_mousefocuslost)
            ev_mousefocusgain = tcp_event.MouseFocusChange(
                event, "MOUSEFOCUSGAIN")
            for c in self.mouse_focused_offspring.focus_gain:
                c.focus_dispatcher.dispatch(ev_mousefocusgain)

        if event.type in ("MOUSEMOTION", "MOUSEBUTTONDOWN",
                          "MOUSEBUTTONUP", "MOUSEWHEEL"):
            for c in self.mouse_focused_offspring.focused:
                if c not in self.mouse_focused_offspring.focus_gain :
                    c.focus_dispatcher.dispatch(event)

            self.update_kbd_focus()
        elif event.type in ("KEYDOWN", "KEYUP", "TEXTINPUT") \
                and not kbd_focused_offspring:
            k_focused_offspring = self.kbd_focused_offspring
            if k_focused_offspring != None:
                k_focused_offspring.focus_dispatcher.dispatch(event)
