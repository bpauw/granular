# SPDX-License-Identifier: MIT

from typing import cast

import pendulum
from rich import box
from rich.console import Console
from rich.table import Table

from granular.color import COMPLETED_TASK_COLOR
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.repository.id_map import ID_MAP_REPO
from granular.time import datetime_to_display_local_date_str_optional
from granular.view.view.util import (
    calculate_task_total_duration,
    format_tags,
    has_logs,
    has_notes,
    is_task_completed,
    render_duration,
    task_age,
    task_state,
)
from granular.view.view.views.header import header


def tasks_view(
    active_context: str,
    report_name: str,
    tasks: list[Task],
    columns: list[str] = [
        "id",
        "state",
        "age",
        "has_logs",
        "has_notes",
        "priority",
        "description",
    ],
    time_audits: list[TimeAudit] = [],
    notes: list[Note] = [],
    logs: list[Log] = [],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    header(active_context, report_name)

    tasks_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column not in ("id", "state"):
            tasks_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            tasks_table.add_column(column)

    for task in tasks:
        row = []
        for column in columns:
            column_value = ""
            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id("tasks", cast(int, task["id"]))
                )
            elif column == "state":
                column_value = task_state(task, tasks)
            elif column == "age":
                column_value = task_age(task)
            elif column == "actual":
                total_duration = calculate_task_total_duration(task["id"], time_audits)
                column_value = render_duration(total_duration) or ""
            elif column == "estimate":
                column_value = render_duration(task["estimate"]) or ""
            elif column == "tags":
                column_value = format_tags(task["tags"])
            elif column == "has_notes":
                column_value = has_notes(task["id"], "task", notes)
            elif column == "has_logs":
                column_value = has_logs(task["id"], "task", logs)
            elif isinstance(task[column], pendulum.DateTime):  # type: ignore[literal-required]
                column_value = task[column].to_date_string()  # type: ignore[literal-required]
            elif task[column] is not None:  # type: ignore[literal-required]
                column_value = str(task[column])  # type: ignore[literal-required]

            # Apply colors if enabled
            if use_color:
                # Apply dark grey color to completed tasks
                if is_task_completed(task):
                    column_value = f"[{COMPLETED_TASK_COLOR}]{column_value}[/{COMPLETED_TASK_COLOR}]"
                # Apply entity color if set and task is not completed
                elif task["color"] is not None and task["color"] != "":
                    column_value = f"[{task['color']}]{column_value}[/{task['color']}]"

            row.append(column_value)
        tasks_table.add_row(*row)

    console = Console()
    console.print(tasks_table)


def single_task_view(
    active_context: str,
    task: Task,
    time_audits: list[TimeAudit] = [],
) -> None:
    header(active_context, "task")

    task_table = Table(box=box.SIMPLE)
    task_table.add_column("property")
    task_table.add_column("value")

    task_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("tasks", cast(int, task["id"]))),
    )
    if task["cloned_from_id"] is not None:
        task_table.add_row(
            "cloned_from_id",
            str(ID_MAP_REPO.associate_id("tasks", task["cloned_from_id"])),
        )
    else:
        task_table.add_row("cloned_from_id", str(task["cloned_from_id"] or ""))
    task_table.add_row("description", task["description"])
    task_table.add_row("project", task["project"])
    task_table.add_row("tags", format_tags(task["tags"]))
    task_table.add_row("priority", str(task["priority"] or ""))
    task_table.add_row("estimate", render_duration(task["estimate"]))

    # Add actual time spent
    total_duration = calculate_task_total_duration(task["id"], time_audits)
    task_table.add_row("actual", render_duration(total_duration) or "")

    task_table.add_row(
        "scheduled", datetime_to_display_local_date_str_optional(task["scheduled"])
    )
    task_table.add_row("due", datetime_to_display_local_date_str_optional(task["due"]))
    task_table.add_row(
        "started", datetime_to_display_local_date_str_optional(task["started"])
    )
    task_table.add_row(
        "completed", datetime_to_display_local_date_str_optional(task["completed"])
    )
    task_table.add_row(
        "not_completed",
        datetime_to_display_local_date_str_optional(task["not_completed"]),
    )
    task_table.add_row(
        "cancelled", datetime_to_display_local_date_str_optional(task["cancelled"])
    )
    task_table.add_row(
        "deleted", datetime_to_display_local_date_str_optional(task["deleted"])
    )
    task_table.add_row(
        "updated", datetime_to_display_local_date_str_optional(task["updated"])
    )

    console = Console()
    console.print(task_table)
