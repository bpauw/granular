# SPDX-License-Identifier: MIT

from typing import Optional, cast

from granular.model.entity_id import EntityId

import pendulum
from rich import box
from rich.console import Console
from rich.table import Table

from granular.model.entry import Entry
from granular.model.tracker import Tracker
from granular.repository.id_map import ID_MAP_REPO
from granular.service.tracker import (
    get_tracker_status_for_date,
    get_tracker_summary,
)
from granular.time import datetime_to_display_local_date_str_optional
from granular.view.view.util import format_tags
from granular.view.view.views.header import header


def trackers_view(
    active_context: str,
    report_name: str,
    trackers: list[Tracker],
    columns: list[str] = ["id", "name", "entry_type", "value_type"],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    """Display list of trackers in a table."""
    header(active_context, report_name)

    trackers_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column not in ("id",):
            trackers_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            trackers_table.add_column(column)

    for tracker in trackers:
        row = []
        for column in columns:
            column_value = ""
            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id("trackers", cast(EntityId, tracker["id"]))
                )
            elif column == "tags":
                column_value = format_tags(tracker["tags"])
            elif column == "entry_type":
                column_value = tracker["entry_type"]
            elif column == "value_type":
                column_value = tracker["value_type"]
            elif column == "unit":
                column_value = tracker["unit"] or ""
            elif tracker.get(column) is not None:
                column_value = str(tracker[column])  # type: ignore[literal-required]

            # Apply colors if enabled
            if use_color and tracker["color"] is not None and tracker["color"] != "":
                column_value = (
                    f"[{tracker['color']}]{column_value}[/{tracker['color']}]"
                )

            row.append(column_value)
        trackers_table.add_row(*row)

    console = Console()
    console.print(trackers_table)


def single_tracker_view(
    active_context: str,
    tracker: Tracker,
) -> None:
    """Display detailed view of a single tracker."""
    header(active_context, "tracker")

    tracker_table = Table(box=box.SIMPLE)
    tracker_table.add_column("property")
    tracker_table.add_column("value")

    tracker_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("trackers", cast(EntityId, tracker["id"]))),
    )
    tracker_table.add_row("name", tracker["name"])
    tracker_table.add_row("description", tracker["description"] or "")
    tracker_table.add_row("entry_type", tracker["entry_type"])
    tracker_table.add_row("value_type", tracker["value_type"])
    tracker_table.add_row("unit", tracker["unit"] or "")
    tracker_table.add_row(
        "scale_min",
        str(tracker["scale_min"]) if tracker["scale_min"] is not None else "",
    )
    tracker_table.add_row(
        "scale_max",
        str(tracker["scale_max"]) if tracker["scale_max"] is not None else "",
    )
    tracker_table.add_row(
        "options", ", ".join(tracker["options"]) if tracker["options"] else ""
    )
    tracker_table.add_row("projects", format_tags(tracker["projects"]))
    tracker_table.add_row("tags", format_tags(tracker["tags"]))
    tracker_table.add_row("color", tracker["color"] or "")
    tracker_table.add_row(
        "archived", datetime_to_display_local_date_str_optional(tracker["archived"])
    )
    tracker_table.add_row(
        "deleted", datetime_to_display_local_date_str_optional(tracker["deleted"])
    )
    tracker_table.add_row(
        "updated", datetime_to_display_local_date_str_optional(tracker["updated"])
    )

    console = Console()
    console.print(tracker_table)


def tracker_today_view(
    active_context: str,
    trackers: list[Tracker],
    entries: list[Entry],
) -> None:
    """
    Display today's status for all trackers.

    Tracker          Type       Status    Value
    ─────────────────────────────────────────────
    Water intake     daily      ✓         3 glasses
    Mood             daily      ✓         3
    Caffeine         intra_day  2 entries 150mg total
    Exercise         weekly     ✓         (checked)
    Meditation       daily      -
    """
    header(active_context, "tracker-today")

    today = pendulum.today("local")
    tracker_table = Table(box=box.SIMPLE)
    tracker_table.add_column("id")
    tracker_table.add_column("tracker")
    tracker_table.add_column("type")
    tracker_table.add_column("status")
    tracker_table.add_column("value")

    for tracker in trackers:
        status = get_tracker_status_for_date(tracker, entries, today)

        tracker_id = str(
            ID_MAP_REPO.associate_id("trackers", cast(EntityId, tracker["id"]))
        )
        tracker_name = tracker["name"]
        entry_type = tracker["entry_type"]

        # Determine status display
        if status["has_entry"]:
            if tracker["entry_type"] == "intra_day" and status["entry_count"] > 1:
                status_str = f"{status['entry_count']} entries"
            else:
                status_str = "X"
        else:
            status_str = "-"

        # Determine value display
        value_str = ""
        if status["has_entry"]:
            if tracker["value_type"] == "checkin":
                value_str = "(checked)"
            elif tracker["value_type"] == "quantitative":
                if status["total_value"] is not None:
                    unit = tracker["unit"] or ""
                    if status["entry_count"] > 1:
                        value_str = (
                            f"{status['total_value']}{' ' + unit if unit else ''} total"
                        )
                    else:
                        value_str = f"{status['values'][0]}{' ' + unit if unit else ''}"
            elif tracker["value_type"] == "multi_select":
                if status["values"]:
                    value_str = ", ".join(str(v) for v in status["values"])

        # Apply color
        row_values = [tracker_id, tracker_name, entry_type, status_str, value_str]
        if tracker["color"] is not None and tracker["color"] != "":
            row_values = [
                f"[{tracker['color']}]{v}[/{tracker['color']}]" for v in row_values
            ]

        tracker_table.add_row(*row_values)

    console = Console()
    console.print(tracker_table)


def tracker_summary_view(
    active_context: str,
    tracker: Tracker,
    entries: list[Entry],
    start_date: Optional[pendulum.Date],
    end_date: Optional[pendulum.Date],
    days: int = 14,
) -> None:
    """
    Display summary statistics.

    Water intake - Summary (Dec 1 - Dec 14)

    Date         Value
    ─────────────────────
    Dec 14       3 glasses
    Dec 13       4 glasses
    Dec 12       2 glasses
    ...
    """
    # Determine date range
    if end_date is None:
        end_date = pendulum.today("local")
    if start_date is None:
        start_date = end_date.subtract(days=days - 1)

    header(active_context, "tracker-summary")

    summary = get_tracker_summary(tracker, entries, start_date, end_date)

    console = Console()
    console.print(
        f"\n[bold]{tracker['name']}[/bold] - Summary "
        f"({start_date.format('MMM D')} - {end_date.format('MMM D')})"
    )
    console.print()

    # Create table
    summary_table = Table(box=box.SIMPLE)
    summary_table.add_column("date")
    summary_table.add_column("value")

    # Iterate in reverse chronological order
    current_date = end_date
    while current_date >= start_date:
        date_str = current_date.to_date_string()
        date_entries = summary["entries_by_date"].get(date_str, [])

        value_str = ""
        if date_entries:
            if tracker["value_type"] == "checkin":
                value_str = "(checked)"
            elif tracker["value_type"] == "quantitative":
                total = sum(
                    float(e["value"])
                    for e in date_entries
                    if e["value"] is not None and isinstance(e["value"], (int, float))
                )
                unit = tracker["unit"] or ""
                value_str = f"{total}{' ' + unit if unit else ''}"
            elif tracker["value_type"] == "multi_select":
                values = [
                    str(e["value"]) for e in date_entries if e["value"] is not None
                ]
                value_str = ", ".join(values)
        else:
            value_str = "-"

        # Apply color
        date_display = current_date.format("MMM D ddd")
        if tracker["color"] is not None and tracker["color"] != "":
            date_display = f"[{tracker['color']}]{date_display}[/{tracker['color']}]"
            value_str = f"[{tracker['color']}]{value_str}[/{tracker['color']}]"

        summary_table.add_row(date_display, value_str)
        current_date = current_date.subtract(days=1)

    console.print(summary_table)

    # Print stats
    console.print()
    console.print(f"Total entries: {summary['total_entries']}")
    console.print(f"Days with entries: {summary['days_with_entries']}")
