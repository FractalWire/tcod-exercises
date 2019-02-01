import numpy as np
import tcod
import textwrap

COUNTRY_COLOR = {
    (236, 200, 77): "W. Europe",
    (113, 128, 168): "Vikings",
    (90, 180, 60): "Rest of the world",
    (208, 242, 252): "Mare Nostrum"
}

COLOR_RANGE = 10


def main():
    #dmouse = DeltaMouse(tcod.Mouse())
    width = height = 50
    root_console = init_root(width, height,
                             "Challenge 5: Cleaner Zoom, drag and tooltip")
    root_canvas = Canvas(console=root_console)

    map_canvas = Canvas(root_canvas, 5, 5, width-10, height-10)
    img_path = "data/img/map-of-europe-clipart.bmp"
    europa_map = ImageMap(img_path, map_canvas)

    mouse_events = [europa_map.on_mouse]
    key_events = []
    events = {"mouse": mouse_events, "key": key_events}

    tcod.sys_set_fps(60)
    while not tcod.console_is_window_closed():
        handle_events(events)
        root_canvas.update()
        tcod.console_flush()


def init_root(w, h, title):
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    tcod.console_set_custom_font(font, flags)
    return tcod.console_init_root(w, h, title)


def handle_events(events):
    key = tcod.Key()
    mouse = tcod.Mouse()
    evnt_masks = tcod.EVENT_KEY_PRESS | tcod.EVENT_MOUSE
    while tcod.sys_check_for_event(evnt_masks, key, mouse):
        if key.vk == tcod.KEY_ESCAPE:
            raise SystemExit()
        for m_evnt in events["mouse"]:
            m_evnt(mouse)


def update_tooltip():
    raise NotImplementedError()


def handle_zoom():
    raise NotImplementedError()


class Canvas:
    def __init__(self, parent=None, x=0, y=0, width=0, height=0, childs=None,
                 fg_alpha=1, bg_alpha=1, console=None):
        self._parent = parent
        if self._parent != None:
            self._parent.childs += [self]
        self.x = x
        self.y = y
        self.childs = childs if childs else list()
        self.console = console if console != None else tcod.console_new(
            width, height)
        self.fg_alpha = fg_alpha
        self.bg_alpha = bg_alpha
        self.updated = True
        self.visible = True

    @property
    def parent(self):
        return self._parent

    def blit(self):
        self.console.blit(self.parent.console, self.x,
                          self.y, width=self.console.width, height=self.console.height,
                          fg_alpha=self.fg_alpha, bg_alpha=self.bg_alpha)

    def update(self):
        if not self.visible:
            return False
        # Leaf
        if self.childs == []:
            r = self.updated
            self.updated = False
            return r

        # Node
        r = False
        for c in self.childs:
            r = r or c.update()
        if r:
            self.console.clear()
            for c in self.childs:
                c.blit()
            self.updated = False
        return r

    @property
    def abs_x(self):
        if self.parent == None:
            return self.x
        return self.x + self.parent.abs_x

    @property
    def abs_y(self):
        if self.parent == None:
            return self.y
        return self.y + self.parent.abs_y


class TooltipTcod:
    def __init__(self, value, x=0, y=0,
                 fg_color=tcod.white, bg_color=tcod.black,
                 fg_alpha=1, bg_alpha=0.7, max_width=-1, max_height=-1):
        self.value = value
        self.x = x
        self.y = y
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.fg_alpha = fg_alpha
        self.bg_alpha = bg_alpha
        self.max_width = max_width
        self.max_height = max_height

    def generate_console(self):
        if self.value == "":
            return tcod.console_new(0,0)
        lines = []
        width=height=0
        if self.max_width > 0:
            lines = textwrap.wrap(self.value, self.max_width)
            lines = [" "*((self.max_width-len(e)-1)//2)+e for e in lines]
            width = min(self.max_width,max(len(L) for L in lines))
        else:
            lines = [self.value]
            width = len(self.value)
        if self.max_height > 0:
            lines = lines[:self.max_height]
            height = min(self.max_height, len(lines))
        else :
            height = len(lines)
        width += 2
        height += 2

        console = tcod.console_new(width, height)
        if len(self.value) > 0:
            console.bg[:] = self.bg_color
            console.fg[:] = self.fg_color
            console.ch[[0, -1], :] = 196
            console.ch[:, [0, -1]] = 179
            console.ch[[[0, -1], [-1, 0]], [0, -1]] = [[218, 217], [192, 191]]

            for i, e in enumerate(lines):
                console.print_(1, i+1, e)

        return console

    def on_mouse(self, mouse):
        raise NotImplementedError()


class ImageMap:
    def __init__(self, path, canvas, off_x=0, off_y=0, scale=-1, angle=0,
                 blend=tcod.BKGND_SET):
        self.canvas = canvas
        self.img = tcod.image_load(path)
        self.scale = scale
        if scale == -1:
            width = self.canvas.console.width
            height = self.canvas.console.height
            self.scale = round(
                min(width/self.img.width, height/self.img.height), 2)
        self._off_x = 0
        self._off_y = 0
        self.angle = angle
        self.blend = blend
        self.clicked = False
        self.tooltip = TooltipTcod("")
        self.blit()

    # Property might just be unnecessary here...
    @property
    def off_x(self):
        return round(self._off_x * self.scale)

    @property
    def off_y(self):
        return round(self._off_y * self.scale)

    @off_x.setter
    def off_x(self, value):
        if not isinstance(value, int):
            raise TypeError("off_x must be an integer")
        self._off_x = round(value / self.scale)
        w = self.img.width
        if abs(self._off_x) >= w:
            self._off_x = (self._off_x//abs(self._off_x)) * w

    @off_y.setter
    def off_y(self, value):
        if not isinstance(value, int):
            raise TypeError("off_y must be an integer")
        self._off_y = round(value / self.scale)

        # Border limit, should be enhanced
        h = self.img.height
        if abs(self._off_y) >= h:
            self._off_y = (self._off_y//abs(self._off_y)) * h

    def on_mouse(self, mouse):
        dcx = dcy = dz = 0
        mcx = mouse.cx
        mcy = mouse.cy

        c = self.canvas
        m_rel_x = mcx-c.abs_x
        m_rel_y = mcy-c.abs_y
        m_in_canvas_x = 0 <= m_rel_x <= c.console.width-1
        m_in_canvas_y = 0 <= m_rel_y <= c.console.height-1

        m_on_map = m_in_canvas_x and m_in_canvas_y

        #I put that there due to a bug for now but it should be back in the next
        # if block once it is fixed
        # Zoom
        if mouse.wheel_up:
            dz = 0.01
        elif mouse.wheel_down:
            dz = -0.01

        if m_on_map:
            # Tooltip management
            bg = c.console.bg[m_rel_y,m_rel_x]
            country = ""
            for k, v in COUNTRY_COLOR.items():
                if all(bg[i]-COLOR_RANGE < k[i] < bg[i]+COLOR_RANGE for i in range(3)):
                    country = v
                    break
            self.tooltip = TooltipTcod(country, m_rel_x+2, m_rel_y)

            # Drag
            if mouse.lbutton:
                if self.clicked:
                    dcx = mouse.dcx
                    dcy = mouse.dcy

                self.clicked = m_on_map

        if dcx != 0:
            self.off_x += dcx  # watch out for property...
        if dcy != 0:
            self.off_y += dcy
        if dz != 0:
            self.scale = round(self.scale+dz, 2)
            if self.scale <= 0:
                self.scale = 0.01

        self.blit()

    def blit(self):
        self.canvas.console.clear()

        # map blitting
        canvas_w = self.canvas.console.width
        canvas_h = self.canvas.console.height
        img_x = canvas_w // 2 + self.off_x
        img_y = canvas_h // 2 + self.off_y
        self.img.blit(self.canvas.console, img_x, img_y, tcod.BKGND_SET,
                      self.scale, self.scale, self.angle)

        #tooltip blitting
        t = self.tooltip
        tooltip_con = t.generate_console()
        tooltip_con.blit(self.canvas.console, t.x, t.y,
                         fg_alpha=t.fg_alpha, bg_alpha=t.bg_alpha)

        self.canvas.updated = True


class DeltaMouse:
    def __init__(self, mouse):
        self.mouse = mouse
        self._pcx = mouse.cx
        self._pcy = mouse.cy
        self.dcx = 0
        self.dcy = 0
        self.plmb = False

    def update(self):
        self.dcx = self.mouse.cx - self._pcx
        self.dcy = self.mouse.cy - self._pcy
        self._pcy = self.mouse.cx
        self._pcy = self.mouse.cy
        self.plmb = self.mouse.lbutton


if __name__ == "__main__":
    main()
