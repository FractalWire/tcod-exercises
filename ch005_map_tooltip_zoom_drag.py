import tcod
import tcod.event
import tcodplus.canvas as canvas
import tcodplus.widgets as widgets
import tcodplus.event as tcp_event
import tcodplus.style as tcp_style
import tcodplus.interfaces as interfaces

COUNTRY_COLOR = {
    (236, 200, 77): "W. Europe",
    (113, 128, 168): "Vikings",
    (90, 180, 60): "Rest of the world",
    (208, 242, 252): "Mare Nostrum"
}

COLOR_RANGE = 10


class ImageMap(canvas.Canvas, interfaces.IMouseFocusable,
               interfaces.IUpdatable):
    def __init__(self, path: str, off_x: int = 0, off_y: int = 0,
                 scale: float = -1, angle: float = 0,
                 blend: int = tcod.BKGND_SET, **kwargs) -> None:
        super().__init__(**kwargs)

        self.img = tcod.image_load(path)
        self.scale = scale
        self._off_x = 0
        self._off_y = 0
        self.angle = angle
        self.blend = blend
        self.console = None

        def ev_mousewheel(event: tcod.event.MouseWheel) -> None:
            # zoom
            dz = 0
            if event.y > 0 and not event.flipped:
                dz = self.scale
            else:
                dz = -self.scale / 2
            if dz != 0:
                self.scale = round(self.scale+dz, 2)
                if self.scale <= 0:
                    self.scale = 0.01
            self.should_update = True

        def ev_mousemotion(event: tcod.event.MouseMotion) -> None:
            # Drag
            dcx = dcy = 0
            if event.state & tcod.event.BUTTON_LMASK:
                dcx, dcy = event.tile_motion

            if dcx != 0:
                self.off_x += dcx  # watch out for property...
            if dcy != 0:
                self.off_y += dcy
            self.should_update = True

        self._mouse_dispatcher = tcp_event.CanvasDispatcher()
        self._mouse_dispatcher.ev_mousewheel += [ev_mousewheel]
        self._mouse_dispatcher.ev_mousemotion += [ev_mousemotion]

        self._should_update = False

    @property
    def should_update(self) -> bool:
        return self._should_update

    @should_update.setter
    def should_update(self, value: bool) -> None:
        self._should_update = value

    @property
    def off_x(self) -> int:
        return round(self._off_x * self.scale)

    @property
    def off_y(self) -> int:
        return round(self._off_y * self.scale)

    @off_x.setter
    def off_x(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("off_x must be an integer")
        self._off_x = round(value / self.scale)

        w = self.img.width
        if abs(self._off_x) >= w:
            self._off_x = (self._off_x//abs(self._off_x)) * w

    @off_y.setter
    def off_y(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("off_y must be an integer")
        self._off_y = round(value / self.scale)

        # Border limit, should be improved
        h = self.img.height
        if abs(self._off_y) >= h:
            self._off_y = (self._off_y//abs(self._off_y)) * h

    def mousefocus(self, event: tcod.event.MouseMotion) -> bool:
        mcx, mcy = event.tile
        abs_x, abs_y, _, _, width, height = self.geometry
        m_rel_x = mcx - abs_x
        m_rel_y = mcy - abs_y
        is_in_x = (0 <= m_rel_x <= width-1)
        is_in_y = (0 <= m_rel_y <= height-1)
        return is_in_x and is_in_y

    @property
    def focus_dispatcher(self) -> tcp_event.CanvasDispatcher:
        return self._mouse_dispatcher

    def update_geometry(self) -> bool:
        up = super().update_geometry()

        width, height = self.geometry.width, self.geometry.height
        if self.scale == -1:
            self.scale = round(
                min(width/self.img.width, height/self.img.height), 2)

        return up

    def update(self) -> None:
        self.console.clear()
        # map blitting
        img_x = self.geometry.width // 2 + self.off_x
        img_y = self.geometry.height // 2 + self.off_y
        self.img.blit(self.console, img_x, img_y, self.blend,
                      self.scale, self.scale, self.angle)

        self.should_update = False


def init_root(w: int, h: int, title: str) -> tcod.console.Console:
    font = "data/fonts/dejavu10x10_gs_tc.png"
    flags = tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD
    tcod.console_set_custom_font(font, flags)
    return tcod.console_init_root(w, h, title)


def handle_events(root: canvas.RootCanvas) -> None:
    for event in tcod.event.get():
        if event.type == "KEYDOWN" and event.sym == tcod.event.K_ESCAPE:
            raise SystemExit()
        root.handle_focus_event(event)
        # elif event.type == "MOUSEMOTION" and not event.state:
        #     canvas._update_mouse_focus(event)

        # if event.type in ("MOUSEMOTION", "MOUSEBUTTONDOWN",
        #                   "MOUSEBUTTONUP", "MOUSEWHEEL"):
        #     for c in canvas.mouse_focused_offsprings().focused.values():
        #         c.focus_dispatcher.dispatch(event)
        # canvas.unfocused_events(event)


def map_tooltip_event(img_map: ImageMap, tooltip: widgets.Tooltip,
                      event: tcod.event.MouseMotion) -> None:
    if event.type in ["MOUSEMOTION", "MOUSEFOCUSGAIN"] and not event.state:
        mcx, mcy = event.tile
        m_rel_x = mcx - img_map.geometry.abs_x
        m_rel_y = mcy - img_map.geometry.abs_y

        bg = img_map.console.bg[m_rel_y, m_rel_x]
        country = ""
        for k, v in COUNTRY_COLOR.items():
            if all(bg[i]-COLOR_RANGE < k[i] < bg[i]+COLOR_RANGE for i in range(3)):
                country = v
                break

        tooltip.style.x = mcx
        tooltip.style.y = mcy
        tooltip.value = country
        # tooltip.should_update = True
    else:  # MOUSEFOCUSELOST
        tooltip.value = ""
        # tooltip.should_update = False


def main() -> None:
    width = height = 70
    font = "data/fonts/dejavu10x10_gs_tc.png"
    root_canvas = canvas.RootCanvas(width, height,
                                    "Challenge 5: Cleaner Zoom, drag and tooltip",
                                    font)

    img_path = "data/img/map-of-europe-clipart.bmp"
    style = tcp_style.Style(x=0, y=0, width=1., height=.5)
    europa_map = ImageMap(img_path, style=style)

    img_path = "data/img/ISS027-E-6501_lrg.bmp"
    style = tcp_style.Style(x=.5, y=.5, width=.5, height=.5)
    iss_img = ImageMap(img_path, style=style)

    img_path = "data/img/mountain.bmp"
    style = tcp_style.Style(x=0, y=.5, width=.5, height=.5)
    mountain_img = ImageMap(img_path, style=style)

    style = tcp_style.Style(max_width=10, outbound=tcp_style.Outbound.STRICT,
                            border=tcp_style.Border.DASHED, fg_color=tcod.white)
    tooltip = widgets.Tooltip(style=style, delay=0.3, fade_duration=0.3)

    europa_map.focus_dispatcher.ev_mousemotion += [
        lambda ev: map_tooltip_event(europa_map, tooltip, ev)]
    europa_map.focus_dispatcher.ev_mousefocusgain += [
        lambda ev: map_tooltip_event(europa_map, tooltip, ev)]
    europa_map.focus_dispatcher.ev_mousefocuslost += [
        lambda ev: map_tooltip_event(europa_map, tooltip, ev)]
    europa_map.focus_dispatcher.ev_mousefocusgain += [
        lambda ev: print("focus gain")]
    europa_map.focus_dispatcher.ev_mousefocuslost += [
        lambda ev: print("focus lost")]

    # root_canvas.childs += map_canvas
    root_canvas.childs.add(europa_map, iss_img, mountain_img, tooltip)

    tcod.sys_set_fps(60)
    while not tcod.console_is_window_closed():
        handle_events(root_canvas)
        root_canvas.refresh()
        tcod.console_flush()


if __name__ == "__main__":
    main()
