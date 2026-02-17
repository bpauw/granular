# SPDX-License-Identifier: MIT

from typing import cast

from granular.model.entity_id import EntityId

import pendulum
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from granular.model.note import Note
from granular.repository.id_map import ID_MAP_REPO
from granular.time import (
    datetime_to_display_local_date_str,
    datetime_to_display_local_datetime_str_optional,
)
from granular.view.view.util import format_tags
from granular.view.view.views.header import header


def notes_report(
    active_context: str,
    report_name: str,
    notes: list[Note],
    columns: list[str] = [
        "id",
        "timestamp",
        "reference_type",
        "reference_id",
        "project",
        "first_line",
        "tags",
        "external_file_path",
    ],
    use_color: bool = True,
    no_wrap: bool = False,
) -> None:
    header(active_context, report_name)

    notes_table = Table(box=box.SIMPLE)
    for column in columns:
        if no_wrap and column not in ("id", "reference_id"):
            notes_table.add_column(column, no_wrap=True, overflow="ellipsis")
        else:
            notes_table.add_column(column)

    for note in notes:
        row = []
        for column in columns:
            column_value = ""
            if column == "id":
                column_value = str(
                    ID_MAP_REPO.associate_id("notes", cast(EntityId, note["id"]))
                )
            elif column == "reference_id":
                if (
                    note["reference_id"] is not None
                    and note["reference_type"] is not None
                ):
                    column_value = str(
                        ID_MAP_REPO.associate_id(
                            note["reference_type"] + "s", note["reference_id"]
                        )
                    )
            elif column == "timestamp":
                column_value = (
                    datetime_to_display_local_datetime_str_optional(note["timestamp"])
                    or ""
                )
            elif column == "tags":
                column_value = format_tags(note["tags"])
            elif column == "first_line":
                if note["text"] is not None and note["text"] != "":
                    first_line = note["text"].split("\n")[0].strip()
                    column_value = first_line
            elif column == "external_file_path":
                column_value = note.get("external_file_path") or ""
            elif isinstance(note[column], pendulum.DateTime):  # type: ignore[literal-required]
                column_value = note[column].to_date_string()  # type: ignore[literal-required]
            elif note[column] is not None:  # type: ignore[literal-required]
                column_value = str(note[column])  # type: ignore[literal-required]

            row.append(column_value)
        notes_table.add_row(*row)

    console = Console()
    console.print(notes_table)


def single_note_report(active_context: str, note: Note) -> None:
    header(active_context, "note")

    note_table = Table(box=box.SIMPLE)
    note_table.add_column("property")
    note_table.add_column("value")

    note_table.add_row(
        "id",
        str(ID_MAP_REPO.associate_id("notes", cast(EntityId, note["id"]))),
    )
    note_table.add_row("reference_type", note["reference_type"] or "")
    if note["reference_id"] is not None and note["reference_type"] is not None:
        note_table.add_row(
            "reference_id",
            str(
                ID_MAP_REPO.associate_id(
                    note["reference_type"] + "s", note["reference_id"]
                )
            ),
        )
    else:
        note_table.add_row("reference_id", str(note["reference_id"] or ""))
    note_table.add_row(
        "timestamp",
        datetime_to_display_local_datetime_str_optional(note["timestamp"]) or "",
    )
    note_table.add_row("project", note["project"] or "")
    note_table.add_row("tags", format_tags(note["tags"]))
    note_table.add_row("color", note["color"] or "")
    note_table.add_row("external_file_path", note.get("external_file_path") or "")
    note_table.add_row("note_folder_name", note.get("note_folder_name") or "")
    note_table.add_row("created", datetime_to_display_local_date_str(note["created"]))
    note_table.add_row("updated", datetime_to_display_local_date_str(note["updated"]))
    note_table.add_row(
        "deleted",
        datetime_to_display_local_datetime_str_optional(note["deleted"]) or "",
    )

    console = Console()
    console.print(note_table)

    # Display the note text in a panel
    if note["text"] is not None and note["text"] != "":
        console.print("\n")
        # Use the note's color for the panel border if available
        border_style = note["color"] if note["color"] is not None else "blue"
        console.print(Panel(note["text"], title="Note Text", border_style=border_style))
