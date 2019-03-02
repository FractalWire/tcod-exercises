import sys
import random
from typing import Tuple, Union, Any
import tcod
import tcod.event
import sympy as sy
import tcodplus.canvas as canvas
import tcodplus.widgets as widgets
import tcodplus.style as tcp_style


def main():
    width = height = 70
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    root_canvas = canvas.RootCanvas(width, height,
                                    "Challenge 7 : GraphViewer",
                                    font, flags,
                                    renderer=tcod.constants.RENDERER_OPENGL,
                                    bg_color=(20, 20, 20))

    style = tcp_style.Style(x=.05, y=.05, width=.9, height=.9,
                            bg_color=(220, 220, 220), fg_color=(190, 190, 190))
    gd = GraphDisplay(style=style)
    gf1 = GraphFunction("f", "-100/x")
    gf2 = GraphFunction("g", "exp(x)", symbol="@")
    gf3 = GraphFunction("h", "log(x)", symbol="$")
    # gf4 = GraphFunction("i", "tan(3*x)", symbol="o")
    gd.childs["viewer"].funs.update({gf1.name: gf1, gf2.name: gf2,
                                     gf3.name: gf3})

    root_canvas.childs.add(gd)

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

        # style declaration
        viewer_style = tcp_style.Style(x=0, y=0, width=1., height=1.,
                                       bg_color=self.style.bg_color,
                                       fg_color=self.style.fg_color)

        fg_coords = tcod.Color(255, 255, 255)-self.style.bg_color
        coords_style = tcp_style.Style(bg_alpha=0., fg_color=fg_coords)

        bg_help = tcod.Color(255, 255, 255)-self.style.fg_color+(128, 128, 0)
        fg_help = tcod.Color(255, 255, 255)-self.style.bg_color
        help_style = tcp_style.Style(x=.98, y=.02, width=3, height=3,
                                     bg_alpha=.5, fg_alpha=.75,
                                     bg_color=bg_help, fg_color=fg_help,
                                     origin=tcp_style.Origin.TOP_RIGHT,
                                     border=tcp_style.Border.SOLID)
        info_style = tcp_style.Style(max_width=20, bg_color=bg_help,
                                     fg_color=fg_help, visible=False,
                                     border=tcp_style.Border.SOLID)
        crosshair_style = tcp_style.Style(width=1, height=1, bg_alpha=.1,
                                          fg_color=(20, 20, 20), visible=False)

        # widgets creation
        viewer = GraphViewer(name="viewer", title=title, style=viewer_style)
        crosshair = canvas.Canvas(style=crosshair_style)
        coords = widgets.Tooltip(delay=0, fade_duration=0, style=coords_style)
        help_ = widgets.Button("?", style=help_style)
        info = widgets.Tooltip(delay=0.3, fade_duration=0.3, style=info_style)
        info.value = """
 * Drag and drop the graph viewer with the LMB.

 * Zoom with the mouse wheel.

 * You can zoom the X-axis only by pressing CTRL while zooming.

 * You can zoom the Y-axis only by pressing SHIFT while zooming.
 """

        self.childs.add(viewer, crosshair, coords, help_, info)

        crosshair.update_geometry()
        crosshair.base_drawing()  # should probably override instead
        crosshair.console.ch[0, 0] = 197

        def viewer_crosshair_event(event: tcod.event.MouseMotion) -> None:
            if event.type == 'MOUSEFOCUSGAIN':
                crosshair.style.visible = True
                crosshair.force_redraw = True
            elif event.type == 'MOUSEFOCUSLOST':
                crosshair.style.visible = False
                crosshair.force_redraw = True
            elif event.type == 'MOUSEMOTION':
                cx, cy = event.tile
                rel_x = cx - viewer.geometry.abs_x
                rel_y = cy - viewer.geometry.abs_y
                crosshair.style.x = rel_x
                crosshair.style.y = rel_y

        def viewer_coords_event(event: tcod.event.MouseMotion) -> None:
            if event.type in ("MOUSEMOTION", "MOUSEFOCUSGAIN"):
                mcx, mcy = event.tile
                vabs_x, vabs_y, _, _, _, _, vwidth, vheight = viewer.geometry
                x = viewer.itox(mcx-vabs_x)
                y = viewer.jtoy(mcy-vabs_y)
                coords.value = f"({x:g}, {y:g})"
                coords.style.x = vwidth - (len(coords.value))
                coords.style.y = vheight-1
            else:  # MOUSEFOCUSLOST
                coords.value = ""

        def help_info_event(event: tcod.event.MouseMotion) -> None:
            if event.type == "MOUSEFOCUSGAIN":
                help_.style.bg_alpha = 1.0
                help_.style.fg_alpha = 1.0
                info.start_timer()
                info.style.x = help_.geometry.x-info.geometry.width
                info.style.y = help_.geometry.y
                info.should_update = True
                info.style.visible = True
            else:  # MOUSEFOCUSLOST
                help_.style.bg_alpha = 0.5
                help_.style.fg_alpha = 0.75
                info.should_update = False
                info.style.visible = False

        vfoc_d = viewer.focus_dispatcher
        vfoc_d.add_events([viewer_coords_event, viewer_crosshair_event],
                          ["MOUSEMOTION", "MOUSEFOCUSGAIN", "MOUSEFOCUSLOST"])

        hfoc_d = help_.focus_dispatcher
        hfoc_d.add_events([help_info_event],
                          ["MOUSEFOCUSGAIN", "MOUSEFOCUSLOST"])

    def add_fun(self, values: Tuple[str, str, str, str]) -> None:
        print("More fun !")
        name, fun, symbol, color = values
        gf = GraphFunction(name, fun, symbol)
        self.childs["viewer"].funs[name] = gf
        self.childs["viewer"].should_update = True


class GraphFunction:
    def __init__(self, name: str, fun_expr: str, symbol: str = "+",
                 color: Tuple[int, int, int] = None, title: str = ""):
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
        self.color = color if color is not None \
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

        def ev_mousemotion(event: tcod.event.MouseMotion) -> None:
            mcx, mcy = event.tile

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

            if event.type == 'MOUSEFOCUSGAIN':
                tcod.mouse_show_cursor(False)
                if not self.kbdfocus:
                    self.kbdfocus_requested = True
            elif event.type == 'MOUSEFOCUSLOST':
                tcod.mouse_show_cursor(True)

        def ev_mousewheel(event: tcod.event.MouseWheel) -> None:
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

        def ev_keydown(event: tcod.event.KeyDown) -> None:
            if event.sym in (tcod.event.K_LSHIFT, tcod.event.K_RSHIFT):
                self._shifts = True
            elif event.sym in (tcod.event.K_LCTRL, tcod.event.K_RCTRL):
                self._ctrls = True

        def ev_keyup(event: tcod.event.KeyUp) -> None:
            if event.sym in (tcod.event.K_LSHIFT, tcod.event.K_RSHIFT):
                self._shifts = False
            elif event.sym in (tcod.event.K_LCTRL, tcod.event.K_RCTRL):
                self._ctrls = False

        foc_d = self.focus_dispatcher
        foc_d.add_events([ev_mousemotion],
                         ["MOUSEMOTION", "MOUSEFOCUSLOST", "MOUSEFOCUSGAIN"])
        foc_d.ev_mousewheel += [ev_mousewheel]
        foc_d.ev_keydown += [ev_keydown]
        foc_d.ev_keyup += [ev_keyup]

    def itox(self, i: int) -> float:
        return self.camera.x + (i-self.geometry.content_width//2)*(2**self.camera.zoom_x)

    def jtoy(self, j: int) -> float:
        return self.camera.y + (self.geometry.content_height//2-j)*(2**self.camera.zoom_y)

    def xtoi(self, x: float) -> int:
        x = sorted([-sys.maxsize, x, sys.maxsize])[1]
        return round((x - self.camera.x) / (2**self.camera.zoom_x)
                     + self.geometry.content_width // 2)

    def ytoj(self, y: float) -> int:
        y = sorted([-sys.maxsize, y, sys.maxsize])[1]
        return round(((y - self.camera.y) / (2**self.camera.zoom_y)
                      - self.geometry.content_height // 2) * (-1))

    def update(self):
        itox = self.itox
        jtoy = self.jtoy
        xtoi = self.xtoi
        ytoj = self.ytoj

        def init_axis():
            width, height = self.geometry[6:]
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
            for i in range((width//2) % step, width, step):
                x = itox(i)
                x = f"{x:g}"
                x_width = len(x)
                i0 = i - x_width//2
                if 0 <= i0 and i0+x_width < width:
                    self.console.ch[j_axis, i0:i0+x_width] = [ord(c)
                                                              for c in x]
                    self.console.fg[j_axis, i0:i0+x_width] = self.axis_color

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
                      max_height: int) -> None:
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

        def get_j(i: int, fun: Any,
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

        width, height = self.geometry[6:]

        self.console.clear(fg=self.style.fg_color, bg=self.style.bg_color)
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


if __name__ == "__main__":
    main()
