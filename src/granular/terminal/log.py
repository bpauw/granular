# SPDX-License-Identifier: MIT

from typing import Annotated, Optional

import pendulum
import typer

from granular.model.entity_id import EntityId
from granular.model.entity_type import EntityType
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.context import CONTEXT_REPO
from granular.repository.id_map import ID_MAP_REPO
from granular.repository.log import LOG_REPO
from granular.service.log import create_log_for_entity
from granular.terminal.completion import complete_project, complete_tag
from granular.terminal.custom_typer import ContextAwareTyperGroup
from granular.terminal.parse import open_editor_for_text, parse_datetime, parse_id_list
from granular.time import now_utc
from granular.version.version import Version
from granular.view.terminal_dispatch import show_cached_dispatch
from granular.view.view.views import log as log_report

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
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    ref_task: Annotated[Optional[int], typer.Option("--ref-task", "-rt")] = None,
    ref_time_audit: Annotated[
        Optional[int], typer.Option("--ref-time-audit", "-rta")
    ] = None,
    ref_event: Annotated[Optional[int], typer.Option("--ref-event", "-re")] = None,
) -> None:
    """
    Add a log entry using an editor.
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    config = CONFIGURATION_REPO.get_config()

    # Validate that only one reference is provided
    reference_count = sum(
        [
            ref_task is not None,
            ref_time_audit is not None,
            ref_event is not None,
        ]
    )
    if reference_count > 1:
        raise ValueError("A log can only reference one entity at a time")

    # Determine reference_type and reference_id (convert synthetic_id to real_id)
    reference_type: Optional[str] = None
    reference_id: Optional[EntityId] = None

    if ref_task is not None:
        reference_type = EntityType.TASK
        reference_id = ID_MAP_REPO.get_real_id("tasks", ref_task)
    elif ref_time_audit is not None:
        reference_type = EntityType.TIME_AUDIT
        reference_id = ID_MAP_REPO.get_real_id("time_audits", ref_time_audit)
    elif ref_event is not None:
        reference_type = EntityType.EVENT
        reference_id = ID_MAP_REPO.get_real_id("events", ref_event)

    # Merge tags with active context
    log_tags = active_context["auto_added_tags"]
    if tags is not None:
        if log_tags is None:
            log_tags = tags
        else:
            log_tags += tags

    # Determine project: use provided project, or auto_added_project from context
    log_project = project
    if log_project is None and active_context["auto_added_project"] is not None:
        log_project = active_context["auto_added_project"]

    # Open editor to get log text
    text = open_editor_for_text()

    if not text:
        raise typer.Exit(0)

    if active_context["name"] is None:
        raise ValueError("context name cannot be None")

    log = create_log_for_entity(
        text=text,
        reference_type=reference_type,
        reference_id=reference_id,
        entity_project=log_project,
        entity_tags=log_tags,
        timestamp=timestamp,
        add_tags=None,  # Already merged above
        color=color,
    )

    id = LOG_REPO.save_new_log(log)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add log: {id}")

    new_log = LOG_REPO.get_log(id)

    log_report.single_log_report(active_context["name"], new_log)

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
            "-rT",
            help="accepts multiple tag options",
            autocompletion=complete_tag,
        ),
    ] = None,
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    ref_task: Annotated[Optional[int], typer.Option("--ref-task", "-rt")] = None,
    ref_time_audit: Annotated[
        Optional[int], typer.Option("--ref-time-audit", "-rta")
    ] = None,
    ref_event: Annotated[Optional[int], typer.Option("--ref-event", "-re")] = None,
    deleted: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--deleted",
            "-del",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    remove_project: Annotated[bool, typer.Option("--remove-project", "-rp")] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rtgs")] = False,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rcol")] = False,
    remove_timestamp: Annotated[
        bool, typer.Option("--remove-timestamp", "-rtms")
    ] = False,
    remove_reference: Annotated[
        bool, typer.Option("--remove-reference", "-rr")
    ] = False,
    remove_deleted: Annotated[bool, typer.Option("--remove-deleted", "-rdel")] = False,
    edit_text: Annotated[
        bool, typer.Option("--edit-text", "-e", help="Open editor to modify log text")
    ] = False,
) -> None:
    """
    Modify a log entry
    """
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Validate that only one reference is provided
    reference_count = sum(
        [
            ref_task is not None,
            ref_time_audit is not None,
            ref_event is not None,
        ]
    )
    if reference_count > 1:
        raise ValueError("A log can only reference one entity at a time")

    # Determine reference_type and reference_id (convert synthetic_id to real_id)
    reference_type: Optional[str] = None
    reference_id: Optional[EntityId] = None

    if ref_task is not None:
        reference_type = EntityType.TASK
        reference_id = ID_MAP_REPO.get_real_id("tasks", ref_task)
    elif ref_time_audit is not None:
        reference_type = EntityType.TIME_AUDIT
        reference_id = ID_MAP_REPO.get_real_id("time_audits", ref_time_audit)
    elif ref_event is not None:
        reference_type = EntityType.EVENT
        reference_id = ID_MAP_REPO.get_real_id("events", ref_event)

    # Process each log
    modified_logs = []
    for log_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("logs", log_id)

        # Handle tag modifications
        updated_tags = None
        if add_tags is not None or remove_tag_list is not None:
            log = LOG_REPO.get_log(real_id)
            current_tags = log["tags"] if log["tags"] is not None else []
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
            log = LOG_REPO.get_log(real_id)
            current_text = log["text"] if log["text"] is not None else ""
            text = open_editor_for_text(current_text)
            if text is None:
                typer.echo("Text editing cancelled")

        # Handle remove_reference flag
        remove_reference_id = remove_reference
        remove_reference_type = remove_reference

        LOG_REPO.modify_log(
            real_id,
            reference_id,
            reference_type,
            timestamp,
            text,
            project,
            updated_tags,
            color,
            deleted,
            remove_reference_id,
            remove_reference_type,
            remove_timestamp,
            False,  # remove_text - not used since text is edited via editor
            remove_project,
            remove_tags,
            remove_color,
            remove_deleted,
        )

        log = LOG_REPO.get_log(real_id)
        modified_logs.append(log)

    if config["use_git_versioning"]:
        log_ids = [str(lg["id"]) for lg in modified_logs]
        version.create_data_checkpoint(f"modify log(s): {', '.join(log_ids)}")

    assert active_context["name"] is not None
    for log in modified_logs:
        log_report.single_log_report(active_context["name"], log)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("delete, d", no_args_is_help=True)
def delete(id: str) -> None:
    """
    Delete a log entry
    """
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each log
    deleted_logs = []
    for log_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("logs", log_id)

        LOG_REPO.modify_log(
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

        log = LOG_REPO.get_log(real_id)
        deleted_logs.append(log)

    if config["use_git_versioning"]:
        log_ids = [str(lg["id"]) for lg in deleted_logs]
        version.create_data_checkpoint(f"delete log(s): {', '.join(log_ids)}")

    assert active_context["name"] is not None
    for log in deleted_logs:
        log_report.single_log_report(active_context["name"], log)

    if config["cache_view"]:
        show_cached_dispatch()
