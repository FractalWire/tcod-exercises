from __future__ import annotations
from typing import Union, List, NamedTuple, Tuple, Dict
import tcod
import tcod.event
from tcodplus import event as tcp_event
from tcodplus.interfaces import IDrawable, IUpdatable, IKeyboardFocusable, IMouseFocusable

_canvasID = 0


def _genCanvasID():
    global _canvasID
    _canvasID += 1
    return f"_can{_canvasID:06x}"


Geometry = NamedTuple('Geometry', [('abs_x', int), ('abs_y', int),
                                   ('x', int), ('y', int),
                                   ('width', int), ('height', int)])


def relative_geometry(dest: Canvas, rel_x: Union[int, float],
                      rel_y: Union[int, float], rel_width: Union[int, float],
                      rel_height: Union[int, float]) -> List[int]:
    """Calculate the relative geometry to a dest Canvas.

    Args:
      dest: Canvas: the Canvas to compare to
      rel_x: Union[int, float]: either the relative x value in tile or in percent
      rel_y: Union[int, float]: either the relative y value in tile or in percent
      rel_width: Union[int, float]: either the relative width value in tile or in percent
      rel_height: Union[int, float]: either the relative height value in tile or in percent

    Returns:
        List[int] : the relative dimension to the dest canvas, in tile
    """
    if dest is not None:
        if dest.geometry is None:
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


class Canvas(IDrawable):
    """A Canvas is a tree-like structure that is able to yield a tcod.Console.

    The Console is drawn in respect to its childs.

    A Canvas is responsible to :
        * update geometry of its child
        * check if any child need to be updated
        * update child if needed.
        * obtain the focus status on its child.

    Args:
        x : Union[int,float]: the relative x position of a Canvas in respect to
            his hypotetical parent
        y : Union[int,float]: the relative y position of a Canvas in respect to
            his hypotetical parent
        width : Union[int,float]: the relative width of a Canvas in respect to
            his hypotetical parent
        height : Union[int,float]: the relative height of a Canvas in respect
            to his hypotetical parent
        bg_alpha : float : the alpha value for the background
        fg_alpha : float : the alpha value for the foreground
        bg_color : Tuple[int,int,int] : the color for the background in RGB
            format
        fg_color : Tuple[int,int,int] : the color for the foreground in RGB
            format
        key_color : Tuple[int,int,int] : a color to set as transparent. If None,
            no transparent color  will be set
    """

    def __init__(self, x: Union[int, float] = 0, y: Union[int, float] = 0,
                 width: Union[int, float] = 0, height: Union[int, float] = 0,
                 bg_alpha: float = 1, fg_alpha: float = 1,
                 bg_color: Tuple[int, int, int] = tcod.black,
                 fg_color: Tuple[int, int, int] = tcod.white,
                 key_color: Tuple[int, int, int] = None,
                 name: str = "") -> None:
        self.name: str = name or _genCanvasID()
        self.x: Union[int, float] = x
        self.y: Union[int, float] = y
        self.width: Union[int, float] = width
        self.height: Union[int, float] = height
        self._geom: Geometry = None

        self.childs: Dict[str, Canvas] = dict()
        self._focused_childs: tcp_event.MouseFocus = tcp_event.MouseFocus([], [
        ], [])

        self.console: tcod.console.Console = None
        self.bg_color: tcod.Color = tcod.Color(*bg_color)
        self.fg_color: tcod.Color = tcod.Color(*fg_color)
        self.bg_alpha: float = bg_alpha
        self.fg_alpha: float = fg_alpha
        self.key_color: tcod.Color = tcod.Color(
            *key_color) if key_color else None
        self.visible: bool = True

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

    def add_childs(self, *childs: Canvas) -> None:
        for c in childs:
            if c.name in self.childs:
                raise ValueError(f"A canvas with name {c.name} already exist in"
                                 f" 'childs' dictionary of canvas {self.name}."
                                 f" Canvas must have unique name")
            self.childs[c.name] = c

    @property
    def focused_childs(self):
        """The mouse focused childs."""
        return self._focused_childs

    def draw(self, dest: 'Canvas') -> None:
        """draw the Canvas to the dest Canvas

        Args:
          dest: 'Canvas': the canvas to draw to
        """
        x, y, width, height = self.geometry[2:]
        self.console.blit(dest.console, x, y, 0, 0, width, height,
                          self.fg_alpha, self.bg_alpha, self.key_color)

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

    def kbd_focusable_offsprings(self) -> List[Canvas]:
        """get the keyboard focusable offsprings of the Canvas

        Returns :
            Dict[str, Canvas] : the focusable offsprings
        """
        focusable_childs = [v for v in self.childs.values()
                            if isinstance(v, IKeyboardFocusable)]
        for c in self.childs.values():
            focusable_childs += c.kbd_focusable_offsprings()
        return focusable_childs

    def init_console(self, width: int, height: int) -> tcod.console.Console:
        """Init the Console Canvas based on width and height

        Args:
          width: int: the width of the Console
          height: int: the height of the Console

        Returns:
            Console : the newly created Console
        """
        console = tcod.console.Console(width, height)
        console.clear(bg=self.bg_color, fg=self.fg_color)
        return console

    def update_geometry(self, dest: 'Canvas') -> bool:
        """Update the geometry of the Canvas based on a dest Canvas

        Args:
          dest: 'Canvas': the parent Canvas

        Returns:
            bool : True if the Canvas was updated otherwise False
        """

        geom_new = relative_geometry(
            dest, self.x, self.y, self.width, self.height)

        geom_old = self.geometry

        if geom_new != geom_old:
            if geom_old is None \
                    or (geom_new.width != geom_old.width
                        or geom_new.height != geom_old.height):
                self.console = self.init_console(geom_new.width,
                                                 geom_new.height)
            self._geom = geom_new
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
            up_geom = c.update_geometry(self)
            if isinstance(c, IUpdatable):
                c.should_update = c.should_update or up_geom
            up = any([c.refresh(), up, up_geom])

        if up:
            self.console.clear(bg=self.bg_color, fg=self.fg_color)

        # update self if necessary
        if isinstance(self, IUpdatable) \
                and (self.should_update or up):
            self.update()
            up = True

        # draw childs if necessary
        if up:
            for c in self.childs.values():
                if c.visible:
                    c.draw(self)

        return up


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
                 bg_color: Tuple[int, int, int] = tcod.black,
                 fg_color: Tuple[int, int, int] = tcod.white) -> None:
        super().__init__(width=width, height=height,
                         bg_color=bg_color, fg_color=fg_color)
        self._geom = Geometry(0, 0, 0, 0, width, height)

        tcod.console_set_custom_font(font, flags)
        self.console = tcod.console_init_root(width, height, title)
        self.console.bg_color = self.bg_color
        self.console.fg_color = self.fg_color
        self.console.clear()

        self.title = title
        self.last_mouse_focused_offsprings = tcp_event.MouseFocus([], [], [])
        self.last_kbd_focused_offspring = None

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
        old_i, new_i = tcp_event.KeyboardFocusAdmin.update_focus(focusable_childs)
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
