# SPDX-License-Identifier: MIT

from contextvars import ContextVar

_clear_ids: ContextVar[bool] = ContextVar("clear_ids", default=True)


def set_clear_ids(value: bool) -> None:
    _clear_ids.set(value)


def get_clear_ids() -> bool:
    return _clear_ids.get()
