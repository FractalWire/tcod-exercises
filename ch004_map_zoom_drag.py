import tcod


def main():
    width = height = 50
    root = init_root(width, height, "Challenge 4: Map zoom and drag")

    canvas = tcod.console_new(width, height)
    img = tcod.image_load("data/img/map-of-europe-clipart.bmp")
    img_x, img_y = width//2, height//2
    img_w, img_h = img.width, img.height
    scale = round(min(width/img_w, height/img_h), 2)

    lmb = mx = my = dx = dy = dz = 0
    off_x = off_y = 0
    while not tcod.console_is_window_closed():
        canvas.clear()
        img.blit(canvas, img_x, img_y, tcod.BKGND_SET, scale, scale, 0)
        canvas.blit(root)

        tcod.console_flush()

        val = handle_events(lmb, mx, my)
        if val:
            lmb, mx, my, dx, dy, dz = val
            off_x -= round(dx/scale)
            off_y -= round(dy/scale)
            scale = round(scale+dz, 2)
            if scale <= 0:
                scale = 0.01
            img_x = round(width//2 + off_x * scale, 2)
            img_y = round(height//2 + off_y * scale, 2)


def init_root(w, h, title):
    tcod.sys_set_fps(60)
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    tcod.console_set_custom_font(font, flags)
    return tcod.console_init_root(w, h, title)


def handle_events(lmb, prev_mx, prev_my):
    dx = dy = dz = 0
    key = tcod.Key()
    mouse = tcod.Mouse()
    evnt_masks = tcod.EVENT_KEY_PRESS | tcod.EVENT_MOUSE
    while tcod.sys_check_for_event(evnt_masks, key, mouse):
        if key.vk == tcod.KEY_ESCAPE:
            raise SystemExit()
        elif mouse.wheel_up:
            dz = 0.01
        elif mouse.wheel_down:
            dz = -0.01
        elif mouse.lbutton:
            if lmb:
                dx = prev_mx-mouse.cx
                dy = prev_my-mouse.cy
            lmb = True
        elif mouse.lbutton_pressed:
            lmb = False
    return (lmb, mouse.cx, mouse.cy, dx, dy, dz)


if __name__ == "__main__":
    main()
