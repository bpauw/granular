# SPDX-License-Identifier: MIT

from functools import wraps
from typing import Any, Callable, TypeVar

from granular import state as app_state
from granular.repository.id_map import ID_MAP_REPO

F = TypeVar("F", bound=Callable[..., Any])


def clear_id_map(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if app_state.get_clear_ids():
            ID_MAP_REPO.clear_ids()
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def clear_id_map_if_required() -> None:
    if app_state.get_clear_ids():
        ID_MAP_REPO.clear_ids()
