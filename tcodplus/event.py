from typing import List, NamedTuple, Tuple
import tcod.event
from tcodplus import interfaces


MouseFocus = NamedTuple('MouseFocus',
                        [('focused', List['Canvas']),
                         ('focus_lost', List['Canvas']),
                            ('focus_gain', List['Canvas'])])


class KeyboardFocusAdmin:
    # This class assume at any time there is only one focused element and one
    # requesting focused element, which might not be true...
    @classmethod
    def update_focus(cls, focusable: List['interfaces.IKeyboardFocusable']) \
            -> Tuple[int, int]:
        i_req = cls.request_focus_index(focusable)
        if i_req != -1:
            i_foc = cls.focus_index(focusable)
            if i_req != i_foc:
                focusable[i_req].change_kbd_focus(True)
                if i_foc != -1:
                    focusable[i_foc].change_kbd_focus(False)
            return i_foc,i_req
        return -1,-1

    @staticmethod
    def request_focus_index(focusable: List['interfaces.IKeyboardFocusable']) -> int:
        for i, kf in enumerate(focusable):
            if kf.iskeyboardfocus_requested():
                return i
        else:
            return -1

    @staticmethod
    def focus_index(focusable: List['interfaces.IKeyboardFocusable']) -> int:
        for i, kf in enumerate(focusable):
            if kf.iskeyboardfocused():
                return i
        else:
            return -1

    @classmethod
    def next(cls, focusable: List['interfaces.IKeyboardFocusable']) -> int:
        if len(focusable) > 0:
            i = cls.focus_index(focusable)
            next_i = (i+1) % len(focusable)
            focusable[next_i].request_kbd_focus()
            return next_i
        return -1

    @classmethod
    def previous(cls, focusable: List['interfaces.IKeyboardFocusable']) -> int:
        if len(focusable) > 0:
            i = cls.focus_index(focusable)
            if i == -1:
                i = 0
            prev_i = (i-1) % len(focusable)
            focusable[prev_i].request_kbd_focus()
            return prev_i
        return -1


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
        self.ev_keyboardfocuslost = []
        self.ev_keyboardfocusgain = []

    def dispatch(self, event: tcod.event.Event) -> None:
        if event.type:
            event_list = getattr(self, f"ev_{event.type.lower()}")
            for ev in event_list:
                ev(event)


class KeyboardFocusChange:
    def __init__(self, type_: str):
        if type_ not in ["KEYBOARDFOCUSLOST", "KEYBOARDFOCUSGAIN"]:
            raise ValueError(
                "type_ must be KEYBOARDFOCUSLOST or KEYBOARDFOCUSGAIN")
        self.type = type_


class MouseFocusChange:
    def __init__(self, event: tcod.event.MouseMotion, type_: str):
        if type_ not in ["MOUSEFOCUSGAIN", "MOUSEFOCUSLOST"]:
            raise ValueError("type_ must be MOUSEFOCUSLOST or MOUSEFOCUSGAIN")
        self.type = type_
        self.sdl_event = event.sdl_event
        self.pixel = event.pixel
        self.pixel_motion = event.pixel_motion
        self.tile = event.tile
        self.tile_motion = event.tile_motion
        self.state = event.state
