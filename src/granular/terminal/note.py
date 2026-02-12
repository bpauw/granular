# SPDX-License-Identifier: MIT

from typing import Annotated, Optional, cast

import pendulum
import typer

from granular.model.entity_type import EntityType
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.context import CONTEXT_REPO
from granular.repository.id_map import ID_MAP_REPO
from granular.repository.note import NOTE_REPO
from granular.template.note import get_note_template
from granular.terminal.completion import complete_project, complete_tag
from granular.terminal.custom_typer import ContextAwareTyperGroup
from granular.terminal.parse import (
    open_editor_for_text,
    parse_datetime,
    parse_id_list,
)
from granular.time import now_utc, python_to_pendulum_utc_optional
from granular.version.version import Version
from granular.view.terminal_dispatch import show_cached_dispatch
from granular.view.view.views import note as note_report

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


@app.command("add, a")
def add(
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            help="valid input: project.subproject",
            autocompletion=complete_project,
        ),
    ] = None,
    tags: Annotated[
        Optional[list[str]],
        typer.Option(
            "--tag",
            "-t",
            help="accepts multiple tag options",
            autocompletion=complete_tag,
        ),
    ] = None,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, now, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    color: Annotated[
        Optional[str],
        typer.Option(
            "--color",
            "-c",
            help="valid inputs: red, green, blue, yellow, magenta, cyan, etc.",
        ),
    ] = None,
    ref_task: Annotated[Optional[int], typer.Option("--ref-task", "-rt")] = None,
    ref_time_audit: Annotated[
        Optional[int], typer.Option("--ref-time-audit", "-rta")
    ] = None,
    ref_event: Annotated[Optional[int], typer.Option("--ref-event", "-re")] = None,
    ref_timespan: Annotated[
        Optional[int], typer.Option("--ref-timespan", "-rts")
    ] = None,
    external: Annotated[
        bool,
        typer.Option("--external", "-x", help="Create external note in markdown file"),
    ] = False,
    folder: Annotated[
        Optional[str],
        typer.Option(
            "--folder", "-f", help="Note folder name (must be configured in config)"
        ),
    ] = None,
) -> None:
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    config = CONFIGURATION_REPO.get_config()

    # Validate that only one reference is provided
    reference_count = sum(
        [
            ref_task is not None,
            ref_time_audit is not None,
            ref_event is not None,
            ref_timespan is not None,
        ]
    )
    if reference_count > 1:
        raise ValueError("A note can only reference one entity at a time")

    # Determine reference_type and reference_id (convert synthetic_id to real_id)
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None

    if ref_task is not None:
        reference_type = EntityType.TASK
        reference_id = ID_MAP_REPO.get_real_id("tasks", ref_task)
    elif ref_time_audit is not None:
        reference_type = EntityType.TIME_AUDIT
        reference_id = ID_MAP_REPO.get_real_id("time_audits", ref_time_audit)
    elif ref_event is not None:
        reference_type = EntityType.EVENT
        reference_id = ID_MAP_REPO.get_real_id("events", ref_event)
    elif ref_timespan is not None:
        reference_type = EntityType.TIMESPAN
        reference_id = ID_MAP_REPO.get_real_id("timespans", ref_timespan)

    # Open editor for note text
    text = open_editor_for_text()
    if text is None:
        typer.echo("Note creation cancelled (no text provided)")
        return

    note_tags = active_context["auto_added_tags"]
    if tags is not None:
        if note_tags is None:
            note_tags = tags
        else:
            note_tags += tags

    # Determine project: use provided project, or auto_added_project from context
    note_project = project
    if note_project is None and active_context["auto_added_project"] is not None:
        note_project = active_context["auto_added_project"]

    note = get_note_template()
    note["reference_id"] = reference_id
    note["reference_type"] = reference_type
    note["timestamp"] = python_to_pendulum_utc_optional(timestamp)
    note["project"] = note_project
    note["tags"] = note_tags
    note["text"] = text
    note["color"] = color

    # Handle external note
    external_filename = None
    note_folder_name = None

    # Determine if creating external note
    should_create_external = external or config.get("external_notes_by_default", False)

    if should_create_external:
        # Resolve folder
        try:
            folder_config = NOTE_REPO._resolve_note_folder(
                config, active_context, folder
            )
            note_folder_name = folder_config["name"]
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

        # Prompt for filename
        external_filename = typer.prompt("Enter filename (without extension)")

    id = NOTE_REPO.save_new_note(note, external_filename, note_folder_name)

    if config["use_git_versioning"]:
        # Truncate text for commit message
        text_preview = text[:50] + "..." if len(text) > 50 else text
        version.create_data_checkpoint(f"add note: {id}: {text_preview}")

    new_note = NOTE_REPO.get_note(id)

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    note_report.single_note_report(active_context_name, new_note)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("modify, m", no_args_is_help=True)
def modify(
    id: str,
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            help="valid input: project.subproject",
            autocompletion=complete_project,
        ),
    ] = None,
    add_tags: Annotated[
        Optional[list[str]],
        typer.Option(
            "--add-tag",
            "-at",
            help="accepts multiple tag options",
            autocompletion=complete_tag,
        ),
    ] = None,
    remove_tag_list: Annotated[
        Optional[list[str]],
        typer.Option(
            "--remove-tag",
            "-rmt",
            help="accepts multiple tag options",
            autocompletion=complete_tag,
        ),
    ] = None,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    deleted: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--deleted",
            "-del",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    color: Annotated[
        Optional[str],
        typer.Option(
            "--color",
            "-c",
            help="valid inputs: red, green, blue, yellow, magenta, cyan, etc.",
        ),
    ] = None,
    ref_task: Annotated[Optional[int], typer.Option("--ref-task", "-rt")] = None,
    ref_time_audit: Annotated[
        Optional[int], typer.Option("--ref-time-audit", "-rta")
    ] = None,
    ref_event: Annotated[Optional[int], typer.Option("--ref-event", "-re")] = None,
    ref_timespan: Annotated[
        Optional[int], typer.Option("--ref-timespan", "-rts")
    ] = None,
    edit_text: Annotated[
        bool, typer.Option("--edit-text", "-e", help="Open editor to modify note text")
    ] = False,
    remove_reference: Annotated[
        bool, typer.Option("--remove-reference", "-rr")
    ] = False,
    remove_timestamp: Annotated[
        bool, typer.Option("--remove-timestamp", "-rtms")
    ] = False,
    remove_project: Annotated[bool, typer.Option("--remove-project", "-rp")] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rtgs")] = False,
    remove_deleted: Annotated[bool, typer.Option("--remove-deleted", "-rdel")] = False,
    remove_text: Annotated[bool, typer.Option("--remove-text", "-rtx")] = False,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rc")] = False,
) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Validate that only one reference is provided
    reference_count = sum(
        [
            ref_task is not None,
            ref_time_audit is not None,
            ref_event is not None,
            ref_timespan is not None,
        ]
    )
    if reference_count > 1:
        raise ValueError("A note can only reference one entity at a time")

    # Determine reference_type and reference_id (convert synthetic_id to real_id)
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None

    if ref_task is not None:
        reference_type = EntityType.TASK
        reference_id = ID_MAP_REPO.get_real_id("tasks", ref_task)
    elif ref_time_audit is not None:
        reference_type = EntityType.TIME_AUDIT
        reference_id = ID_MAP_REPO.get_real_id("time_audits", ref_time_audit)
    elif ref_event is not None:
        reference_type = EntityType.EVENT
        reference_id = ID_MAP_REPO.get_real_id("events", ref_event)
    elif ref_timespan is not None:
        reference_type = EntityType.TIMESPAN
        reference_id = ID_MAP_REPO.get_real_id("timespans", ref_timespan)

    # Process each note
    modified_notes = []
    for note_id in ids:
        real_id: int = ID_MAP_REPO.get_real_id("notes", note_id)

        # Handle tag modifications
        updated_tags = None
        if add_tags is not None or remove_tag_list is not None:
            note = NOTE_REPO.get_note(real_id)
            current_tags = note["tags"] if note["tags"] is not None else []
            updated_tags = list(current_tags)

            if add_tags is not None:
                updated_tags.extend(add_tags)

            if remove_tag_list is not None:
                updated_tags = [
                    tag for tag in updated_tags if tag not in remove_tag_list
                ]

            # Set to None if empty, otherwise keep the list
            updated_tags = updated_tags if len(updated_tags) > 0 else None

        # Handle text editing
        text = None
        if edit_text:
            note = NOTE_REPO.get_note(real_id)
            current_text = note["text"] if note["text"] is not None else ""

            # Check if external note
            if note.get("external_file_path"):
                # Open the actual external file in editor
                import os
                import subprocess

                # Resolve absolute path
                absolute_path = NOTE_REPO._resolve_external_file_path(note, config)

                # Open editor on the actual file
                editor = os.environ.get("EDITOR", "nano")
                subprocess.run([editor, str(absolute_path)], check=True)

                # Don't set text - the file was edited directly
                # Repository will read it on next access
                text = None
            else:
                # Embedded note - use temp file as before
                text = open_editor_for_text(current_text)
                if text is None:
                    typer.echo("Text editing cancelled")

        # Handle remove_reference flag
        remove_reference_id = remove_reference
        remove_reference_type = remove_reference

        NOTE_REPO.modify_note(
            real_id,
            reference_id,
            reference_type,
            timestamp,
            deleted,
            updated_tags,
            project,
            text,
            color,
            remove_reference_id,
            remove_reference_type,
            remove_timestamp,
            remove_deleted,
            remove_tags,
            remove_project,
            remove_text,
            remove_color,
        )

        note = NOTE_REPO.get_note(real_id)
        modified_notes.append(note)

    if config["use_git_versioning"]:
        note_previews = [
            f"{n['id']}: {(n['text'][:50] + '...' if len(n['text']) > 50 else n['text']) if n['text'] is not None else ''}"
            for n in modified_notes
        ]
        version.create_data_checkpoint(f"modify note(s): {', '.join(note_previews)}")

    for note in modified_notes:
        note_report.single_note_report(active_context_name, note)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("delete, d", no_args_is_help=True)
def delete(id: str) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each note
    deleted_notes = []
    for note_id in ids:
        real_id: int = ID_MAP_REPO.get_real_id("notes", note_id)

        NOTE_REPO.modify_note(
            real_id,
            None,  # reference_id
            None,  # reference_type
            None,  # timestamp
            now_utc(),  # deleted
            None,  # tags
            None,  # project
            None,  # text
            None,  # color
            False,  # remove_reference_id
            False,  # remove_reference_type
            False,  # remove_timestamp
            False,  # remove_deleted
            False,  # remove_tags
            False,  # remove_project
            False,  # remove_text
            False,  # remove_color
        )

        note = NOTE_REPO.get_note(real_id)
        deleted_notes.append(note)

    if config["use_git_versioning"]:
        note_ids = [str(n["id"]) for n in deleted_notes]
        version.create_data_checkpoint(f"delete note(s): {', '.join(note_ids)}")

    for note in deleted_notes:
        note_report.single_note_report(active_context_name, note)

    if config["cache_view"]:
        show_cached_dispatch()
