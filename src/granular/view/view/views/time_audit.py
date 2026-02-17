# SPDX-License-Identifier: MIT

from typing import Optional, cast

import pendulum
from rich import box
from rich.console import Console
from rich.table import Table

from granular.model.entity_id import EntityId
from granular.model.log import Log
from granular.model.note import Note
from granular.model.time_audit import TimeAudit
from granular.repository.id_map import ID_MAP_REPO
from granular.time import (
    datetime_to_display_local_datetime_str_optional,
    now_utc,
)
from granular.view.view.util import format_tags, has_logs, has_notes
from granular.view.view.views.header import header


def time_audits_report(
    active_context: str,
    report_name: str,
    time_audits: list[TimeAudit],
    columns: list[str] = ["id", "has_logs", "has_notes", "description", "start", "end"],
    notes: list[Note] = [],
    logs: list[Log] = [],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    header(active_context, report_name)

    time_audits_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column != "id":
            time_audits_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            time_audits_table.add_column(column)

    # Track if duration column is present and collect durations for totals
    has_duration_column = "duration" in columns
    total_duration: Optional[pendulum.Duration] = None

    # Sort time_audits chronologically for adjacency detection
    # Filter out audits without start times
    chronological_audits = [ta for ta in time_audits if ta["start"] is not None]
    chronological_audits.sort(key=lambda ta: ta["start"])  # type: ignore[arg-type, return-value]

    # Build adjacency maps: for each time_audit id, find chronological prev/next
    prev_end_map: dict[EntityId, Optional[pendulum.DateTime]] = {}
    next_start_map: dict[EntityId, Optional[pendulum.DateTime]] = {}

    for i, audit in enumerate(chronological_audits):
        audit_id = audit["id"]
        if audit_id is None:
            continue
        # Find chronological previous audit's end time
        if i > 0:
            prev_end_map[audit_id] = chronological_audits[i - 1]["end"]
        # Find chronological next audit's start time
        if i < len(chronological_audits) - 1:
            next_start_map[audit_id] = chronological_audits[i + 1]["start"]

    for idx, time_audit in enumerate(time_audits):
        row = []
        audit_id = time_audit["id"]

        # Check if this is an open time audit (has start but no end)
        is_open = time_audit["start"] is not None and time_audit["end"] is None

        # Check if start time differs from chronological previous end time
        highlight_start = False
        if (
            time_audit["start"] is not None
            and audit_id is not None
            and audit_id in prev_end_map
        ):
            prev_end = prev_end_map[audit_id]
            if prev_end is not None:
                highlight_start = time_audit["start"] != prev_end

        # Check if end time differs from chronological next start time
        highlight_end = False
        if (
            time_audit["end"] is not None
            and audit_id is not None
            and audit_id in next_start_map
        ):
            next_start = next_start_map[audit_id]
            if next_start is not None:
                highlight_end = time_audit["end"] != next_start

        for column in columns:
            column_value = ""
            apply_style = False

            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id(
                        "time_audits", cast(EntityId, time_audit["id"])
                    )
                )
            elif column == "task_id":
                if time_audit["task_id"] is not None:
                    column_value = str(
                        ID_MAP_REPO.associate_id("tasks", time_audit["task_id"])
                    )
            elif column == "duration":
                # Calculate and format duration
                duration = __calculate_duration(time_audit)
                column_value = __format_duration(duration)
                # Add to total if duration is not None
                if duration is not None:
                    if total_duration is None:
                        total_duration = duration
                    else:
                        total_duration = total_duration + duration
            elif column == "tags":
                column_value = format_tags(time_audit["tags"])
            elif column == "has_notes":
                column_value = has_notes(time_audit["id"], "time_audit", notes)
            elif column == "has_logs":
                column_value = has_logs(time_audit["id"], "time_audit", logs)
            elif column == "start":
                if isinstance(time_audit["start"], pendulum.DateTime):
                    column_value = (
                        datetime_to_display_local_datetime_str_optional(
                            time_audit["start"]
                        )
                        or ""
                    )
                    apply_style = highlight_start
            elif column == "end":
                if isinstance(time_audit["end"], pendulum.DateTime):
                    column_value = (
                        datetime_to_display_local_datetime_str_optional(
                            time_audit["end"]
                        )
                        or ""
                    )
                    apply_style = highlight_end
            elif isinstance(time_audit[column], pendulum.DateTime):  # type: ignore[literal-required]
                column_value = (
                    datetime_to_display_local_datetime_str_optional(time_audit[column])  # type: ignore[literal-required]
                    or ""
                )
            elif time_audit[column] is not None:  # type: ignore[literal-required]
                column_value = str(time_audit[column])  # type: ignore[literal-required]

            # Apply italic for adjacency gaps (time doesn't match prev/next audit)
            if apply_style:
                column_value = f"[italic]{column_value}[/italic]"

            # Apply color markup if needed
            if use_color:
                # Apply entity color if set
                if time_audit["color"] is not None and time_audit["color"] != "":
                    column_value = (
                        f"[{time_audit['color']}]{column_value}[/{time_audit['color']}]"
                    )

            # Apply underline for open time audits
            if is_open:
                column_value = f"[underline]{column_value}[/underline]"

            row.append(column_value)
        time_audits_table.add_row(*row)

    # Add totals footer if duration column is present
    if has_duration_column:
        footer_row = []
        for column in columns:
            if column == "duration":
                footer_row.append(__format_duration(total_duration))
            else:
                footer_row.append("")
        time_audits_table.add_row(*footer_row, style="bold")

    console = Console()
    console.print(time_audits_table)


def single_time_audit_report(
    active_context: str,
    time_audit: TimeAudit,
    title: str = "single time audit",
    show_header: bool = True,
) -> None:
    if show_header:
        header(active_context, title)

    time_audit_table = Table(box=box.SIMPLE)
    time_audit_table.add_column("property")
    time_audit_table.add_column("value")

    time_audit_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("time_audits", cast(EntityId, time_audit["id"]))),
    )
    time_audit_table.add_row("description", time_audit["description"])
    time_audit_table.add_row("project", time_audit["project"])
    time_audit_table.add_row("tags", format_tags(time_audit["tags"]))
    time_audit_table.add_row("color", time_audit["color"])
    time_audit_table.add_row(
        "start", datetime_to_display_local_datetime_str_optional(time_audit["start"])
    )
    time_audit_table.add_row(
        "end", datetime_to_display_local_datetime_str_optional(time_audit["end"])
    )
    if time_audit["task_id"] is not None:
        time_audit_table.add_row(
            "task_id",
            str(ID_MAP_REPO.associate_id("tasks", time_audit["task_id"])),
        )
    else:
        time_audit_table.add_row("task_id", str(time_audit["task_id"] or ""))
    time_audit_table.add_row(
        "created",
        datetime_to_display_local_datetime_str_optional(time_audit["created"]),
    )
    time_audit_table.add_row(
        "updated",
        datetime_to_display_local_datetime_str_optional(time_audit["updated"]),
    )
    time_audit_table.add_row(
        "deleted",
        datetime_to_display_local_datetime_str_optional(time_audit["deleted"]),
    )

    console = Console()
    console.print(time_audit_table)


def active_time_audit_report(
    active_context: str,
    time_audit: Optional[TimeAudit],
    show_header: bool = True,
) -> None:
    if time_audit is None:
        if show_header:
            header(active_context, "active time_audit")
            print()
        print("no active time audit")
    else:
        single_time_audit_report(
            active_context,
            time_audit,
            title="active time audit",
            show_header=show_header,
        )


def __calculate_duration(time_audit: TimeAudit) -> Optional[pendulum.Duration]:
    """Calculate duration as end - start if both are present, or now - start for open audits."""
    if time_audit["start"] is not None:
        if time_audit["end"] is not None:
            return time_audit["end"] - time_audit["start"]
        else:
            # Open time audit: calculate duration from start to now
            return now_utc() - time_audit["start"]
    return None


def __format_duration(duration: Optional[pendulum.Duration]) -> str:
    """Format duration as HH:MM."""
    if duration is None:
        return ""
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"
