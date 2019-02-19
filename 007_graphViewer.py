import tcod
import tcod.event
import tcodplus.canvas as canvas
import tcodplus.widgets as widgets
import random
from typing import Tuple, Callable, NamedTuple, Union
import sympy as sy
import numpy as np
import sys
import traceback


def main():
    width = height = 70
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    root_canvas = canvas.RootCanvas(width, height,
                                    "Challenge 7 : GraphViewer",
                                    font, flags,
                                    bg_color=(20, 20, 20))

    gd = GraphDisplay(.05, .05, .9, .9,
                      bg_color=(220, 220, 220), fg_color=(190, 190, 190))
    gf1 = GraphFunction("f", "-100/x")
    gf2 = GraphFunction("g", "exp(x)", symbol="@")
    gf3 = GraphFunction("h", "log(x)", symbol="$")
    # gf4 = GraphFunction("i", "tan(3*x)", symbol="o")
    gd.viewer.funs.update({gf1.name: gf1, gf2.name: gf2,
                           gf3.name: gf3})

    root_canvas.childs += [gd]

    tcod.sys_set_fps(60)
    while not tcod.console_is_window_closed():
        root_canvas.refresh()
        tcod.console_flush()
        handle_events(root_canvas)


def handle_events(root_canvas: canvas.RootCanvas) -> None:
    for event in tcod.event.get():
        if event.type == "KEYDOWN" and event.sym == tcod.event.K_ESCAPE:
            raise SystemExit()
        root_canvas.handle_focus_event(event)


class GraphDisplay(canvas.Canvas):
    def __init__(self, *args, title="", **kwargs):
        super().__init__(*args, **kwargs)

        self.viewer = GraphViewer(0, 0, 1., 1., title=title,
                                  bg_color=self.bg_color,
                                  fg_color=self.fg_color)

        fg_tooltip = tcod.Color(255, 255, 255)-self.bg_color
        self.tooltip = widgets.Tooltip(bg_alpha=.0,
                                       fg_color=fg_tooltip,
                                       delay=0, fade_duration=0,
                                       has_border=False)

        bg_help = tcod.Color(255, 255, 255)-self.fg_color+(128, 128, 0)
        fg_help = tcod.Color(255, 255, 255)-self.bg_color
        self.help = widgets.Button("?", .94, .02, bg_alpha=0.5, fg_alpha=0.75,
                                   bg_color=bg_help, fg_color=fg_help)
        self.info_tooltip = widgets.Tooltip(bg_color=bg_help,
                                            fg_color=fg_help, bg_alpha=1.,
                                            delay=0.3, fade_duration=0.3,
                                            max_width=20)

        self.childs += [self.viewer, self.tooltip, self.help,
                        self.info_tooltip]

        def viewer_tooltip_event(event: tcod.event.MouseMotion) -> None:
            viewer = self.viewer
            tooltip = self.tooltip

            if event.type in ("MOUSEMOTION", "MOUSEFOCUSGAIN"):
                mcx, mcy = event.tile
                vabs_x, vabs_y, _, _, vwidth, vheight = viewer.geometry
                x = viewer.itox(mcx-vabs_x)
                y = viewer.jtoy(mcy-vabs_y)
                tooltip.value = f"({x:g}, {y:g})"
                tooltip.x = vwidth - (len(tooltip.value))
                tooltip.y = vheight-1
            else:  # MOUSEFOCUSLOST
                tooltip.value = ""

        def help_tooltip_event(event: tcod.event.MouseMotion) -> None:
            help_ = self.help
            info = self.info_tooltip
            help_.bg_alpha = 1.0
            help_.fg_alpha = 1.0
            if event.type == "MOUSEFOCUSGAIN":
                s = """
 * Drag and drop the graph viewer with the LMB.

 * Zoom with the mouse wheel.

 * You can zoom the X-axis only by pressing CTRL while zooming.

 * You can zoom the Y-axis only by pressing SHIFT while zooming.
 """
                self.info_tooltip.value = s
                info.x = help_.geometry.x-info.geometry.width
                info.y = help_.geometry.y
            else:  # MOUSEFOCUSLOST
                info.value = ""
                help_.bg_alpha = 0.5
                help_.fg_alpha = 0.75

        vfoc_dispatcher = self.viewer.focus_dispatcher
        vfoc_dispatcher.ev_mousemotion += [viewer_tooltip_event]
        vfoc_dispatcher.ev_mousefocusgain += [viewer_tooltip_event]
        vfoc_dispatcher.ev_mousefocuslost += [viewer_tooltip_event]

        hfoc_dispatcher = self.help.focus_dispatcher
        hfoc_dispatcher.ev_mousefocusgain += [help_tooltip_event]
        hfoc_dispatcher.ev_mousefocuslost += [help_tooltip_event]


class GraphFunction:
    def __init__(self, name: str, fun_expr: str,
                 color: Tuple[int, int, int] = None,
                 symbol: str = "+", title: str = ""):
        self.name = name
        expr = sy.sympify(fun_expr)
        if len(expr.free_symbols) > 1:
            raise ValueError(f"Expression invalid : "
                             f"there must be one symbol at most."
                             f"Given : {expr.free_symbols}")
        elif expr.has(sy.oo, -sy.oo, sy.zoo, sy.nan):
            raise ValueError("Expression invalid : "
                             f"Don't try to divide by zero, you scoundrel !")
        else:
            self.expr = expr
        self.color = color if color != None \
            else tuple(random.randrange(150) for _ in range(3))
        self.symbol = symbol
        self.title = title


class Camera:
    def __init__(self, x: float = 0, y: float = 0,
                 zoom_x: float = 0, zoom_y: float = 0):
        self.x = x
        self.y = y
        self.zoom_x = zoom_x
        self.zoom_y = zoom_y


class GraphViewer(widgets.BoxFocusable, widgets.BaseKeyboardFocusable):
    def __init__(self, *args, title="", camera=Camera(), **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.funs = {}
        self.camera = camera
        self.axis_color = (200, 60, 60)
        self.axis_step = 15
        self._shifts = False
        self._ctrls = False

        self.focus_dispatcher.ev_mousemotion += [self._ev_mousemotion]
        self.focus_dispatcher.ev_mousefocusgain += [self._ev_mousemotion]
        self.focus_dispatcher.ev_mousefocuslost += [self._ev_mousemotion]
        self.focus_dispatcher.ev_mousewheel += [self._ev_mousewheel]
        self.focus_dispatcher.ev_keydown += [self._ev_keydown]
        self.focus_dispatcher.ev_keyup += [self._ev_keyup]

    def itox(self, i: int) -> float:
        return self.camera.x + (i-self.geometry.width//2)*(2**self.camera.zoom_x)

    def jtoy(self, j: int) -> float:
        return self.camera.y + (self.geometry.height//2-j)*(2**self.camera.zoom_y)

    def xtoi(self, x: float) -> int:
        x = sorted([-sys.maxsize, x, sys.maxsize])[1]
        return round((x - self.camera.x) / (2**self.camera.zoom_x)
                     + self.geometry.width // 2)

    def ytoj(self, y: float) -> int:
        y = sorted([-sys.maxsize, y, sys.maxsize])[1]
        return round(((y - self.camera.y) / (2**self.camera.zoom_y)
                      - self.geometry.height // 2) * (-1))

    def update(self):
        itox = self.itox
        jtoy = self.jtoy
        xtoi = self.xtoi
        ytoj = self.ytoj

        def init_axis():
            width, height = self.geometry[4:]
            i_axis = sorted([0, xtoi(0), width-1])[1]
            j_axis = sorted([0, ytoj(0), height-1])[1]

            # drawing the axis line
            self.console.ch[:, i_axis] = 179
            self.console.ch[j_axis, :] = 196
            self.console.fg[:, i_axis] = [50]*3
            self.console.fg[j_axis, :] = [50]*3
            self.console.ch[j_axis, i_axis] = 197
            self.console.ch[j_axis, width-1] = 16
            self.console.ch[0, i_axis] = 30

            # drawing the axis step
            step = self.axis_step
            zoom = f"{2**self.camera.zoom_x:g}"
            x_precision = 0 if "." not in zoom else len(zoom.split(".")[1])
            for i in range((width//2) % step, width, step):
                x = itox(i)
                x = f"{x:g}"
                x_width = len(x)
                i0 = i - x_width//2
                if 0 <= i0 and i0+x_width < width:
                    self.console.ch[j_axis, i0:i0+x_width] = [ord(c)
                                                              for c in x]
                    self.console.fg[j_axis, i0:i0+x_width] = self.axis_color

            zoom = f"{2**self.camera.zoom_y:g}"
            y_precision = 0 if "." not in zoom else len(zoom.split(".")[1])
            for j in range((height//2) % step, height, step):
                y = jtoy(j)
                y = f"{y:g}"
                y_width = len(y)
                i0 = i_axis - y_width//2
                if i0 < 0:
                    i0 = 0
                elif i0+y_width >= width:
                    i0 = width-y_width
                self.console.ch[j, i0:i0+y_width] = [ord(c) for c in y]
                self.console.fg[j, i0:i0+y_width] = self.axis_color

        def draw_line(p1: Tuple[int, int], p2: Tuple[int, int],
                      max_height: int) -> int:
            i1, j1 = p1
            i2, j2 = p2
            # dealing with ascending or descending function difference here
            # this is so weird ! but it seems to work...
            var1 = j1 > j2
            i1, i2 = (i1, i2)[::1-2*var1]
            j1, j2 = (j1, j2)[::1-2*var1]
            j1, j2 = j1+var1, j2+var1
            # dealing with rounding issue here
            var2 = ((j2-j1) - int(j2-j1)) <= 0.5
            b1margin = (j2-j1) // 2 + var2
            a2margin = (j2-j1) // 2 + (not var2)
            b1margin, a2margin = (b1margin, a2margin)[::1-2*var1]
            a1, b1, a2, b2 = j1, j1+b1margin, j2-a2margin, j2

            def middle_value(val) -> int:
                return sorted([0, val, height-1])[1]
            if j1 < 0:
                a1 = 0
                b1 = middle_value(j1+b1margin)
                a2 = middle_value(j1+b1margin)
            elif j1 >= max_height-1:
                a1 = max_height-1
                b1 = middle_value(j1+b1margin)
                a2 = middle_value(j2-a2margin)
            if j2 < 0:
                b1 = middle_value(j1+b1margin-1)
                a2 = middle_value(j2-a2margin)
                b2 = 0
            elif j2 >= max_height:
                b1 = middle_value(j1+b1margin)
                a2 = middle_value(j2-a2margin-1)
                b2 = max_height-1

            if i1 != -1:
                for j in range(a1, b1):
                    self.console.ch[j, i1] = ord(fun.symbol)
                    self.console.fg[j, i1] = fun.color
            if i2 != -1:
                for j in range(a2, b2):
                    self.console.ch[j, i2] = ord(fun.symbol)
                    self.console.fg[j, i2] = fun.color

        def get_j(i: int, fun: Callable[[float], float],
                  lim_sign: str = '') -> Union[int, str]:
            x = itox(i)
            res = None
            if lim_sign in ['+', '-']:
                res = fun.expr.limit(fun.expr.free_symbols.pop(), x, lim_sign)
            else:
                res = fun.expr.subs(fun.expr.free_symbols.pop(), x)
                if res.is_infinite:
                    return 'inf'
            if not res.is_real:
                return 'complex'
            y = float(res)
            j = ytoj(y)
            return j

        width, height = self.geometry[4:]

        self.console.clear(fg=self.fg_color, bg=self.bg_color)
        self.console.ch[:] = ord("#")
        init_axis()

        for fun in self.funs.values():
            prev_j = get_j(-1, fun)
            for i in range(width):
                if prev_j == 'inf':
                    prev_j = get_j(i-1, fun, '+')

                j = tmp_j = get_j(i, fun)
                if j == 'inf':
                    j = get_j(i, fun, '-')

                if isinstance(j, int) and isinstance(prev_j, int):
                    draw_line((i-1, prev_j), (i, j), height)

                prev_j = tmp_j

        self.should_update = False

    def _ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        mcx, mcy = event.tile
        abs_x, abs_y = self.geometry.abs_x, self.geometry.abs_y
        m_rel_x = mcx - abs_x
        m_rel_y = mcy - abs_y

        # Drag
        dcx = dcy = 0
        if event.state & tcod.event.BUTTON_LMASK:
            dcx, dcy = event.tile_motion
            if dcx:
                self.camera.x -= dcx*2**self.camera.zoom_x
            if dcy:
                self.camera.y += dcy*2**self.camera.zoom_y
            if dcx or dcy:
                self.should_update = True
        else: # Tile focus
            if event.type == 'MOUSEFOCUSGAIN':
                self.console.bg[m_rel_y, m_rel_x] = (200,200,0)
                if not self.iskeyboardfocused():
                    self.request_kbd_focus()
            elif event.type == 'MOUSEFOCUSLOST':
                dcx, dcy = event.tile_motion
                if 0 <= m_rel_x-dcx < self.geometry.width \
                        and 0 <= m_rel_y-dcy < self.geometry.height:
                    self.console.bg[m_rel_y-dcy, m_rel_x-dcx] = self.bg_color
            elif event.type == 'MOUSEMOTION':
                dcx, dcy = event.tile_motion
                if dcx or dcy:
                    self.console.bg[m_rel_y, m_rel_x] = (200,200,0)
                    self.console.bg[m_rel_y-dcy, m_rel_x-dcx] = self.bg_color

    def _ev_mousewheel(self, event: tcod.event.MouseWheel) -> None:
        mv = (-1+event.flipped*2) * event.y
        is_zx_ok = self.camera.zoom_x < 54
        is_zy_ok = self.camera.zoom_y < 54

        if self._shifts and (is_zx_ok or mv < 0):
            self.camera.zoom_x += mv
        elif self._ctrls and (is_zy_ok or mv < 0):
            self.camera.zoom_y += mv
        else:
            if is_zx_ok or mv < 0:
                self.camera.zoom_x += mv
            if is_zy_ok or mv < 0:
                self.camera.zoom_y += mv
        self.should_update = True

    def _ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym in (tcod.event.K_LSHIFT, tcod.event.K_RSHIFT):
            self._shifts = True
        elif event.sym in (tcod.event.K_LCTRL, tcod.event.K_RCTRL):
            self._ctrls = True

    def _ev_keyup(self, event: tcod.event.KeyUp) -> None:
        if event.sym in (tcod.event.K_LSHIFT, tcod.event.K_RSHIFT):
            self._shifts = False
        elif event.sym in (tcod.event.K_LCTRL, tcod.event.K_RCTRL):
            self._ctrls = False


if __name__ == "__main__":
    main()
