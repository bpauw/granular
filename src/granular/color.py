# SPDX-License-Identifier: MIT

import random

# Color constant for completed tasks
COMPLETED_TASK_COLOR = "bright_black"

# Color constants for entity metadata in agenda/story views
TIME_AUDIT_META_COLOR = "cyan"
LOG_META_COLOR = "green"
NOTE_META_COLOR = "yellow"


def get_random_color() -> str:
    """Return a random color from the Rich color palette.

    These colors are chosen for good visibility in terminal displays.
    """
    colors = [
        "red",
        "green",
        "yellow",
        "blue",
        "magenta",
        "cyan",
        "bright_red",
        "bright_green",
        "bright_yellow",
        "bright_blue",
        "bright_magenta",
        "bright_cyan",
        "dark_orange",
        "purple",
        "deep_pink",
        "spring_green",
        "dark_violet",
        "gold",
        "orange",
        "pink",
    ]
    return random.choice(colors)
