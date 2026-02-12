# SPDX-License-Identifier: MIT

from typing import cast

import pendulum
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from granular.model.log import Log
from granular.repository.id_map import ID_MAP_REPO
from granular.time import (
    datetime_to_display_local_date_str,
    datetime_to_display_local_datetime_str_optional,
)
from granular.view.view.util import format_tags
from granular.view.view.views.header import header


def logs_view(
    active_context: str,
    report_name: str,
    logs: list[Log],
    columns: list[str] = [
        "id",
        "timestamp",
        "reference_type",
        "reference_id",
        "project",
        "text",
    ],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    header(active_context, report_name)

    logs_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column not in ("id", "reference_id"):
            logs_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            logs_table.add_column(column)

    for log in logs:
        row = []
        for column in columns:
            column_value = ""
            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id("logs", cast(int, log["id"]))
                )
            elif column == "reference_id":
                if (
                    log["reference_id"] is not None
                    and log["reference_type"] is not None
                ):
                    column_value = str(
                        ID_MAP_REPO.associate_id(
                            log["reference_type"] + "s", log["reference_id"]
                        )
                    )
            elif column == "timestamp":
                column_value = (
                    datetime_to_display_local_datetime_str_optional(log["timestamp"])
                    or ""
                )
            elif column == "tags":
                column_value = format_tags(log["tags"])
            elif isinstance(log[column], pendulum.DateTime):  # type: ignore[literal-required]
                column_value = log[column].to_date_string()  # type: ignore[literal-required]
            elif log[column] is not None:  # type: ignore[literal-required]
                column_value = str(log[column])  # type: ignore[literal-required]

            # Apply colors if enabled
            if use_color and log["color"] is not None and log["color"] != "":
                column_value = f"[{log['color']}]{column_value}[/{log['color']}]"

            row.append(column_value)
        logs_table.add_row(*row)

    console = Console()
    console.print(logs_table)


def single_log_report(active_context: str, log: Log) -> None:
    header(active_context, "log")

    log_table = Table(box=box.SIMPLE)
    log_table.add_column("property")
    log_table.add_column("value")

    log_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("logs", cast(int, log["id"]))),
    )
    log_table.add_row("reference_type", log["reference_type"] or "")
    if log["reference_id"] is not None and log["reference_type"] is not None:
        log_table.add_row(
            "reference_id",
            str(
                ID_MAP_REPO.associate_id(
                    log["reference_type"] + "s", log["reference_id"]
                )
            ),
        )
    else:
        log_table.add_row("reference_id", str(log["reference_id"] or ""))
    log_table.add_row(
        "timestamp",
        datetime_to_display_local_datetime_str_optional(log["timestamp"]) or "",
    )
    log_table.add_row("project", log["project"] or "")
    log_table.add_row("tags", format_tags(log["tags"]))
    log_table.add_row("color", log["color"] or "")
    log_table.add_row("created", datetime_to_display_local_date_str(log["created"]))
    log_table.add_row(
        "deleted",
        datetime_to_display_local_datetime_str_optional(log["deleted"]) or "",
    )

    console = Console()
    console.print(log_table)

    # Display the log text in a panel
    if log["text"] is not None and log["text"] != "":
        console.print("\n")
        console.print(Panel(log["text"], title="Log Text", border_style="blue"))
