# SPDX-License-Identifier: MIT

import importlib
import pkgutil
from copy import deepcopy
from typing import Any, Callable

MIGRATIONS: dict[int, Callable[..., Any]] = {}


def migration[T, **P](version: int) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def wrapper(func: Callable[P, T]) -> Callable[P, T]:
        global MIGRATIONS
        MIGRATIONS[version] = func
        return func

    return wrapper


def __import_all_modules(package_name: str) -> None:
    package = importlib.import_module(package_name)

    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{package_name}.{modname}"
        importlib.import_module(full_module_name)


def register_migrations() -> None:
    __import_all_modules("granular.migrate.migrations")


def get_migrations() -> dict[int, Callable[[], None]]:
    global MIGRATIONS
    return deepcopy(MIGRATIONS)
