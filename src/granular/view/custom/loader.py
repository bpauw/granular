# SPDX-License-Identifier: MIT

from functools import partial
from typing import cast

from yaml import load

try:
    from yaml import CDumper as Dumper  # noqa: F401
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Loader  # type: ignore[assignment]


from granular import configuration
from granular.model.custom_view import (
    Views,
)
from granular.model.terminal_dispatch import TerminalView
from granular.terminal import custom_view
from granular.view.terminal_dispatch import dispatch


def load_custom_views() -> None:
    views_data = cast(
        Views, load(configuration.DATA_CUSTOM_VIEWS_PATH.read_text(), Loader=Loader)
    )

    for compound_view in views_data.get("custom_views", []):
        custom_view.app.command(compound_view["name"], help="")(
            partial(
                dispatch, TerminalView.CUSTOM_LOADER, {"compound_view": compound_view}
            )
        )
