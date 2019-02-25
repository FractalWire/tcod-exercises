import tcod
import tcod.event
import tcodplus.canvas as canvas
import tcodplus.widgets as widgets
import tcodplus.style as tcp_style


def main():
    width = height = 50
    font = "data/fonts/dejavu10x10_gs_tc.png"
    root_canvas = canvas.RootCanvas(width, height,
                                    "Challenge 7 : Input box and button",
                                    font)

    style = tcp_style.Style(x=5, y=height-5, width=width-10,
                            height=5, bg_color=(20, 20, 20))
    input_canvas = canvas.Canvas(style=style)

    style = tcp_style.Style(x=1, y=.5, width=.45, height=3,
                            bg_color=(200, 200, 200), fg_color=(20, 20, 20))
    input_field = widgets.InputField(max_len=10, style=style)

    style = tcp_style.Style(x=.5, y=1, width=10, height=3,
                            bg_color=(200, 20, 20))
    button_canvas = widgets.Button("MyButton", style=style)

    root_canvas.childs.add(input_canvas)
    input_canvas.childs.add(input_field, button_canvas)

    tcod.sys_set_fps(60)
    while not tcod.console_is_window_closed():
        root_canvas.refresh()
        tcod.console_flush()
        handle_events(root_canvas)


def init_root(w, h, title):
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    tcod.console_set_custom_font(font, flags)
    return tcod.console_init_root(w, h, title)


def handle_events(root_canvas: canvas.RootCanvas) -> None:
    kbd_focus_changed = False
    for event in tcod.event.get():
        if event.type == "KEYDOWN" and event.sym == tcod.event.K_ESCAPE:
            raise SystemExit()
        elif event.type == "MOUSEMOTION" and not event.state:
            root_canvas.update_last_mouse_focused_offsprings(event)
        elif event.type == "KEYDOWN":
            if event.sym == tcod.event.K_TAB:
                kbd_focus_changed = root_canvas.cycle_bkwd_kbd_focus() \
                    if event.mod & tcod.event.KMOD_SHIFT \
                    else root_canvas.cycle_fwd_kbd_focus()

        if event.type in ("MOUSEMOTION", "MOUSEBUTTONDOWN",
                          "MOUSEBUTTONUP", "MOUSEWHEEL"):
            for c in root_canvas.last_mouse_focused_offsprings.focused.values():
                c.focus_dispatcher.dispatch(event)
        elif event.type in ("KEYDOWN", "KEYUP", "TEXTINPUT"):
            k_focused_offspring = root_canvas.last_kbd_focused_offspring
            if not kbd_focus_changed and k_focused_offspring is not None:
                k_focused_offspring.focus_dispatcher.dispatch(event)

        if event.type == "MOUSEBUTTONDOWN":
            root_canvas.update_kbd_focus()


if __name__ == "__main__":
    main()
