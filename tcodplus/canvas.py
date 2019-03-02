from __future__ import annotations
from collections.abc import Mapping
from typing import List, NamedTuple, Tuple, Optional, Union
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
                                   ('width', int), ('height', int),
                                   ('content_width', int), ('content_height', int)])


class CanvasChilds(dict):
    """CanvasChilds is a specialized dictionary for storing Canvas' childs

    Adding or removing a child will update the child 'parent' attribute
    accordingly

    Common dictionary operations are supported.

    To add childs, you should typically use the add() method.

    Args:
        canvas : the canvas in which it is used
    """

    def __init__(self, canvas: Canvas, other=None, **kwargs) -> None:
        super().__init__()
        self.canvas = canvas
        self.update(other, **kwargs)

    def __setitem__(self, k: str, v: Canvas) -> None:
        if k != v.name:
            raise KeyError(f"The key must be the name of the new child. Given:"
                           f"{k}, expected: {v.name}")
        if v.name in self:
            raise KeyError(f"A Canvas with name {v.name} already exist."
                           f" Canvas must have unique name")
        super().__setitem__(k, v)
        if v.parent != self.canvas:
            v.parent = self.canvas

    def __delitem__(self, k: str) -> None:
        v = self[k]
        super().__delitem__(k)
        if v.parent == self.canvas:
            v.parent = None

    def update(self, other=None, **kwargs) -> None:
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def copy(self) -> CanvasChilds:
        return type(self)(self.canvas, self)

    def clear(self) -> None:
        while len(self) > 0:
            k, v = self.popitem()
            v.parent = None

    def add(self, *childs: Canvas) -> None:
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
                 style: Union[dict, tcp_style.Style] = dict()) -> None:
        self.name = name or _genCanvasID()
        self._geom: Geometry = Geometry(0, 0, 0, 0, 0, 0, 0, 0)

        self._parent = None
        self.childs: CanvasChilds[str, Canvas] = CanvasChilds(self)
        self._focused_childs = tcp_event.MouseFocus({}, {}, {})

        self._style = None
        self.style = style
        self.console = self.init_console()

        self._force_redraw = False

    @property
    def force_redraw(self) -> bool:
        return self._force_redraw

    @force_redraw.setter
    def force_redraw(self, value: bool) -> None:
        self._force_redraw = value

    @property
    def geometry(self) -> Geometry:
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
    def parent(self) -> Canvas:
        return self._parent

    @parent.setter
    def parent(self, value) -> None:
        # !!! Order is important, don't touch !!!
        old_parent = self._parent
        self._parent = value

        if value != old_parent:
            if old_parent is not None and self.name in old_parent.childs:
                del old_parent.childs[self.name]
            if value is not None and self.name not in value.childs:
                value.childs[self.name] = self

    @property
    def focused_childs(self) -> tcp_event.MouseFocus:
        """The mouse focused childs."""
        return self._focused_childs

    @property
    def style(self) -> tcp_style.Style:
        return self._style

    @style.setter
    def style(self, value: Union[tcp_style.Style, Mapping]) -> None:
        self._style = value if isinstance(value, tcp_style.Style) \
            else tcp_style.Style(value)
        self.force_redraw = True

    def styles(self) -> tcp_style.Style:
        return self.style

    def base_drawing(self) -> None:
        """Draw the base elements of the Canvas.

        It happens in the refresh() method before any child is drawed to the
        Canvas.

        This method should be overrode if needed. The default behaviour is to
        clear, with the color defined in style, the underlying Console of the
        Canvas.
        """
        style = self.styles()
        self.console.clear(bg=style.bg_color, fg=style.fg_color)

    def draw(self) -> None:
        """draw the Canvas to the parent Canvas"""

        style = self.styles()

        con = None
        if style.border != tcp_style.Border.NONE:
            con = tcod.console.Console(*self.geometry[4:6])
            tcp_style.draw_border(con, style)
            self.console.blit(con, 1, 1)
        else:
            con = self.console

        x, y, width, height = self.geometry[2:6]

        # TODO: improve tcp_style.Outbound.PARTIAL here so that it blit on both
        # sides if on the edge
        con.blit(self.parent.console, x, y, 0, 0, width, height,
                 style.fg_alpha, style.bg_alpha, style.key_color)

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
            style = c.styles()
            if style.display == tcp_style.Display.NONE:
                continue

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
            style = c.styles()
            if style.display == tcp_style.Display.NONE:
                continue
            focusable_childs += c.kbd_focusable_offsprings()
        return focusable_childs

    def init_console(self, width: Optional[int] = None,
                     height: Optional[int] = None) -> tcod.console.Console:
        """Init the Console Canvas based on content_width and content_height

        Note: It's a bit useless right now

        Returns:
            Console : the newly created Console
        """
        width = width or self.geometry.content_width
        height = height or self.geometry.content_height
        console = tcod.console.Console(width, height)
        return console

    def update_geometry(self) -> bool:
        """Update the geometry of the Canvas based on the parent Canvas

        Returns:
            bool : True if the Canvas geometry, excluding abs_x/abs_y, changed.
            Otherwise False
        """
        def relative_geometry() -> Geometry:
            def autointfloat(val: Union[str, int, float], rel: int,
                             auto_ret: int) -> int:
                if val == "auto":
                    return auto_ret
                elif isinstance(val, int):
                    return val
                elif isinstance(val, float):
                    return round(val*rel)

            if self.parent is not None:
                p_abs_x, p_abs_y, _, _, _, _, p_c_width, p_c_height = self.parent.geometry
                p_style = self.parent.styles()
                p_padding = 0
                p_has_border = p_style.border != tcp_style.Border.NONE

                # TODO: padding support here
                style = self.styles()
                padding = 0
                has_border = style.border != tcp_style.Border.NONE

                width = autointfloat(style.width, p_c_width,
                                     self.console.width + 2*(has_border+padding))
                height = autointfloat(style.height, p_c_height,
                                      self.console.height + 2*(has_border+padding))

                min_width = style.min_width or 0  # <=> value or None or 0
                max_width = style.max_width or width
                min_height = style.min_height or 0
                max_height = style.max_height or height

                width = sorted([min_width, width, max_width])[1]
                height = sorted([min_height, height, max_height])[1]

                # 0 is for future use here
                x = autointfloat(style.x, p_c_width, 0)
                y = autointfloat(style.y, p_c_height, 0)

                x, y = tcp_style.origin_coords(x, y, p_c_width, p_c_height,
                                               width, height,
                                               style.origin)
                x, y = tcp_style.bounded_coords(x, y, p_c_width, p_c_height,
                                                width, height,
                                                style.outbound)

                abs_x = p_abs_x + p_padding + p_has_border + x
                abs_y = p_abs_y + p_padding + p_has_border + y
                content_width = max(0, width - 2*(has_border + padding))
                content_height = max(0, height - 2*(has_border + padding))

                return Geometry(abs_x, abs_y, x, y, width, height,
                                content_width, content_height)

            return self.geometry

        geom_new = relative_geometry()

        geom_old = self.geometry

        self._geom = geom_new

        if geom_new[2:] != geom_old[2:]:
            if geom_new[6:] != (self.console.width, self.console.height):
                self.console = self.init_console()
                # TODO: blit old console here ?
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

            c_style = c.styles()
            up_geom = c.update_geometry()
            up_redraw = c.force_redraw
            up_style = c_style.is_modified
            up_current_child = any([up_geom, up_redraw, up_style])
            c.force_redraw = False
            c_style._is_modified = False
            if isinstance(c, IUpdatable):
                c.should_update = c.should_update or up_current_child

            up = any([c.refresh(), up, up_current_child])

        if up:
            self.base_drawing()

        # update self if necessary
        if isinstance(self, IUpdatable) and (self.should_update or up):
            if not up:
                self.base_drawing()
            self.update()
            up = True

        # draw childs if necessary
        if up:
            for c in self.childs.values():
                c_style = c.styles()
                if c_style.visible and c_style.display != tcp_style.Display.NONE:
                    c.draw()

        return up

    def __repr__(self) -> str:
        return f"{type(self).__name__} with name '{self.name}' at {hex(id(self))}"

    def __str__(self) -> str:
        return (f"{repr(self)}:\n"
                f"\tparent: {repr(self.parent)}\n"
                f"\tstyle: {self.style}\n"
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
        self._geom = Geometry(0, 0, 0, 0, width, height, width, height)

        tcod.console_set_custom_font(font, flags)
        self.console = tcod.console_init_root(width, height, title, fullscreen,
                                              renderer)
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
