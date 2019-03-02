from __future__ import annotations
from typing import List, NamedTuple, Tuple, Dict, Callable, TYPE_CHECKING
import tcod.event

if TYPE_CHECKING:
    # from tcodplus.canvas import Canvas
    from tcodplus.interfaces import IKeyboardFocusable


MouseFocus = NamedTuple('MouseFocus',
                        [('focused', Dict[str, 'Canvas']),
                         ('focus_lost', Dict[str, 'Canvas']),
                         ('focus_gain', Dict[str, 'Canvas'])])


class KeyboardFocusAdmin:
    # This class assume at any time there is only one focused element and one
    # requesting focused element, which might not be true...
    @classmethod
    def update_focus(cls, focusable: List[IKeyboardFocusable]) -> Tuple[int, int]:
        i_req = cls.focus_requested_index(focusable)
        if i_req != -1:
            i_foc = cls.focus_index(focusable)
            if i_req != i_foc:
                focusable[i_req].kbdfocus = True
                if i_foc is not None:
                    focusable[i_foc].kbdfocus = False
            else:
                focusable[i_req].kbdfocus_requested = False
            return i_foc, i_req
        return (-1, -1)

    @staticmethod
    def focus_requested_index(focusable: List[IKeyboardFocusable]) -> int:
        for i, kf in enumerate(focusable):
            if kf.kbdfocus_requested:
                return i
        return -1

    @staticmethod
    def focus_index(focusable: List[IKeyboardFocusable]) -> int:
        for i, kf in enumerate(focusable):
            if kf.kbdfocus:
                return i
        return -1

    @classmethod
    def next(cls, focusable: List[IKeyboardFocusable]) -> int:
        if focusable:
            i = cls.focus_index(focusable)
            next_i = (i+1) % len(focusable)
            focusable[next_i].kbdfocus_requested = True
            return next_i
        return -1

    @classmethod
    def previous(cls, focusable: List[IKeyboardFocusable]) -> int:
        if focusable:
            i = cls.focus_index(focusable)
            if i == -1:
                i = 0
            prev_i = (i-1) % len(focusable)
            focusable[prev_i].kbdfocus_requested = True
            return prev_i
        return -1


class CanvasDispatcher:
    def __init__(self) -> None:
        event_funs = List[Callable[[tcod.event.Event], None]]
        self.ev_keydown: event_funs = []
        self.ev_keyup: event_funs = []
        self.ev_mousemotion: event_funs = []
        self.ev_mousebuttondown: event_funs = []
        self.ev_mousebuttonup: event_funs = []
        self.ev_mousewheel: event_funs = []
        self.ev_textinput: event_funs = []
        self.ev_mousefocuslost: event_funs = []
        self.ev_mousefocusgain: event_funs = []
        self.ev_keyboardfocuslost: event_funs = []
        self.ev_keyboardfocusgain: event_funs = []

    def dispatch(self, event: tcod.event.Event) -> None:
        if event.type:
            event_list = getattr(self, f"ev_{event.type.lower()}")
            for ev in event_list:
                ev(event)

    def add_events(self, event_funs: List[Callable[[tcod.event.Event], None]],
                   event_types: List[str]) -> None:
        for type_ in event_types:
            event_list = getattr(self, f"ev_{type_.lower()}")
            event_list += event_funs

# Those two classes are UGLY, they should inherit or something !


class KeyboardFocusChange:
    def __init__(self, type_: str) -> None:
        if type_ not in ["KEYBOARDFOCUSLOST", "KEYBOARDFOCUSGAIN"]:
            raise ValueError(
                "type_ must be KEYBOARDFOCUSLOST or KEYBOARDFOCUSGAIN")
        self.type = type_


class MouseFocusChange:
    def __init__(self, event: tcod.event.MouseMotion, type_: str) -> None:
        if type_ not in ["MOUSEFOCUSGAIN", "MOUSEFOCUSLOST"]:
            raise ValueError("type_ must be MOUSEFOCUSLOST or MOUSEFOCUSGAIN")
        self.type = type_
        self.sdl_event = event.sdl_event
        self.pixel = event.pixel
        self.pixel_motion = event.pixel_motion
        self.tile = event.tile
        self.tile_motion = event.tile_motion
        self.state = event.state
