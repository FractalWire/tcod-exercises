import tcod.event
from tcodplus import event
from tcodplus import canvas
import abc


class IDrawable(abc.ABC):
    @abc.abstractmethod
    def draw(self, dest: 'canvas.Canvas') -> None:
        pass

class IFocusable(abc.ABC):
    @property
    @abc.abstractmethod
    def focus_dispatcher(self) -> 'event.CanvasDispatcher':
        pass


class IMouseFocusable(IFocusable):
    @abc.abstractmethod
    def ismousefocused(self, event: tcod.event.MouseMotion) -> bool:
        pass


class IKeyboardFocusable(IFocusable):
    @abc.abstractmethod
    def iskeyboardfocused(self) -> bool:
        pass

    @abc.abstractmethod
    def iskeyboardfocus_requested(self) -> bool:
        pass

    @abc.abstractmethod
    def request_kbd_focus(self) -> None:
        pass

    @abc.abstractmethod
    def change_kbd_focus(self, value) -> None:
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

