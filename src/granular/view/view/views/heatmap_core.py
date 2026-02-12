# SPDX-License-Identifier: MIT

from typing import Any, Callable, Literal

import pendulum
from rich.text import Text

GranularityType = Literal["day", "week", "month"]


def build_heatmap_row(
    left_column_text: str,
    left_column_style: str,
    timeline_data: list[dict[str, Any]],
    time_slots: list[pendulum.DateTime],
    granularity: GranularityType,
    slot_widths: list[int],
    slots_to_show: set[int],
    left_column_width: int,
    get_symbol: Callable[[dict[str, Any], bool], tuple[str, str]],
) -> Text:
    """
    Build a heatmap row for any entity type.

    This is a generic function that builds a heatmap row with a left column (name/description)
    and a timeline visualization. The symbol and style for each slot is determined by
    the provided get_symbol callback.

    Args:
        left_column_text: Text to display in the left column
        left_column_style: Rich style for the left column
        timeline_data: List of slot data dicts from a timeline service function
        time_slots: List of time slots for the timeline
        granularity: "day", "week", or "month"
        slot_widths: List of widths for each slot
        slots_to_show: Set of indices for slots that should show headers
        left_column_width: Width of the left column
        get_symbol: Callback function (slot_data, is_future) -> (symbol, style)

    Returns:
        Rich Text object with the heatmap row
    """
    row = Text()

    # Format the left column
    left_col = left_column_text
    if len(left_col) > left_column_width:
        left_col = left_col[: left_column_width - 3] + "..."
    else:
        left_col = left_col.ljust(left_column_width)

    row.append(left_col, style=left_column_style)

    # Get current time for determining future slots
    now = pendulum.now("local")

    # Track if previous slot had a label (needed for proper spacing alignment)
    prev_slot_had_label = False

    for i, slot in enumerate(time_slots):
        width = slot_widths[i]
        current_slot_has_label = i in slots_to_show
        slot_data = timeline_data[i]

        # Determine background style for alternating day columns (only for day granularity)
        bg_style = ""
        if granularity == "day" and i % 2 == 1:
            bg_style = " on grey23"

        # Handle leading separator space if both current and previous slots have labels
        if current_slot_has_label and prev_slot_had_label:
            row.append(" ")
            width = width - 1  # Adjust width for the remaining content

        # Determine if this slot is in the future
        is_future = slot > now

        # Get symbol and style from callback
        symbol, symbol_style = get_symbol(slot_data, is_future)

        # Apply background style
        if bg_style and symbol_style:
            final_style = symbol_style + bg_style
        elif bg_style:
            final_style = bg_style
        else:
            final_style = symbol_style

        # Place symbol
        if final_style:
            row.append(symbol, style=final_style)
        else:
            row.append(symbol)

        # Fill remaining width with spaces
        if width > 1:
            if bg_style:
                row.append(" " * (width - 1), style=bg_style)
            else:
                row.append(" " * (width - 1))

        prev_slot_had_label = current_slot_has_label

    return row


def get_tracker_symbol(
    slot_data: dict[str, Any],
    is_future: bool,
    tracker_value_type: str,
    color: str,
) -> tuple[str, str]:
    """
    Get the symbol and style for a tracker heatmap slot.

    Args:
        slot_data: Data for this slot from get_tracker_timeline_data
        is_future: Whether this slot is in the future
        tracker_value_type: The tracker's value_type (checkin, quantitative, etc.)
        color: The tracker's color

    Returns:
        Tuple of (symbol, style)
    """
    if is_future:
        return ("-", "dim")

    if slot_data["has_entry"]:
        if tracker_value_type == "checkin":
            return ("X", color)
        else:
            intensity = slot_data["intensity"]
            if intensity <= 0:
                return (" ", "")
            elif intensity == 1:
                return (".", color)
            elif intensity == 2:
                return ("o", color)
            elif intensity == 3:
                return ("O", color)
            else:  # intensity >= 4
                return ("#", color)
    else:
        return (" ", "")


def get_tasks_symbol(
    slot_data: dict[str, Any],
    is_future: bool,
    color: str,
) -> tuple[str, str]:
    """
    Get the symbol and style for a tasks heatmap slot.

    Args:
        slot_data: Data for this slot from get_tasks_timeline_data
        is_future: Whether this slot is in the future
        color: The color to use for markers

    Returns:
        Tuple of (symbol, style)
    """
    if is_future:
        return ("-", "dim")

    if slot_data["has_entry"]:
        intensity = slot_data["intensity"]
        if intensity <= 0:
            return (" ", "")
        elif intensity == 1:
            return (".", color)
        elif intensity == 2:
            return ("o", color)
        elif intensity == 3:
            return ("O", color)
        else:  # intensity >= 4
            return ("#", color)
    else:
        return (" ", "")
