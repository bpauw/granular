# SPDX-License-Identifier: MIT

from typing import Annotated, Optional

import pendulum
import typer

from granular.color import get_random_color
from granular.model.entity_id import EntityId
from granular.model.entity_type import EntityType
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.context import CONTEXT_REPO
from granular.repository.id_map import ID_MAP_REPO
from granular.repository.log import LOG_REPO
from granular.repository.note import NOTE_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.service.log import create_log_for_entity
from granular.template.note import get_note_template
from granular.template.time_audit import get_time_audit_template
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
from granular.view.view.views import log as log_report
from granular.view.view.views import note as note_report
from granular.view.view.views import time_audit as time_audit_report

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


@app.command("add, a", no_args_is_help=True)
def add(
    description: str,
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
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    start: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start",
            "-s",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    task_id: Annotated[Optional[int], typer.Option("--task-id", "-tid")] = None,
) -> None:
    """
    add a time audit
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    config = CONFIGURATION_REPO.get_config()

    # Convert task_id from synthetic to real if provided
    real_task_id = None
    if task_id is not None:
        real_task_id = ID_MAP_REPO.get_real_id("tasks", task_id)

    time_audit_tags = active_context["auto_added_tags"]
    if tags is not None:
        if time_audit_tags is None:
            time_audit_tags = tags
        else:
            time_audit_tags += tags

    # Determine project: use provided project, or auto_added_project from context
    time_audit_project = project
    if time_audit_project is None and active_context["auto_added_project"] is not None:
        time_audit_project = active_context["auto_added_project"]

    # Determine color: use provided color, or random if config enabled
    time_audit_color = color
    if time_audit_color is None and config["random_color_for_time_audits"]:
        time_audit_color = get_random_color()

    time_audit = get_time_audit_template()
    time_audit["description"] = description
    time_audit["project"] = time_audit_project
    time_audit["tags"] = time_audit_tags
    time_audit["color"] = time_audit_color
    time_audit["start"] = (
        python_to_pendulum_utc_optional(start) if start is not None else now_utc()
    )
    time_audit["end"] = python_to_pendulum_utc_optional(end)
    time_audit["task_id"] = real_task_id

    # Close any open time audits by setting their end time to the new start time
    all_time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    for existing_time_audit in all_time_audits:
        if (
            existing_time_audit["end"] is None
            and existing_time_audit["deleted"] is None
        ):
            TIME_AUDIT_REPO.modify_time_audit(
                existing_time_audit["id"],  # type: ignore[arg-type]
                None,
                None,
                None,
                None,
                None,
                time_audit["start"],
                None,
                None,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
            )

    id = TIME_AUDIT_REPO.save_new_time_audit(time_audit)
    new_time_audit = TIME_AUDIT_REPO.get_time_audit(id)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"add time audit: {id}: {new_time_audit['description']}"
        )

    assert active_context["name"] is not None
    time_audit_report.single_time_audit_report(active_context["name"], new_time_audit)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("modify, m", no_args_is_help=True)
def modify(
    id: str,
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
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
            "-rt",
            help="accepts multiple tag options",
            autocompletion=complete_tag,
        ),
    ] = None,
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    start: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--start",
            "-s",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    task_id: Annotated[Optional[int], typer.Option("--task-id", "-tid")] = None,
    deleted: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--deleted",
            "-del",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    remove_description: Annotated[
        bool, typer.Option("--remove-description", "-rd")
    ] = False,
    remove_project: Annotated[bool, typer.Option("--remove-project", "-rp")] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rts")] = False,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rcol")] = False,
    remove_start: Annotated[bool, typer.Option("--remove-start", "-rs")] = False,
    remove_end: Annotated[bool, typer.Option("--remove-end", "-re")] = False,
    remove_task_id: Annotated[bool, typer.Option("--remove-task-id", "-rtid")] = False,
    remove_deleted: Annotated[bool, typer.Option("--remove-deleted", "-rdel")] = False,
) -> None:
    """
    modify a time audit
    """
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Convert task_id from synthetic to real if provided
    real_task_id = None
    if task_id is not None:
        real_task_id = ID_MAP_REPO.get_real_id("tasks", task_id)

    # Process each time audit
    modified_time_audits = []
    for time_audit_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("time_audits", time_audit_id)

        # Handle tag modifications
        updated_tags = None
        if add_tags is not None or remove_tag_list is not None:
            time_audit = TIME_AUDIT_REPO.get_time_audit(real_id)
            current_tags = time_audit["tags"] if time_audit["tags"] is not None else []
            updated_tags = list(current_tags)

            if add_tags is not None:
                updated_tags.extend(add_tags)

            if remove_tag_list is not None:
                updated_tags = [
                    tag for tag in updated_tags if tag not in remove_tag_list
                ]

            # Set to None if empty, otherwise keep the list
            updated_tags = updated_tags if len(updated_tags) > 0 else None

        TIME_AUDIT_REPO.modify_time_audit(
            real_id,
            description,
            project,
            updated_tags,
            color,
            start,
            end,
            real_task_id,
            deleted,
            remove_description,
            remove_project,
            remove_tags,
            remove_color,
            remove_start,
            remove_end,
            remove_task_id,
            remove_deleted,
        )

        time_audit = TIME_AUDIT_REPO.get_time_audit(real_id)
        modified_time_audits.append(time_audit)

    if config["use_git_versioning"]:
        time_audit_descriptions = [
            f"{ta['id']}: {ta['description']}" for ta in modified_time_audits
        ]
        version.create_data_checkpoint(
            f"modify time audit(s): {', '.join(time_audit_descriptions)}"
        )

    assert active_context["name"] is not None
    for time_audit in modified_time_audits:
        time_audit_report.single_time_audit_report(active_context["name"], time_audit)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("delete, d", no_args_is_help=True)
def delete(id: str) -> None:
    """
    delete a time audit
    """
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each time audit
    deleted_time_audits = []
    for time_audit_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("time_audits", time_audit_id)

        TIME_AUDIT_REPO.modify_time_audit(
            real_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            now_utc(),
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
        )

        time_audit = TIME_AUDIT_REPO.get_time_audit(real_id)
        deleted_time_audits.append(time_audit)

    if config["use_git_versioning"]:
        time_audit_descriptions = [
            f"{ta['id']}: {ta['description']}" for ta in deleted_time_audits
        ]
        version.create_data_checkpoint(
            f"delete time audit(s): {', '.join(time_audit_descriptions)}"
        )

    assert active_context["name"] is not None
    for time_audit in deleted_time_audits:
        time_audit_report.single_time_audit_report(active_context["name"], time_audit)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("stop, s")
def stop() -> None:
    """
    if there is an active time audit, stop it
    """
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    # Find all open time audits
    all_time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    open_time_audits = [
        time_audit
        for time_audit in all_time_audits
        if time_audit["end"] is None and time_audit["deleted"] is None
    ]

    # Check that at most one time audit is open
    if len(open_time_audits) > 1:
        raise ValueError(
            f"Found {len(open_time_audits)} open time audits. At most one time audit should be open at a time."
        )

    # Check if there is an open time audit
    if len(open_time_audits) == 0:
        print("No time audit active")
        return

    # Close the open time audit
    open_time_audit = open_time_audits[0]
    TIME_AUDIT_REPO.modify_time_audit(
        open_time_audit["id"],  # type: ignore[arg-type]
        None,
        None,
        None,
        None,
        None,
        now_utc(),
        None,
        None,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    )

    # Get the updated time audit and display it
    closed_time_audit = TIME_AUDIT_REPO.get_time_audit(open_time_audit["id"])  # type: ignore[arg-type]

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"close time audit: {closed_time_audit['id']}: {closed_time_audit['description']}"
        )

    assert active_context["name"] is not None
    time_audit_report.single_time_audit_report(
        active_context["name"], closed_time_audit
    )

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("move-adjacent-start, mas", no_args_is_help=True)
def move_adjacent_start(
    id: int,
    start: Annotated[
        pendulum.DateTime,
        typer.Option(
            "--adjacent-start",
            "-s",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ],
) -> None:
    """
    move the start time of a time audit and adjust the end time of the previous adjacent audit
    """
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    real_id = ID_MAP_REPO.get_real_id("time_audits", id)

    # Move the start time and adjust adjacent audit
    modified_target, modified_previous = TIME_AUDIT_REPO.move_adjacent_start(
        real_id, start
    )

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"move adjacent start for time audit: {modified_target['id']}: {modified_target['description']}"
        )

    assert active_context["name"] is not None

    # Collect all affected audits and sort by start time
    affected_audits = [modified_target]
    if modified_previous is not None:
        affected_audits.append(modified_previous)

    # Sort by start time (ascending)
    affected_audits.sort(
        key=lambda a: a["start"] if a["start"] is not None else pendulum.DateTime.min
    )

    # Display all affected audits in order
    for audit in affected_audits:
        time_audit_report.single_time_audit_report(active_context["name"], audit)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("move-adjacent-end, mae", no_args_is_help=True)
def move_adjacent_end(
    id: int,
    end: Annotated[
        pendulum.DateTime,
        typer.Option(
            "--adjacent-end",
            "-e",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ],
) -> None:
    """
    move the end time of a time audit and adjust the start time of the next adjacent audit
    """
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    real_id = ID_MAP_REPO.get_real_id("time_audits", id)

    # Move the end time and adjust adjacent audit
    modified_target, modified_next = TIME_AUDIT_REPO.move_adjacent_end(real_id, end)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"move adjacent end for time audit: {modified_target['id']}: {modified_target['description']}"
        )

    assert active_context["name"] is not None

    # Collect all affected audits and sort by start time
    affected_audits = [modified_target]
    if modified_next is not None:
        affected_audits.append(modified_next)

    # Sort by start time (ascending)
    affected_audits.sort(
        key=lambda a: a["start"] if a["start"] is not None else pendulum.DateTime.min
    )

    # Display all affected audits in order
    for audit in affected_audits:
        time_audit_report.single_time_audit_report(active_context["name"], audit)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("log, lg", no_args_is_help=True)
def log(
    time_audit_id: int,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
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
) -> None:
    """
    Add a log entry for a time audit using an editor.
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    real_id = ID_MAP_REPO.get_real_id("time_audits", time_audit_id)
    config = CONFIGURATION_REPO.get_config()

    # Get the time audit
    time_audit = TIME_AUDIT_REPO.get_time_audit(real_id)

    # Open editor to get log text
    text = open_editor_for_text()

    if not text:
        raise typer.Exit(0)

    if active_context["name"] is None:
        raise ValueError("context name cannot be None")

    log_entry = create_log_for_entity(
        text=text,
        reference_type=EntityType.TIME_AUDIT,
        reference_id=real_id,
        entity_project=time_audit["project"],
        entity_tags=time_audit["tags"],
        timestamp=timestamp,
        add_tags=add_tags,
        color=None,
    )

    log_id = LOG_REPO.save_new_log(log_entry)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add log for time audit {real_id}: {log_id}")

    new_log = LOG_REPO.get_log(log_id)

    log_report.single_log_report(active_context["name"], new_log)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("note, nt", no_args_is_help=True)
def note(
    time_audit_id: int,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
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
    """
    Add a note for a time audit
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    real_id = ID_MAP_REPO.get_real_id("time_audits", time_audit_id)
    config = CONFIGURATION_REPO.get_config()

    # Get the time audit
    time_audit = TIME_AUDIT_REPO.get_time_audit(real_id)

    # Open editor for note text
    text = open_editor_for_text()
    if text is None:
        typer.echo("Note creation cancelled (no text provided)")
        return

    # Start with time audit tags
    note_tags = time_audit["tags"] if time_audit["tags"] is not None else []
    note_tags = list(note_tags)  # Make a copy

    # Add context tags if they're not already in the time audit tags
    if active_context["auto_added_tags"] is not None:
        for tag in active_context["auto_added_tags"]:
            if tag not in note_tags:
                note_tags.append(tag)

    # Add any additional tags from the command
    if add_tags is not None:
        for tag in add_tags:
            if tag not in note_tags:
                note_tags.append(tag)

    # Set to None if empty
    final_tags = note_tags if len(note_tags) > 0 else None

    # Create the note
    note_entry = get_note_template()
    note_entry["text"] = text
    note_entry["project"] = time_audit["project"]
    note_entry["tags"] = final_tags
    note_entry["timestamp"] = (
        python_to_pendulum_utc_optional(timestamp)
        if timestamp is not None
        else now_utc()
    )
    note_entry["reference_type"] = EntityType.TIME_AUDIT
    note_entry["reference_id"] = real_id

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

    note_id = NOTE_REPO.save_new_note(note_entry, external_filename, note_folder_name)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add note for time audit {real_id}: {note_id}")

    new_note = NOTE_REPO.get_note(note_id)

    if active_context["name"] is None:
        raise ValueError("context name cannot be None")

    note_report.single_note_report(active_context["name"], new_note)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("color, co")
def color() -> None:
    """Add random colors to all time audits with null colors."""
    from rich.console import Console

    version = Version()

    config = CONFIGURATION_REPO.get_config()
    console = Console()

    # Get all time audits
    all_time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    # Filter time audits with null color
    time_audits_without_color = [
        time_audit for time_audit in all_time_audits if time_audit["color"] is None
    ]

    if len(time_audits_without_color) == 0:
        console.print("[yellow]No time audits with null colors found.[/yellow]")
        return

    # Add random colors to time audits without color
    for time_audit in time_audits_without_color:
        TIME_AUDIT_REPO.modify_time_audit(
            time_audit["id"],  # type: ignore[arg-type]
            None,  # description
            None,  # project
            None,  # tags
            get_random_color(),  # color
            None,  # start
            None,  # end
            None,  # task_id
            None,  # deleted
            False,  # remove_description
            False,  # remove_project
            False,  # remove_tags
            False,  # remove_color
            False,  # remove_start
            False,  # remove_end
            False,  # remove_task_id
            False,  # remove_deleted
        )

    console.print(
        f"[green]Added random colors to {len(time_audits_without_color)} time audit(s).[/green]"
    )

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"add random colors to {len(time_audits_without_color)} time audit(s)"
        )

    if config["cache_view"]:
        show_cached_dispatch()
