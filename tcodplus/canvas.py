from __future__ import annotations
from collections.abc import Mapping
from typing import List, NamedTuple, Tuple, Optional
import tcod
import tcod.event
import tcodplus.style as tcp_style
from tcodplus import event as tcp_event
from tcodplus.interfaces import IDrawable, IUpdatable, IKeyboardFocusable, IMouseFocusable

_canvasID = 0


def _genCanvasID() -> str:
    global _canvasID
    _canvasID += 1
    return f"_can{_canvasID:06x}"


Geometry = NamedTuple('Geometry', [('abs_x', int), ('abs_y', int),
                                   ('x', int), ('y', int),
                                   ('width', int), ('height', int)])


class CanvasChilds(dict):
    """CanvasChilds is a specialized dictionary for storing Canvas' childs

    Adding or removing a child will update the child 'parent' attribute
    accordingly

    Common dictionary operations are supported.

    To add childs, you should typically use the add() method.

    Args:
        canvas : the canvas in which it is used
    """

    def __init__(self, canvas: Canvas, other=None, **kwargs):
        super().__init__()
        self.canvas = canvas
        self.update(other, **kwargs)

    def __setitem__(self, k: str, v: Canvas):
        if k != v.name:
            raise KeyError(f"The key must be the name of the new child. Given:"
                           f"{k}, expected: {v.name}")
        if v.name in self:
            raise KeyError(f"A Canvas with name {v.name} already exist."
                           f" Canvas must have unique name")
        super().__setitem__(k, v)
        if v.parent != self.canvas:
            v.parent = self.canvas

    def __delitem__(self, k: str):
        v = self[k]
        super().__delitem__(k)
        if v.parent == self.canvas:
            v.parent = None

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def copy(self):
        return type(self)(self.canvas, self)

    def clear(self):
        while len(self) > 0:
            k, v = self.popitem()
            v.parent = None

    def add(self, *childs: Canvas):
        for c in childs:
            self[c.name] = c

    def pop(self, key: str) -> Canvas:
        v = super().pop(key)
        v.parent = None
        return v

    def popitem(self) -> Canvas:
        kv = super().popitem()
        kv[1].parent = None
        return kv


class Canvas(IDrawable):
    """A Canvas is a tree-like structure that is able to yield a tcod.Console.

    The Console is drawn in respect to its childs.

    A Canvas is responsible to :
        * update geometry of its child
        * check if any child need to be updated
        * update child if needed.
        * obtain the focus status on its child.
        * draw itself on other Canvas when asked

    Args:
        name: str: A name for the canvas. Must be a unique name. If not set, the
            name will be automatically picked
        geometry: Geometry: The tiled base geometry of the Canvas, relative to
            its parent. It is read-only. If you want to modify this geometry,
            use the style properties (x, y, width, height)
        parent : Canvas: the parent of the Canvas
        childs: CanvasChilds[str, Canvas]: the childs of the Canvas. The key is the name
            of the child. Use add() to add any number of child.
        console: tcod.Console: the internal Console of the Canvas where
            everything is drawn.
        style: style.Style: the style for the Canvas.
    """

    def __init__(self, name: str = "", parent: Canvas = None,
                 style: tcp_style.Style = None):
        self.name = name or _genCanvasID()
        self._geom: Geometry = Geometry(0, 0, 0, 0, 0, 0)

        self._parent = None
        self.childs: CanvasChilds[str, Canvas] = CanvasChilds(self)
        self._focused_childs = tcp_event.MouseFocus({}, {}, {})

        self.style = style or tcp_style.Style()
        self.console = self.init_console()

        self._should_redraw = False

    @property
    def should_redraw(self):
        redraw = self._should_redraw
        self._should_redraw = False
        return redraw

    @should_redraw.setter
    def should_redraw(self, value: bool):
        self._should_redraw = value

    @property
    def geometry(self):
        """The tiled base geometry of the Canvas, relative to his parent

        This is a named tuple with 6 values :
            abs_x : int : the absolute x of the Canvas related to the root
                Canvas
            abs_y : int : the absolute y of the Canvas related to the root
                Canvas
            x : int : the relative x of the Canvas related to his parent
            y : int : the relative y of the Canvas related to his parent
            width : int : the relative width of the Canvas related to his parent
            height : int : the relative height of the Canvas related to his
                parent
        """
        return self._geom

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        # !!! Order is important, don't touch !!!
        old_parent = self._parent
        self._parent = value

        if value != old_parent:
            if old_parent is not None and self.name in old_parent.childs:
                del old_parent.childs[self.name]
            if value is not None and self.name not in value.childs:
                value.childs[self.name] = self

    # def add_childs(self, *childs: Canvas) -> None:
    #     for c in childs:
    #         if c.name in self.childs:
    #             raise ValueError(f"A canvas with name {c.name} already exist in"
    #                              f" 'childs' dictionary of canvas {self.name}."
    #                              f" Canvas must have unique name")
    #         self.childs[c.name] = c

    @property
    def focused_childs(self):
        """The mouse focused childs."""
        return self._focused_childs

    def draw(self) -> None:
        """draw the Canvas to the parent Canvas"""

        # This might need to be outsourced to update_geometry
        # Maybe add some kind of content-size attribute...
        # think about it
        if self.style.border:
            tcp_style.draw_border(self.console, self.style)

        x, y, width, height = self.geometry[2:]
        x_max, y_max = self.parent.geometry[4:]
        x, y = tcp_style.transform_coords(x, y, x_max, y_max, width, height,
                                          self.style.origin, self.style.outbound)

        self.console.blit(self.parent.console, x, y, 0, 0, width, height,
                          self.style.fg_alpha, self.style.bg_alpha,
                          self.style.key_color)

    def _update_mouse_focus(self, event: tcod.event.MouseMotion) -> None:
        """update the status of IMouseFocusable childs in _focused_childs

        Args:
          event: tcod.event.MouseMotion: an event to consider when updating
              focus
        """
        focusable_childs = {k: v for k, v in self.childs.items()
                            if isinstance(v, IMouseFocusable)}
        focused = {k: v for k, v in focusable_childs.items()
                   if v.mousefocus(event)}

        childs_focus_gain = {k: v for k, v in focused.items()
                             if k not in self._focused_childs.focused}
        childs_focus_lost = {k: v for k, v in focusable_childs.items()
                             if k in self._focused_childs.focused
                             and k not in focused}

        self._focused_childs = tcp_event.MouseFocus(focused,
                                                    childs_focus_lost,
                                                    childs_focus_gain)

        for c in self.childs.values():
            c._update_mouse_focus(event)

    def mouse_focused_offsprings(self) -> tcp_event.MouseFocus:
        """get the mouse focused offsprings of the Canvas.

        Returns :
            MouseFocus : the currently focused, lost focused, new focused
                Canvas.
                MouseFocus is a named tuple  with 3 value :
                    focus : Dict[str, Canvas] : the currently focused Canvas
                    focus_lost : Dict[str, Canvas] : Canvas that lost focus
                    focus_gain : Dict[str, Canvas] : Canvas that gained focus
        """
        nfc = tcp_event.MouseFocus(*[dict(elt) for elt in self._focused_childs])

        for c in self.childs.values():
            cfc = c.mouse_focused_offsprings()
            nfc.focused.update(cfc.focused)
            nfc.focus_lost.update(cfc.focus_lost)
            nfc.focus_gain.update(cfc.focus_gain)

        return nfc

    def kbd_focusable_offsprings(self) -> List[IKeyboardFocusable]:
        """get the keyboard focusable offsprings of the Canvas

        Returns :
            Dict[str, Canvas] : the focusable offsprings
        """
        focusable_childs = [v for v in self.childs.values()
                            if isinstance(v, IKeyboardFocusable)]
        for c in self.childs.values():
            focusable_childs += c.kbd_focusable_offsprings()
        return focusable_childs

    def init_console(self) -> tcod.console.Console:
        """Init the Console Canvas based on width and height

        Returns:
            Console : the newly created Console
        """
        console = tcod.console.Console(self.geometry.width,
                                       self.geometry.height)
        console.clear(bg=self.style.bg_color, fg=self.style.fg_color)
        return console

    def update_geometry(self) -> bool:
        """Update the geometry of the Canvas based on the parent Canvas

        Returns:
            bool : True if the Canvas geometry, excluding abs_x/abs_y, changed.
            Otherwise False
        """
        def relative_geometry() -> Geometry:
            if self.parent is not None:
                p_abs_x, p_abs_y, _, _, p_width, p_height = self.parent.geometry
                x = self.style.x if isinstance(self.style.x, int) \
                    else round(self.style.x*p_width)
                y = self.style.y if isinstance(self.style.y, int) \
                    else round(self.style.y*p_height)
                abs_x = p_abs_x + x
                abs_y = p_abs_y + y
                width = self.style.width if isinstance(self.style.width, int) \
                    else round(self.style.width*p_width)
                height = self.style.height if isinstance(self.style.height, int) \
                    else round(self.style.height*p_height)

                min_width = 0 if self.style.min_width is None \
                    else self.style.min_width
                max_width = width if self.style.max_width is None \
                    else self.style.max_width
                min_height = 0 if self.style.min_height is None \
                    else self.style.min_height
                max_height = height if self.style.max_height is None \
                    else self.style.max_height

                width = sorted([min_width, width, max_width])[1]
                height = sorted([min_height, height, max_height])[1]

                return Geometry(abs_x, abs_y, x, y, width, height)

            return Geometry(0, 0, 0, 0, 0, 0)

        geom_new = relative_geometry()

        geom_old = self.geometry

        self._geom = geom_new

        if geom_new[2:] != geom_old[2:]:
            if geom_new.width != geom_old.width or geom_new.height != geom_old.height:
                self.console = self.init_console()
            return True

        return False

    def refresh(self) -> bool:
        """refresh the Canvas and its childs if needed.

        Returns :
            bool : True if the Canvas had to refresh itself otherwise False
        """

        up = False

        # refresh childs
        for c in self.childs.values():
            # c._update_mouse_focus()
            up_geom = c.update_geometry()
            if isinstance(c, IUpdatable):
                c.should_update = c.should_update or up_geom
            up = any([c.refresh(), c.should_redraw, up, up_geom])

        if up:
            self.console.clear(bg=self.style.bg_color, fg=self.style.fg_color)

        # update self if necessary
        if isinstance(self, IUpdatable) \
                and (self.should_update or up):
            self.update()
            up = True

        # draw childs if necessary
        if up:
            for c in self.childs.values():
                if c.style.visible:
                    c.draw()

        return up

    def __repr__(self) -> str:
        return f"{type(self).__name__} with name '{self.name}' at {hex(id(self))}"

    def __str__(self) -> str:
        return (f"{repr(self)}:\n"
                f"\tparent: {repr(self.parent)}\n"
                f"\tstyle: {self.style})\n"
                f"\tchilds: {self.childs}")


class RootCanvas(Canvas):
    """The RootCanvas. A Canvas to rule them all.

    The Console of the RootCanvas is the root Console of tcod.

    Args :
        width : int : the width of the Canvas, in tile
        height : int : the height of the Canvas, in tile
        title : str : the title of the Window
        font : str : the font to use
        flags : int : tcod specific flags for the font

    """

    def __init__(self, width: int, height: int,
                 title: str = "", font: str = "",
                 flags: int = tcod.FONT_LAYOUT_TCOD | tcod.FONT_TYPE_GREYSCALE,
                 fullscreen: bool = False, renderer: Optional[int] = None,
                 bg_color: Tuple[int, int, int] = tcod.black,
                 fg_color: Tuple[int, int, int] = tcod.white) -> None:
        style = tcp_style.Style(width=width, height=height,
                                bg_color=bg_color, fg_color=fg_color)
        super().__init__(style=style)
        self._geom = Geometry(0, 0, 0, 0, width, height)

        tcod.console_set_custom_font(font, flags)
        self.console = tcod.console_init_root(width, height, title)
        self.console.clear(bg=bg_color, fg=fg_color)

        self.title = title
        self.last_mouse_focused_offsprings = tcp_event.MouseFocus({}, {}, {})
        self.last_kbd_focused_offspring: Canvas = None

    def update_last_mouse_focused_offsprings(self, event: tcod.event.MouseMotion) -> None:
        """update the focus of the IMouseFocusable childs and update
            last_mouse_focused_offsprings

        Args:
          event: tcod.event.MouseMotion: an event to consider when updating
              focus
        """
        if not event.state:
            self._update_mouse_focus(event)
            self.last_mouse_focused_offsprings = self.mouse_focused_offsprings()

    def update_kbd_focus(self) -> bool:
        """update keyboard focus self.kbd_focused_offspring

        Returns :
            bool : True if the focus has changed, otherwise False
        """
        focusable_childs = self.kbd_focusable_offsprings()
        old_i, new_i = tcp_event.KeyboardFocusAdmin.update_focus(
            focusable_childs)
        if new_i != old_i:
            if old_i != -1:
                last = self.last_kbd_focused_offspring
                ev_keyboardfocuslost = tcp_event.KeyboardFocusChange(
                    "KEYBOARDFOCUSLOST")
                last.focus_dispatcher.dispatch(ev_keyboardfocuslost)
            if new_i != -1:
                gain = focusable_childs[new_i]
                ev_keyboardfocusgain = tcp_event.KeyboardFocusChange(
                    "KEYBOARDFOCUSGAIN")
                gain.focus_dispatcher.dispatch(ev_keyboardfocusgain)
                self.last_kbd_focused_offspring = gain
            return True
        return False

    def cycle_fwd_kbd_focus(self) -> bool:
        """cycle keyboard focus forward and update self.kbd_focused_offspring

        Returns :
            bool : True if the focus has changed, otherwise False
        """
        focusable_childs = self.kbd_focusable_offsprings()
        _ = tcp_event.KeyboardFocusAdmin.next(focusable_childs)
        has_changed = self.update_kbd_focus()
        return has_changed

    def cycle_bkwd_kbd_focus(self) -> bool:
        """cycle keyboard focus backward and update self.kbd_focused_offspring

        Returns :
            bool : True if the focus has changed, otherwise False
        """
        focusable_childs = self.kbd_focusable_offsprings()
        _ = tcp_event.KeyboardFocusAdmin.previous(focusable_childs)
        has_changed = self.update_kbd_focus()
        return has_changed

    def handle_focus_event(self, event: tcod.event.Event) -> None:
        """General purpose event handler. It update focus and fire focused
            events

        Args:
          event: tcod.event.Event: the current event
        """

        # Update keyboard and mouse focus
        if event.type == "MOUSEMOTION" and not event.state:
            self.update_last_mouse_focused_offsprings(event)
        elif event.type == "KEYDOWN":
            if event.sym == tcod.event.K_TAB:
                _ = self.cycle_bkwd_kbd_focus() \
                    if event.mod & tcod.event.KMOD_SHIFT \
                    else self.cycle_fwd_kbd_focus()

        # fire mouse focus change events
        if event.type == "MOUSEMOTION":
            ev_mousefocuslost = tcp_event.MouseFocusChange(event,
                                                           "MOUSEFOCUSLOST")
            for c in self.last_mouse_focused_offsprings.focus_lost.values():
                c.focus_dispatcher.dispatch(ev_mousefocuslost)
            ev_mousefocusgain = tcp_event.MouseFocusChange(event,
                                                           "MOUSEFOCUSGAIN")
            for c in self.last_mouse_focused_offsprings.focus_gain.values():
                c.focus_dispatcher.dispatch(ev_mousefocusgain)

        # /!\ Keyboard focus changes should be handled too

        # fire event for focused Canvas only
        if event.type in ("MOUSEMOTION", "MOUSEBUTTONDOWN",
                          "MOUSEBUTTONUP", "MOUSEWHEEL"):
            for k, c in self.last_mouse_focused_offsprings.focused.items():
                if k not in self.last_mouse_focused_offsprings.focus_gain:
                    c.focus_dispatcher.dispatch(event)
            self.update_kbd_focus()
        elif event.type in ("KEYDOWN", "KEYUP", "TEXTINPUT") \
                and self.last_kbd_focused_offspring is not None:
            k_focused_offspring = self.last_kbd_focused_offspring
            if k_focused_offspring is not None:
                k_focused_offspring.focus_dispatcher.dispatch(event)
