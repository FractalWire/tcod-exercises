from typing import Tuple
import tcod
import tcodplus.canvas as canvas
import tcodplus.style as tcp_style
import tcodplus.widgets as widgets
from ch007_graph_viewer import GraphDisplay


def main() -> None:
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    tcod.console_set_custom_font(font, flags)

    r_width, r_height = tcod.sys_get_current_resolution()
    c_width, c_height = tcod.sys_get_char_size()
    width, height = (2*r_width) // (3*c_width), (2*r_height) // (3*c_height)
    # print(width, height, c_width, c_height)

    root_canvas = canvas.RootCanvas(width, height,
                                    "Challenge 7 : GraphViewer",
                                    font, flags, False,
                                    tcod.constants.RENDERER_OPENGL,
                                    bg_color=(20, 20, 20))

    gd_style = dict(x=.05, y=.05, width=.53, height=.9,
                    border=tcp_style.Border.DASHED,
                    border_fg_color=(20, 20, 20),
                    bg_color=(220, 220, 220), fg_color=(190, 190, 190))
    rp_style = dict(x=.95, y=.05, width=.3, height=.9,
                    bg_color=(220, 220, 220), fg_color=(20, 20, 20),
                    border=tcp_style.Border.DASHED,
                    origin=tcp_style.Origin.TOP_RIGHT)

    gd = GraphDisplay(style=gd_style)
    rp = RPanel(style=rp_style)

    def add_fun(event: tcod.event.Event) -> None:
        if event.type == "KEYDOWN" and event.sym != tcod.event.K_RETURN:
            return
        gd.add_fun(rp._focused_panel.edit_values)

    rp._focused_panel.childs["button_addmod"].focus_dispatcher.ev_keydown += [add_fun]
    rp._focused_panel.childs["button_addmod"].focus_dispatcher.ev_mousebuttondown += [add_fun]

    root_canvas.childs.add(gd, rp)

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


class RPanel(canvas.Canvas):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        edit_style = dict(y=4, width=1., height=1., bg_color=(20, 20, 20),
                          fg_color=(220, 220, 220),
                          border=tcp_style.Border.DOTTED,
                          display=tcp_style.Display.NONE)
        view_style = dict(y=4, width=1., height=1.,
                          display=tcp_style.Display.NONE)
        e_panel = EditPanel(name="EDIT_panel", style=edit_style)
        v_panel = ViewPanel(name="VIEW_panel", style=view_style)
        self.childs.add(e_panel, v_panel)
        self._focused_panel = e_panel  # TODO: make this dynamic...

        self.tab_style = tcp_style.Style(bg_color=(20, 20, 20),
                                         fg_color=(220, 220, 220),
                                         border=tcp_style.Border.EMPTY)
        self.tab_hover_style = tcp_style.Style(bg_color=(80, 80, 80),
                                               border=tcp_style.Border.EMPTY)
        self.tab_focus_style = tcp_style.Style(bg_color=(200, 200, 200),
                                               fg_color=(20, 20, 20),
                                               border=tcp_style.Border.DASHED)

        x = 0
        tabs = []
        for c in self.childs.values():
            tab = widgets.Button(value=c.title, name=f"{c.title}_tab",
                                 style=self.tab_style | {"x": x},
                                 style_focus=self.tab_hover_style)

            def tab_click(_, c=c):
                self.change_tab_focus(f"{c.title}")
            tab.focus_dispatcher.ev_mousebuttondown.append(tab_click)

            tabs += [tab]
            x += len(tab.value) + 2

        self.childs.add(*tabs)

        self.change_tab_focus("EDIT")

    def change_tab_focus(self, title: str) -> None:
        old_tab = self.childs[f"{self._focused_panel.title}_tab"]
        old_tab.style = self.tab_style | old_tab.style
        old_tab.style_focus = self.tab_hover_style | old_tab.style_focus

        tab = self.childs[f"{title}_tab"]
        tab.style = self.tab_focus_style | tab.style
        tab.style_focus = self.tab_focus_style | tab.style_focus

        self._focused_panel.style.display = tcp_style.Display.NONE
        new_panel = self.childs[f"{title}_panel"]
        self._focused_panel = new_panel
        self._focused_panel.style.display = tcp_style.Display.INITIAL

    def base_drawing(self) -> None:
        self.console.clear(bg=self.style.bg_color, fg=self.style.fg_color)
        self.console.ch[3, :] = 205


class ViewPanel(canvas.Canvas):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title = "VIEW"


class EditPanel(canvas.Canvas):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title = "EDIT"

        label = ["Name", "Function", "Symbol", "Color"]

        style_tpl = dict(x=max(len(e) for e in label) + 2, width=1.,
                         bg_color=tcod.Color(220, 220, 220),
                         fg_color=tcod.Color(20, 20, 20))
        name_style = {**style_tpl, **dict(y=1)}
        fun_style = {**style_tpl, **dict(y=3)}
        symbol_style = {**style_tpl, **dict(y=5)}
        color_style = {**style_tpl, **dict(y=7)}

        fname = widgets.InputField("field_name", max_len=3, style=name_style)
        ffun = widgets.InputField("field_fun", style=fun_style)
        fsymbol = widgets.InputField("field_symbol", max_len=1,
                                     style=symbol_style)
        fcolor = widgets.InputField("field_color", style=color_style)

        style_tpl = dict(origin=tcp_style.Origin.TOP_RIGHT,
                         outbound=tcp_style.Outbound.PARTIAL,
                         border=tcp_style.Border.EMPTY)
        delete_style = {**style_tpl, **dict(x=-9, y=10,
                                            bg_color=(160, 40, 40))}
        badd_style = {**style_tpl, **dict(x=-1, y=10,
                                          bg_color=(40, 160, 40))}

        bdelete = widgets.Button("Delete", name="button_delete",
                                 style=delete_style,
                                 style_focus=dict(bg_color=(180, 60, 60)))
        badd_mod = widgets.Button("Add", name="button_addmod",
                                  style=badd_style,
                                  style_focus=dict(bg_color=(60, 180, 60)))

        self.childs.add(fname, ffun, fsymbol, fcolor, bdelete, badd_mod)

    @property
    def edit_values(self) -> Tuple[str, str, str, str]:
        c = self.childs
        return (c["field_name"].value, c["field_fun"].value,
                c["field_symbol"].value, c["field_color"].value)

    @edit_values.setter
    def edit_values(self, values: Tuple[str, str, str, str]) -> None:
        c = self.childs
        # check for max_len maybe...
        c["field_name"].value = values[0]
        c["field_fun"].value = values[1]
        c["field_symbol"].value = values[2]
        c["field_color"].value = values[3]

    def base_drawing(self) -> None:
        console = self.console
        console.clear(bg=self.style.bg_color, fg=self.style.fg_color)
        label = ["Name", "Function", "Symbol", "Color"]
        for i, e in enumerate(label):
            console.print(0, 1+2*i, e+":")

        console.print(0, len(label)*2 + 5, "."*self.geometry.content_width)


if __name__ == "__main__":
    main()
