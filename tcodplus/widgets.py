import tcod.event
import time
import textwrap
from tcodplus import canvas
from tcodplus import interfaces
from tcodplus import event


################
# BASE WIDGETS #
################

class BaseUpdatable(canvas.Canvas, interfaces.IUpdatable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._should_update = True

    @property
    def should_update(self) -> bool:
        return self._should_update

    @should_update.setter
    def should_update(self, value: bool) -> None:
        self._should_update = value


class BaseFocusable(BaseUpdatable, interfaces.IFocusable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._focus_dispatcher = event.CanvasDispatcher()

    @property
    def focus_dispatcher(self):
        return self._focus_dispatcher


class BoxFocusable(BaseFocusable, interfaces.IMouseFocusable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ismousefocused(self, event: tcod.event.MouseMotion) -> bool:
        mcx, mcy = event.tile
        abs_x, abs_y, _, _, width, height = self.geometry
        m_rel_x = mcx - abs_x
        m_rel_y = mcy - abs_y
        is_in_x = (0 <= m_rel_x <= width-1)
        is_in_y = (0 <= m_rel_y <= height-1)
        return is_in_x and is_in_y


class KeyColorFocusable(BaseFocusable, interfaces.IMouseFocusable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ismousefocused(self, event: tcod.event.MouseMotion) -> bool:
        mcx, mcy = event.tile
        abs_x, abs_y = self.geometry[:3]
        m_rel_x = mcx - abs_x
        m_rel_y = mcy - abs_y

        return self.console.bg[m_rel_y, m_rel_x] != self.key_color


class BaseKeyboardFocusable(BaseFocusable, interfaces.IKeyboardFocusable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kbd_focused = False
        self._request_kbd_focus = False

    def iskeyboardfocused(self) -> bool:
        return self._kbd_focused

    def change_kbd_focus(self, val: bool) -> None:
        self._request_kbd_focus = False
        if self.iskeyboardfocused != val:
            self.should_update = True
        self._kbd_focused = val

    def iskeyboardfocus_requested(self) -> bool:
        return self._request_kbd_focus

    def request_kbd_focus(self) -> None:
        self._request_kbd_focus = True

####################
# CONCRETE WIDGETS #
####################


class Tooltip(BaseUpdatable):
    def __init__(self, value: str = "",
                 fg_alpha: float = 1, bg_alpha: float = 0.7,
                 max_width: int = -1, max_height: int = -1,
                 delay: float = 0., fade_duration: float = 0.,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._value = value
        self.fg_alpha = fg_alpha
        self.bg_alpha = bg_alpha
        self.max_width = max_width
        self.max_height = max_height
        self._delay = delay
        self._fade_duration = fade_duration
        self._last_time = 0

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val) -> None:
        self._last_time = time.perf_counter()
        self._value = val

    def update_geometry(self, dest: canvas.Canvas) -> bool:
        up = super().update_geometry(dest)
        if up:
            self.should_update = True
        return up

    def update(self) -> None:
        if len(self.value) > 0:
            dt = time.perf_counter() - self._last_time
            if dt < self._delay:
                pass
            elif dt > (self._delay + self._fade_duration + 0.5):
                self.should_update = False
            else:
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

                self.console = self.init_console(width, height)
                self.console.bg[:] = self.bg_color
                self.console.fg[:] = self.fg_color
                self.console.ch[[0, -1], :] = 196
                self.console.ch[:, [0, -1]] = 179
                self.console.ch[[[0, -1], [-1, 0]],
                                [0, -1]] = [[218, 217], [192, 191]]

                for i, e in enumerate(lines):
                    self.console.print_(1, i+1, e)

    def draw(self, dest: canvas.Canvas) -> None:
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


class Button(BoxFocusable, BaseKeyboardFocusable):
    def __init__(self, value: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

        self.focus_dispatcher.ev_mousefocusgain += [self._ev_mousefocusgain]
        self.focus_dispatcher.ev_mousefocuslost += [self._ev_mousefocuslost]
        self.focus_dispatcher.ev_keyboardfocusgain += [self._ev_keyboardfocusgain]
        self.focus_dispatcher.ev_keyboardfocuslost += [self._ev_keyboardfocuslost]
        self.focus_dispatcher.ev_mousebuttonup += [self._ev_mousebuttonup]

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val: str) -> None:
        self.should_update = True
        self._value = val

    def update(self):
        height = 3
        width = 2 + len(self.value)
        self.console = tcod.console_new(width, height)

        self.console = self.init_console(width, height)
        self.console.bg[:] = self.bg_color
        self.console.fg[:] = self.fg_color
        self.console.ch[[0, -1], :] = 196
        self.console.ch[:, [0, -1]] = 179
        self.console.ch[[[0, -1], [-1, 0]],
                        [0, -1]] = [[218, 217], [192, 191]]
        self.console.fg[[0, -1], :] = (20, 20, 20)
        self.console.fg[:, [0, -1]] = (20, 20, 20)
        self.console.fg[[[0, -1], [-1, 0]],
                        [0, -1]] = (20, 20, 20)
        self.console.print_(1, 1, self.value)
        self.should_update = False

    def _ev_mousefocuslost(self, event: 'event.MouseFocusChange') -> None:
        self.bg_color = [min(col+20, 255) for col in self.bg_color]
        self.should_update = True

    def _ev_mousefocusgain(self, event: 'event.MouseFocusChange') -> None:
        self.bg_color = [max(col-20, 0) for col in self.bg_color]
        self.should_update = True

    def _ev_mousebuttonup(self, event: tcod.event.MouseButtonEvent):
        print("You clicked me !")

    def _ev_keyboardfocuslost(self, event: 'event.KeyboardFocusChange') -> None:
        print("keyboard focus lost")
        self.bg_color = [min(col+20, 255) for col in self.bg_color]
        self.should_update = True

    def _ev_keyboardfocusgain(self, event: 'event.KeyboardFocusChange') -> None:
        print("keyboard focus gain")
        self.bg_color = [max(col-20, 0) for col in self.bg_color]
        self.should_update = True



class InputField(BoxFocusable, BaseKeyboardFocusable):
    def __init__(self, *args, value: str = "", max_len: int = 128,
                 width: int = 10, height: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value
        self.max_len = max_len
        self._pos = 0
        self._offset = 0

        self.focus_dispatcher.ev_mousefocusgain += [self._ev_mousefocusgain]
        self.focus_dispatcher.ev_mousefocuslost += [self._ev_mousefocuslost]
        self.focus_dispatcher.ev_mousebuttondown += [self._ev_mousebuttondown]
        self.focus_dispatcher.ev_keydown += [self._ev_keydown]
        self.focus_dispatcher.ev_textinput += [self._ev_textinput]

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val: str) -> None:
        self.should_update = True
        self._value = val

    def update(self):
        height = 1
        width = self.geometry.width
        visible_value = self.value[self._offset:self._offset+width]
        self.console = tcod.console_new(width, height)

        self.console = self.init_console(width, height)
        self.console.bg[:] = self.bg_color
        self.console.fg[:] = self.fg_color
        self.console.print_(0, 0, visible_value)
        if self.iskeyboardfocused():
            self.console.bg[0, self._pos] = [255-col for col in self.bg_color]
            self.console.fg[0, self._pos] = [255-col for col in self.fg_color]
        self.should_update = False

    def _ev_mousefocuslost(self, event: event.MouseFocusChange) -> None:
        self.bg_color = [min(col+20, 255) for col in self.bg_color]
        self.should_update = True

    def _ev_mousefocusgain(self, event: event.MouseFocusChange) -> None:
        self.bg_color = [max(col-20, 0) for col in self.bg_color]
        self.should_update = True

    def _ev_mousebuttondown(self, event: tcod.event.MouseButtonEvent):
        print("keyboard focus requested")
        self.request_kbd_focus()
        self.should_update = True

    def _ev_keydown(self, event: tcod.event.KeyboardEvent) -> None:
        def right():
            if self._offset + self._pos == len(self._value):
                pass
            elif self._pos == self.geometry.width-1:
                self._offset = self._offset+1
            else:
                self._pos += 1

        if event.sym == tcod.event.K_LEFT:
            if self._pos == 0:
                self._offset = max(0, self._offset-1)
            else:
                self._pos -= 1
        elif event.sym == tcod.event.K_RIGHT:
            right()
        elif event.sym == tcod.event.K_END:
            val_len = len(self.value)
            self._offset = max(0, val_len - self.geometry.width+1)
            self._pos = val_len - self._offset
        elif event.sym == tcod.event.K_HOME:
            self._offset = 0
            self._pos = 0
        elif event.sym == tcod.event.K_BACKSPACE:
            if not (self._pos == self._offset == 0):
                val = self.value
                ind = self._pos + self._offset
                self.value = val[:ind-1]+val[ind:]

            if self._pos + self._offset == 0:
                pass
            elif self._offset > 0:
                self._offset = self._offset-1
            else:
                self._pos -= 1
        elif event.sym == tcod.event.K_DELETE:
            if self._offset + self._pos == len(self.value):
                pass
            else:
                val = self.value
                ind = self._offset + self._pos
                self.value = val[:ind]+val[ind+1:]

        self.should_update = True

    def _ev_textinput(self, event: tcod.event.TextInput):
        def right():
            if self._offset + self._pos == len(self._value):
                pass
            elif self._pos == self.geometry.width-1:
                self._offset = self._offset+1
            else:
                self._pos += 1
        if len(self.value) < self.max_len:
            val = self.value
            insert_ind = self._offset + self._pos
            self.value = val[:insert_ind]+event.text+val[insert_ind:]
            right()
            self.should_update = True
