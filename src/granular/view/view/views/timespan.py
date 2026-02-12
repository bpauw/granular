# SPDX-License-Identifier: MIT

from typing import cast

import pendulum
from rich import box
from rich.console import Console
from rich.table import Table

from granular.model.timespan import Timespan
from granular.repository.id_map import ID_MAP_REPO
from granular.time import datetime_to_display_local_date_str_optional
from granular.view.view.util import format_tags
from granular.view.view.views.header import header


def timespans_view(
    active_context: str,
    report_name: str,
    timespans: list[Timespan],
    columns: list[str] = ["id", "description", "start", "end"],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    header(active_context, report_name)

    timespans_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column != "id":
            timespans_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            timespans_table.add_column(column)

    for timespan in timespans:
        row = []
        for column in columns:
            column_value = ""
            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id("timespans", cast(int, timespan["id"]))
                )
            elif column == "tags":
                column_value = format_tags(timespan["tags"])
            elif isinstance(timespan[column], pendulum.DateTime):  # type: ignore[literal-required]
                column_value = (
                    datetime_to_display_local_date_str_optional(timespan[column])  # type: ignore[literal-required]
                    or ""
                )
            elif timespan[column] is not None:  # type: ignore[literal-required]
                column_value = str(timespan[column])  # type: ignore[literal-required]

            # Apply entity color if enabled and color is set
            if use_color and timespan["color"] is not None and timespan["color"] != "":
                column_value = (
                    f"[{timespan['color']}]{column_value}[/{timespan['color']}]"
                )

            row.append(column_value)
        timespans_table.add_row(*row)

    console = Console()
    console.print(timespans_table)


def single_timespan_view(active_context: str, timespan: Timespan) -> None:
    header(active_context, "timespan")

    timespan_table = Table(box=box.SIMPLE)
    timespan_table.add_column("property")
    timespan_table.add_column("value")

    timespan_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("timespans", cast(int, timespan["id"]))),
    )
    timespan_table.add_row("description", timespan["description"])
    timespan_table.add_row("project", timespan["project"])
    timespan_table.add_row("tags", format_tags(timespan["tags"]))
    timespan_table.add_row("color", timespan["color"])
    timespan_table.add_row(
        "start", datetime_to_display_local_date_str_optional(timespan["start"])
    )
    timespan_table.add_row(
        "end", datetime_to_display_local_date_str_optional(timespan["end"])
    )
    timespan_table.add_row(
        "created", datetime_to_display_local_date_str_optional(timespan["created"])
    )
    timespan_table.add_row(
        "updated", datetime_to_display_local_date_str_optional(timespan["updated"])
    )
    timespan_table.add_row(
        "completed", datetime_to_display_local_date_str_optional(timespan["completed"])
    )
    timespan_table.add_row(
        "not_completed",
        datetime_to_display_local_date_str_optional(timespan["not_completed"]),
    )
    timespan_table.add_row(
        "cancelled", datetime_to_display_local_date_str_optional(timespan["cancelled"])
    )
    timespan_table.add_row(
        "deleted", datetime_to_display_local_date_str_optional(timespan["deleted"])
    )

    console = Console()
    console.print(timespan_table)
