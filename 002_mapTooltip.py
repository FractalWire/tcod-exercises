import numpy as np
import tcod

country_color = {
    (236, 200, 77): "W. Europe",
    (113, 128, 168): "Vikings",
    (90, 180, 60): "Rest of the world",
    (208, 242, 252): "Mare Nostrum"
}

color_range = 10


def main():
    width = 90
    height = 70

    root = init_root(width, height)

    canvas = tcod.console_new(width, height)

    img_path = "data/img/map-of-europe-clipart.bmp"
    img = tcod.image_load(img_path)

    img_x, img_y = width//2, height//2
    img_scale = 0.1

    bg, country = (0, 0, 0), ""
    mx = my = 0
    while not tcod.console_is_window_closed():

        img.blit(canvas, img_x, img_y, tcod.BKGND_SET, img_scale, img_scale, 0)
        canvas.blit(root, 0, 0, 0, 0, width, height)

        add_label(root, mx+2, my, country)

        tcod.console_flush()
        val = handle_events(canvas)
        if val:
            mx, my, bg, country = val

        root.clear()


def add_label(dest, x, y, country_name):
    label_text = f"{country_name}"
    if len(label_text) > 0:
        label_width, label_height = len(label_text)+2, 3
        label = tcod.console_new(label_width, label_height)
        label.bg[:] = tcod.black
        label.fg[:] = tcod.Color(200, 200, 200)
        # label.ch[:] = ord("#")
        label.ch[[0, -1], :] = 196
        label.ch[:, [0, -1]] = 179
        label.ch[[[0, -1], [-1, 0]], [0, -1]] = [[218,217],[192,191]]

        label.print_(1, 1, label_text)
        label.blit(dest, x, y, 0, 0, label_width, label_height, 1, 0.7)
        label.clear()


def init_root(w, h):
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    tcod.console_set_custom_font(font, flags)
    return tcod.console_init_root(w, h, "Challenge 2 : interactive ASCII map", False)


def handle_events(canvas):
    key = tcod.Key()
    mouse = tcod.Mouse()
    evnt_mask = tcod.EVENT_KEY_PRESS | tcod.EVENT_MOUSE

    while tcod.sys_check_for_event(evnt_mask, key, mouse):
        if key.vk == tcod.KEY_ESCAPE:
            raise SystemExit()

        mx, my = mouse.cx, mouse.cy
        bg = canvas.bg[my, mx]
        country = "UNKNWON"
        for k, v in country_color.items():
            if all(bg[i]-color_range < k[i] < bg[i]+color_range for i in range(3)):
                country = v
                break
        return (mx, my, bg, country)


if __name__ == "__main__":
    main()
