from __future__ import annotations
from typing import TYPE_CHECKING
import abc
import tcod.event

if TYPE_CHECKING:
    from tcodplus.canvas import Canvas
    from tcodplus.event import CanvasDispatcher


class IDrawable(abc.ABC):
    @property
    @abc.abstractmethod
    def force_redraw(self) -> bool:
        pass

    @property
    @force_redraw.setter
    def force_redraw(self, value: bool) -> None:
        pass

    @abc.abstractmethod
    def draw(self, dest: Canvas) -> None:
        pass

    @abc.abstractmethod
    def base_drawing(self, console: tcod.console.Console) -> None:
        pass


class IFocusable(abc.ABC):
    @property
    @abc.abstractmethod
    def focus_dispatcher(self) -> CanvasDispatcher:
        pass


class IMouseFocusable(IFocusable):
    @abc.abstractmethod
    def mousefocus(self, event: tcod.event.MouseMotion) -> bool:
        pass


class IKeyboardFocusable(IFocusable):
    @property
    @abc.abstractmethod
    def kbdfocus(self) -> bool:
        pass

    @kbdfocus.setter
    @abc.abstractmethod
    def kbdfocus(self, val: bool) -> None:
        pass

    @property
    @abc.abstractmethod
    def kbdfocus_requested(self) -> bool:
        pass

    @kbdfocus_requested.setter
    @abc.abstractmethod
    def kbdfocus_requested(self, val: bool) -> None:
        pass


class IUpdatable(abc.ABC):
    @property
    @abc.abstractmethod
    def should_update(self) -> bool:
        pass

    @should_update.setter
    @abc.abstractmethod
    def should_update(self, value: bool) -> None:
        pass

    @abc.abstractmethod
    def update(self) -> None:
        pass
