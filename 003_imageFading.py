import numpy as np
import tcod
import math


def main():
    width = 96
    height = 52

    root = init_root(width, height, "Challenge 3: Console fading")

    canvas1 = tcod.console_new(width, height)
    canvas2 = tcod.console_new(width, height)

    img1 = tcod.image_load("data/img/map-of-europe-clipart.bmp")
    img1.blit(canvas2, width//2, height//2, tcod.BKGND_SET, 0.05, 0.05, 0)
    img2 = tcod.image_load("data/img/ISS027-E-6501_lrg.bmp")
    img2.blit(canvas1, width//2, height//2, tcod.BKGND_SET, 0.1, 0.1, 0)

    alpha1 = 1
    alpha2 = 0

    tempo = 5000  # in milliseconds

    while not tcod.console_is_window_closed():
        root.clear()
        canvas1.blit(root, 0, 0, 0, 0, width, height, alpha1, alpha1)
        canvas2.blit(root, 0, 0, 0, 0, width, height, alpha2, alpha2)

        tcod.console_flush()
        handle_key()

        theta = ((tcod.sys_elapsed_milli() * (math.pi)/tempo) %
                 tempo) % (math.pi)

        alpha1 = abs(math.sin(theta))
        alpha2 = abs(math.cos(theta))


def init_root(w, h, title):
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    tcod.console_set_custom_font(font, flags)
    tcod.sys_set_fps(60)
    return tcod.console_init_root(w, h, title)


def handle_key():
    key = tcod.Key()
    evnt_mask = tcod.EVENT_KEY_PRESS
    while tcod.sys_check_for_event(evnt_mask, key, None):
        if key.vk == tcod.KEY_ESCAPE:
            raise SystemExit()


if __name__ == "__main__":
    main()
