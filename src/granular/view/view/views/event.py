# SPDX-License-Identifier: MIT

from typing import cast

import pendulum
from rich import box
from rich.console import Console
from rich.table import Table

from granular.model.event import Event
from granular.model.log import Log
from granular.model.note import Note
from granular.repository.id_map import ID_MAP_REPO
from granular.time import datetime_to_display_local_datetime_str_optional
from granular.view.view.util import format_tags, has_logs, has_notes
from granular.view.view.views.header import header


def events_view(
    active_context: str,
    report_name: str,
    events: list[Event],
    columns: list[str] = ["id", "has_logs", "has_notes", "title", "start", "end"],
    notes: list[Note] = [],
    logs: list[Log] = [],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    header(active_context, report_name)

    events_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column != "id":
            events_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            events_table.add_column(column)

    for event in events:
        row = []
        for column in columns:
            column_value = ""
            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id("events", cast(int, event["id"]))
                )
            elif column == "tags":
                column_value = format_tags(event["tags"])
            elif column == "has_notes":
                column_value = has_notes(event["id"], "event", notes)
            elif column == "has_logs":
                column_value = has_logs(event["id"], "event", logs)
            elif isinstance(event[column], pendulum.DateTime):  # type: ignore[literal-required]
                column_value = (
                    datetime_to_display_local_datetime_str_optional(event[column])  # type: ignore[literal-required]
                    or ""
                )
            elif isinstance(event[column], bool):  # type: ignore[literal-required]
                column_value = str(event[column])  # type: ignore[literal-required]
            elif event[column] is not None:  # type: ignore[literal-required]
                column_value = str(event[column])  # type: ignore[literal-required]

            # Apply entity color if enabled and color is set
            if use_color and event["color"] is not None and event["color"] != "":
                column_value = f"[{event['color']}]{column_value}[/{event['color']}]"

            row.append(column_value)
        events_table.add_row(*row)

    console = Console()
    console.print(events_table)


def single_event_view(active_context: str, event: Event) -> None:
    header(active_context, "event")

    event_table = Table(box=box.SIMPLE)
    event_table.add_column("property")
    event_table.add_column("value")

    event_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("events", cast(int, event["id"]))),
    )
    event_table.add_row("title", event["title"])
    event_table.add_row("description", event["description"])
    event_table.add_row("location", event["location"])
    event_table.add_row("project", event["project"])
    event_table.add_row("tags", format_tags(event["tags"]))
    event_table.add_row("color", event["color"])
    event_table.add_row(
        "start", datetime_to_display_local_datetime_str_optional(event["start"])
    )
    event_table.add_row(
        "end", datetime_to_display_local_datetime_str_optional(event["end"])
    )
    event_table.add_row("all_day", str(event["all_day"]))
    event_table.add_row(
        "created", datetime_to_display_local_datetime_str_optional(event["created"])
    )
    event_table.add_row(
        "updated", datetime_to_display_local_datetime_str_optional(event["updated"])
    )
    event_table.add_row(
        "deleted",
        datetime_to_display_local_datetime_str_optional(event["deleted"]),
    )

    console = Console()
    console.print(event_table)
