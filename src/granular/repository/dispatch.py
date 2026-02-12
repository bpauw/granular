# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Optional

from yaml import dump, load

try:
    from yaml import CDumper as Dumper  # noqa: F401
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.model.terminal_dispatch import (
    TerminalDispatchPersistence,
    TerminalView,
    TerminalViewParams,
)


class DispatchRepository:
    def __init__(self) -> None:
        self._dispatch: Optional[TerminalDispatchPersistence] = None
        self.is_dirty = False

    @property
    def dispatch(self) -> Optional[TerminalDispatchPersistence]:
        if self._dispatch is None:
            self.__load_data()
        return self._dispatch

    def __load_data(self) -> None:
        if configuration.DATA_DISPATCH_PATH.is_file():
            self._dispatch = load(
                configuration.DATA_DISPATCH_PATH.read_text(), Loader=Loader
            )

    def __save_data(self, dispatch: TerminalDispatchPersistence) -> None:
        configuration.DATA_DISPATCH_PATH.write_text(dump(dispatch, Dumper=Dumper))

    def flush(self) -> bool:
        if self._dispatch is not None and self.is_dirty:
            self.__save_data(self._dispatch)
            return True
        return False

    def save_dispatch(
        self, view_type: TerminalView, dispatch_data: TerminalViewParams
    ) -> None:
        self.is_dirty = True
        self._dispatch = {"view_type": view_type, "view_params": dispatch_data}

    def get_dispatch(self) -> Optional[tuple[TerminalView, TerminalViewParams]]:
        if self.dispatch is not None:
            return (
                deepcopy(self.dispatch["view_type"]),
                deepcopy(self.dispatch["view_params"]),
            )
        return None


DISPATCH_REPO = DispatchRepository()
