from __future__ import annotations
from typing import Union
from collections.abc import Mapping
import time
import tcod.event
from tcodplus.canvas import Canvas
from tcodplus import event as tcp_event
from tcodplus.interfaces import IUpdatable, IFocusable, IMouseFocusable, IKeyboardFocusable
from tcodplus.style import Style


################
# BASE WIDGETS #
################

class BaseUpdatable(Canvas, IUpdatable):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._should_update = True

    @property
    def should_update(self) -> bool:
        return self._should_update

    @should_update.setter
    def should_update(self, value: bool) -> None:
        self._should_update = value


class BaseFocusable(BaseUpdatable, IFocusable):
    def __init__(self, *args, style_focus: Union[dict, Style] = dict(),
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._focus_dispatcher = tcp_event.CanvasDispatcher()
        self._current_style = self._style
        self._style_focus = None
        self.style_focus = style_focus
        self._is_focus = False

        def style_focus_on(event: tcod.event.Event) -> None:
            self._is_focus = True
            self.force_redraw = True

        def style_focus_off(event: tcod.event.Event) -> None:
            self._is_focus = False
            self.force_redraw = True

        self.focus_dispatcher.add_events([style_focus_on],
                                         ["KEYBOARDFOCUSGAIN", "MOUSEFOCUSGAIN"])
        self.focus_dispatcher.add_events([style_focus_off],
                                         ["KEYBOARDFOCUSLOST", "MOUSEFOCUSLOST"])

    def styles(self) -> Style:
        style = super().styles()
        if self._is_focus:
            style = self.style_focus | style
        return style

    @property
    def focus_dispatcher(self) -> None:
        return self._focus_dispatcher

    @property
    def style(self) -> Style:
        return self._style

    @style.setter
    def style(self, value: Union[Style, Mapping]) -> None:
        self._style = value if isinstance(value, Style) \
            else Style(value)
        self.force_redraw = True

    @property
    def style_focus(self) -> Style:
        return self._style_focus

    @style_focus.setter
    def style_focus(self, value: Union[Style, Mapping]) -> None:
        self._style_focus = value if isinstance(value, Style) \
            else Style(value)
        self.force_redraw = True


class BoxFocusable(BaseFocusable, IMouseFocusable):
    def mousefocus(self, event: tcod.event.MouseMotion) -> bool:
        mcx, mcy = event.tile
        abs_x, abs_y, _, _, width, height, _, _ = self.geometry
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
    def __init__(self, *args, **kwargs) -> None:
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

        self.style.width = "auto"
        self.style.height = "auto"
        self.style.visible = False

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
        style = self.styles()
        has_border = style.border != 0
        width = len(self.value)
        if style.max_width is not None:
            width = min(width, style.max_width - 2*has_border)

        height = tcod.console.get_height_rect(width, self.value)
        if style.max_height is not None:
            height = min(height, style.max_height - 2*has_border)

        self.console = self.init_console(width, height)

        self.base_drawing()
        self.console.print_box(0, 0, width, height, self.value,
                               style.fg_color, style.bg_color)
        self.should_update = False
        self.force_redraw = True

    def draw(self) -> None:
        if self.value:
            dt = time.perf_counter() - self._last_time
            fade = 1.
            if self._fade_duration > 0.:
                fade = (dt - self._delay) / self._fade_duration
            if dt > self._delay:
                if fade > 1.:
                    fade = 1.

                bg_alpha = self.style.bg_alpha
                fg_alpha = self.style.fg_alpha
                self.style.bg_alpha = bg_alpha * fade
                self.style.fg_alpha = fg_alpha * fade

                super().draw()
                self.style.bg_alpha = bg_alpha
                self.style.fg_alpha = fg_alpha

            if dt <= self._delay + self._fade_duration:
                self.force_redraw = True


class Button(BoxFocusable, BaseKeyboardFocusable):
    ''' still EXPERIMENTAL '''

    def __init__(self, value: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val: str) -> None:
        self._value = val
        self.should_update = True

    def update(self) -> None:
        content_w = max(len(self.value), self.geometry.content_width)
        content_h = max(1, self.geometry.content_height)
        if content_w != self.console.width or content_h != self.console.height:
            self.console = self.init_console(content_w, content_h)
            self.update_geometry()

        text_h = self.console.get_height_rect(0, 0, 0, 0, self.value)

        y = (content_h - text_h)//2

        style = self.styles()
        self.console.print_box(0, y, content_w, content_h, self.value,
                               style.fg_color, style.bg_color,
                               alignment=tcod.constants.CENTER)
        self.should_update = False


class InputField(BoxFocusable, BaseKeyboardFocusable):
    def __init__(self, *args, value: str = "", max_len: int = 128,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._value = value
        self.max_len = max_len
        self._pos = 0
        self._offset = 0

        style = self.styles()
        if style.width == 0:
            style.width = 10  # default value
        style.height = 1

        def ev_mousefocuslost(event: tcp_event.MouseFocusChange) -> None:
            # self.bg_color = [min(col+20, 255) for col in self.bg_color]
            # Need to find something better here
            self.should_update = True

        def ev_mousefocusgain(event: tcp_event.MouseFocusChange) -> None:
            # self.bg_color = [max(col-20, 0) for col in self.bg_color]
            # Need to find something better here
            self.should_update = True

        def ev_mousebuttondown(event: tcod.event.MouseButtonEvent) -> None:
            self.kbdfocus_requested = True
            self.should_update = True

        def ev_keydown(event: tcod.event.KeyboardEvent) -> None:
            def right():
                if self._offset + self._pos == len(self._value):
                    pass
                elif self._pos == self.geometry.content_width-1:
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
                self._offset = max(0, val_len - self.geometry.content_width+1)
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

        def ev_textinput(event: tcod.event.TextInput) -> None:
            def right():
                if self._offset + self._pos == len(self._value):
                    pass
                elif self._pos == self.geometry.content_width-1:
                    self._offset = self._offset+1
                else:
                    self._pos += 1
            if len(self.value) < self.max_len:
                val = self.value
                insert_ind = self._offset + self._pos
                self.value = val[:insert_ind]+event.text+val[insert_ind:]
                right()
                self.should_update = True

        self.focus_dispatcher.ev_mousefocusgain += [ev_mousefocusgain]
        self.focus_dispatcher.ev_mousefocuslost += [ev_mousefocuslost]
        self.focus_dispatcher.ev_mousebuttondown += [ev_mousebuttondown]
        self.focus_dispatcher.ev_keydown += [ev_keydown]
        self.focus_dispatcher.ev_textinput += [ev_textinput]

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, val: str) -> None:
        self.should_update = True
        self._value = val

    def update(self) -> None:
        width = self.geometry.content_width
        visible_value = self.value[self._offset:self._offset+width]

        # TODO: Better color scheme please
        style = self.styles()
        bg = style.bg_color * \
            (0.75 if len(self.value) == self.max_len else 1)

        self.console.clear(bg=bg, fg=style.fg_color)
        self.console.print(0, 0, visible_value, bg=bg)

        # TODO: Need something better here for opposite color
        if self.kbdfocus:
            self.console.bg[0, self._pos] = [255-col
                                             for col in style.bg_color]
            self.console.fg[0, self._pos] = [255-col
                                             for col in style.fg_color]
        self.should_update = False
