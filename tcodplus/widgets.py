from __future__ import annotations
import time
import tcod.event
from tcodplus.canvas import Canvas
from tcodplus import event as tcp_event
from tcodplus.interfaces import IUpdatable, IFocusable, IMouseFocusable, IKeyboardFocusable


################
# BASE WIDGETS #
################

class BaseUpdatable(Canvas, IUpdatable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._should_update = True

    @property
    def should_update(self) -> bool:
        return self._should_update

    @should_update.setter
    def should_update(self, value: bool) -> None:
        self._should_update = value


class BaseFocusable(BaseUpdatable, IFocusable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._focus_dispatcher = tcp_event.CanvasDispatcher()

    @property
    def focus_dispatcher(self):
        return self._focus_dispatcher


class BoxFocusable(BaseFocusable, IMouseFocusable):
    def mousefocus(self, event: tcod.event.MouseMotion) -> bool:
        mcx, mcy = event.tile
        abs_x, abs_y, _, _, width, height = self.geometry
        m_rel_x = mcx - abs_x
        m_rel_y = mcy - abs_y
        is_in_x = (0 <= m_rel_x <= width-1)
        is_in_y = (0 <= m_rel_y <= height-1)
        return is_in_x and is_in_y


class KeyColorFocusable(BaseFocusable, IMouseFocusable):
    def mousefocus(self, event: tcod.event.MouseMotion) -> bool:
        mcx, mcy = event.tile
        abs_x, abs_y = self.geometry[:3]
        m_rel_x = mcx - abs_x
        m_rel_y = mcy - abs_y

        return self.console.bg[m_rel_y, m_rel_x] != self.key_color


class BaseKeyboardFocusable(BaseFocusable, IKeyboardFocusable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kbdfocus = False
        self._kbdfocus_requested = False

    @property
    def kbdfocus(self) -> bool:
        return self._kbdfocus

    @kbdfocus.setter
    def kbdfocus(self, val: bool) -> None:
        self.kbdfocus_requested = False
        if self.kbdfocus != val:
            self.should_update = True
        self._kbdfocus = val

    @property
    def kbdfocus_requested(self) -> bool:
        return self._kbdfocus_requested

    @kbdfocus_requested.setter
    def kbdfocus_requested(self, val: bool) -> None:
        self._kbdfocus_requested = val

####################
# CONCRETE WIDGETS #
####################


class Tooltip(BaseUpdatable):
    def __init__(self, value: str = "", delay: float = 0.,
                 fade_duration: float = 0., *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._value = value
        self._delay = delay
        self._fade_duration = fade_duration
        self._last_time = 0.

        self.should_update = False

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val) -> None:
        if val:
            self.start_timer()
            self.should_update = True
        else:
            self.should_update = False
        self._value = val

    def start_timer(self) -> None:
        self._last_time = time.perf_counter()

    def update(self) -> None:
        if not self.value:
            self.should_update = False
        else:
            dt = time.perf_counter() - self._last_time
            if dt < self._delay:
                pass
            elif dt > (self._delay + self._fade_duration + 0.5):
                self.should_update = False
            else:
                has_border = self.style.border != 0
                width = len(self.value) + 2*has_border
                if self.style.max_width is not None:
                    width = min(width, self.style.max_width)

                content_w = width - 2*has_border
                text_h = tcod.console.get_height_rect(content_w, self.value)
                height = text_h + 2 * has_border
                if self.style.max_height is not None:
                    height = min(height, self.style.max_height)

                content_h = height - 2*has_border

                x = int(has_border)
                y = int(has_border)

                self.style.width = width
                self.style.height = height
                self.update_geometry()

                self.console.clear(fg=self.style.fg_color,
                                   bg=self.style.bg_color)
                self.console.print_box(x, y, content_w, content_h, self.value,
                                       self.style.fg_color, self.style.bg_color)

    def draw(self) -> None:
        if len(self.value) > 0:

            bg_alpha = self.style.bg_alpha
            fg_alpha = self.style.fg_alpha

            dt = time.perf_counter() - self._last_time
            fade = 1.
            if self._fade_duration > 0.:
                fade = (dt - self._delay) / self._fade_duration
            if dt > self._delay:
                if fade > 1.:
                    fade = 1.
                self.style.bg_alpha = bg_alpha * fade
                self.style.fg_alpha = fg_alpha * fade

                super().draw()
                self.style.bg_alpha = bg_alpha
                self.style.fg_alpha = fg_alpha


class Button(BoxFocusable, BaseKeyboardFocusable):
    ''' still EXPERIMENTAL '''

    def __init__(self, value: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value
        if self.style.height == 0:
            self.style.height = 1

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val: str) -> None:
        self._value = val
        self.should_update = True

    def update(self) -> None:
        has_border = self.style.border != 0
        content_w = self.geometry.width - 2*has_border
        content_h = self.geometry.height - 2*has_border
        text_h = self.console.get_height_rect(has_border, has_border,
                                              content_w, content_h, self.value)
        x = int(has_border)
        y = (content_h - text_h)//2 + has_border
        self.console.print_box(x, y, content_w, content_h, self.value,
                               self.style.fg_color, self.style.bg_color,
                               alignment=tcod.constants.CENTER)
        self.should_update = False


class InputField(BoxFocusable, BaseKeyboardFocusable):
    def __init__(self, *args, value: str = "", max_len: int = 128, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value
        self.max_len = max_len
        self._pos = 0
        self._offset = 0

        if self.style.width == 0:
            self.style.width = 10  # default value
        self.style.height = 1

        def _ev_mousefocuslost(self, event: tcp_event.MouseFocusChange) -> None:
            # self.bg_color = [min(col+20, 255) for col in self.bg_color]
            # Need to find something better here
            self.should_update = True

        def _ev_mousefocusgain(self, event: tcp_event.MouseFocusChange) -> None:
            # self.bg_color = [max(col-20, 0) for col in self.bg_color]
            # Need to find something better here
            self.should_update = True

        def _ev_mousebuttondown(self, event: tcod.event.MouseButtonEvent):
            self.kbdfocus_requested = True
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
                if not self._pos == self._offset == 0:
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

    def update(self) -> None:
        width = self.geometry.width
        visible_value = self.value[self._offset:self._offset+width]

        self.console = self.init_console()
        self.console.print(0, 0, visible_value)

        # Need something better here
        if self.kbdfocus:
            self.console.bg[0, self._pos] = [
                255-col for col in self.style.bg_color]
            self.console.fg[0, self._pos] = [
                255-col for col in self.style.fg_color]
        self.should_update = False
