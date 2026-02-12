# SPDX-License-Identifier: MIT

from typing import Optional

from rich import print
from rich.padding import Padding

from granular.view.state import get_show_header


def header(active_context: str, sub_header: Optional[str] = None) -> None:
    """Print the application header with context information.

    Args:
        active_context: The name of the active context
        sub_header: Optional sub-header text to display
    """
    # Check if headers should be shown
    if not get_show_header():
        return

    additional = ""
    if sub_header is not None:
        additional = f"[sandy_brown]{sub_header}[/sandy_brown]"
    active_context = f"[plum1]{active_context}[/plum1]"

    print(Padding("[dark_orange]granular[/dark_orange]", (1, 0, 0, 1)))
    print(Padding(additional, (0, 1)))
    print(Padding(active_context, (0, 1)))
