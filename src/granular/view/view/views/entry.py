# SPDX-License-Identifier: MIT

from typing import cast

from granular.model.entity_id import EntityId

from rich import box
from rich.console import Console
from rich.table import Table

from granular.model.entry import Entry
from granular.model.tracker import Tracker
from granular.repository.id_map import ID_MAP_REPO
from granular.time import datetime_to_display_local_datetime_str_optional
from granular.view.view.util import format_tags
from granular.view.view.views.header import header


def entries_view(
    active_context: str,
    tracker: Tracker,
    entries: list[Entry],
    columns: list[str] = ["id", "timestamp", "value"],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    """Display list of entries for a tracker."""
    header(active_context, f"entries for {tracker['name']}")

    entries_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column not in ("id",):
            entries_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            entries_table.add_column(column)

    for entry in entries:
        row = []
        for column in columns:
            column_value = ""
            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id("entries", cast(EntityId, entry["id"]))
                )
            elif column == "timestamp":
                column_value = (
                    datetime_to_display_local_datetime_str_optional(entry["timestamp"])
                    or ""
                )
            elif column == "value":
                if entry["value"] is not None:
                    column_value = str(entry["value"])
                    if tracker["unit"]:
                        column_value += f" {tracker['unit']}"
                elif tracker["value_type"] == "checkin":
                    column_value = "(checked)"
            elif column == "tags":
                column_value = format_tags(entry["tags"])
            elif entry.get(column) is not None:
                column_value = str(entry[column])  # type: ignore[literal-required]

            # Apply colors if enabled
            if use_color and entry["color"] is not None and entry["color"] != "":
                column_value = f"[{entry['color']}]{column_value}[/{entry['color']}]"

            row.append(column_value)
        entries_table.add_row(*row)

    console = Console()
    console.print(entries_table)


def single_entry_view(
    active_context: str,
    entry: Entry,
    tracker: Tracker,
) -> None:
    """Display detailed view of a single entry."""
    header(active_context, "entry")

    entry_table = Table(box=box.SIMPLE)
    entry_table.add_column("property")
    entry_table.add_column("value")

    entry_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("entries", cast(EntityId, entry["id"]))),
    )
    entry_table.add_row("tracker", tracker["name"])
    entry_table.add_row(
        "tracker_id",
        str(ID_MAP_REPO.associate_id("trackers", entry["tracker_id"])),
    )
    entry_table.add_row(
        "timestamp",
        datetime_to_display_local_datetime_str_optional(entry["timestamp"]) or "",
    )

    # Display value with unit if applicable
    if entry["value"] is not None:
        value_str = str(entry["value"])
        if tracker["unit"]:
            value_str += f" {tracker['unit']}"
        entry_table.add_row("value", value_str)
    elif tracker["value_type"] == "checkin":
        entry_table.add_row("value", "(checked)")
    else:
        entry_table.add_row("value", "")

    entry_table.add_row("project", entry["project"] or "")
    entry_table.add_row("tags", format_tags(entry["tags"]))
    entry_table.add_row("color", entry["color"] or "")
    entry_table.add_row(
        "deleted", datetime_to_display_local_datetime_str_optional(entry["deleted"])
    )
    entry_table.add_row(
        "updated", datetime_to_display_local_datetime_str_optional(entry["updated"])
    )

    console = Console()
    console.print(entry_table)
