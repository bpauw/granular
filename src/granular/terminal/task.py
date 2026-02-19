# SPDX-License-Identifier: MIT

from typing import Annotated, Optional, cast

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
from granular.repository.task import TASK_REPO
from granular.repository.time_audit import TIME_AUDIT_REPO
from granular.service.log import create_log_for_entity
from granular.template.note import get_note_template
from granular.template.task import get_task_template
from granular.template.time_audit import get_time_audit_template
from granular.terminal.completion import complete_project, complete_tag
from granular.terminal.custom_typer import ContextAwareTyperGroup
from granular.terminal.parse import (
    open_editor_for_text,
    parse_datetime,
    parse_id_list,
)
from granular.terminal.validate import validate_duration, validate_priority
from granular.time import (
    duration_from_str_optional,
    now_utc,
    python_to_pendulum_utc_optional,
)
from granular.version.version import Version
from granular.view.terminal_dispatch import show_cached_dispatch
from granular.view.view.views import log as log_report
from granular.view.view.views import note as note_report
from granular.view.view.views import task as task_report
from granular.view.view.views import time_audit as time_audit_report

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


@app.command("add, a", no_args_is_help=True)
def add(
    description: str,
    projects: Annotated[
        Optional[list[str]],
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
    priority: Annotated[
        Optional[int],
        typer.Option(
            "--priority",
            "-pr",
            callback=validate_priority,
            help="valid input: 1-5 (1=highest, 5=lowest)",
        ),
    ] = None,
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    estimate: Annotated[
        Optional[str],
        typer.Option(
            "--estimate", "-e", callback=validate_duration, help="valid input: HH:mm"
        ),
    ] = None,
    scheduled: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--scheduled",
            "-s",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, now, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    due: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--due",
            "-u",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, now, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    started: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--started",
            "-a",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, now, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    timespan_id: Annotated[Optional[int], typer.Option("--timespan-id", "-ts")] = None,
) -> None:
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    config = CONFIGURATION_REPO.get_config()

    task_tags = active_context["auto_added_tags"]
    if tags is not None:
        if task_tags is None:
            task_tags = tags
        else:
            task_tags += tags

    # Determine projects: merge context auto_added_projects with provided projects
    entity_projects = active_context["auto_added_projects"]
    if projects is not None:
        if entity_projects is None:
            entity_projects = projects
        else:
            entity_projects += projects

    # Determine color: use provided color, or random if config enabled
    task_color = color
    if task_color is None and config["random_color_for_tasks"]:
        task_color = get_random_color()

    task = get_task_template()
    task["description"] = description
    task["projects"] = entity_projects
    task["tags"] = task_tags
    task["priority"] = priority
    task["color"] = task_color
    task["estimate"] = duration_from_str_optional(estimate)
    task["scheduled"] = python_to_pendulum_utc_optional(scheduled)
    task["due"] = python_to_pendulum_utc_optional(due)
    task["started"] = python_to_pendulum_utc_optional(started)
    task["timespan_id"] = (
        ID_MAP_REPO.get_real_id("timespans", timespan_id)
        if timespan_id is not None
        else None
    )

    id = TASK_REPO.save_new_task(task)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add task: {id}: {description}")

    new_task = TASK_REPO.get_task(id)

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    task_report.single_task_view(active_context_name, new_task, time_audits)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("modify, m", no_args_is_help=True)
def modify(
    id: str,
    cloned_from_id: Annotated[
        Optional[int], typer.Option("--cloned-from-id", "-cfi")
    ] = None,
    timespan_id: Annotated[Optional[int], typer.Option("--timespan-id", "-ts")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
    add_projects: Annotated[
        Optional[list[str]],
        typer.Option(
            "--add-project",
            "-ap",
            autocompletion=complete_project,
            help="Add project (repeatable)",
        ),
    ] = None,
    remove_project_list: Annotated[
        Optional[list[str]],
        typer.Option(
            "--remove-project",
            "-rp",
            autocompletion=complete_project,
            help="Remove specific project (repeatable)",
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
    priority: Annotated[
        Optional[int],
        typer.Option(
            "--priority",
            "-pr",
            callback=validate_priority,
            help="valid input: 1-5 (1=highest, 5=lowest)",
        ),
    ] = None,
    estimate: Annotated[
        Optional[str],
        typer.Option(
            "--estimate", "-e", callback=validate_duration, help="valid input: HH:mm"
        ),
    ] = None,
    scheduled: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--scheduled",
            "-s",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    due: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--due",
            "-u",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    started: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--started",
            "-a",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    completed: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--completed",
            "-c",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    not_completed: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--not-completed",
            "-nc",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    cancelled: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--cancelled",
            "-ca",
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
    remove_cloned_from_id: Annotated[
        bool, typer.Option("--remove-cloned-from-id", "-rcfi")
    ] = False,
    remove_timespan_id: Annotated[
        bool, typer.Option("--remove-timespan-id", "-rts")
    ] = False,
    remove_description: Annotated[
        bool, typer.Option("--remove-description", "-rd")
    ] = False,
    remove_projects: Annotated[
        bool, typer.Option("--remove-projects", "-rpjs", help="Clear all projects")
    ] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rtgs")] = False,
    remove_priority: Annotated[bool, typer.Option("--remove-priority", "-rpr")] = False,
    remove_estimate: Annotated[bool, typer.Option("--remove-estimate", "-re")] = False,
    remove_scheduled: Annotated[
        bool, typer.Option("--remove-scheduled", "-rs")
    ] = False,
    remove_due: Annotated[bool, typer.Option("--remove-due", "-ru")] = False,
    remove_started: Annotated[bool, typer.Option("--remove-started", "-ra")] = False,
    remove_completed: Annotated[
        bool, typer.Option("--remove-completed", "-ro")
    ] = False,
    remove_not_completed: Annotated[
        bool, typer.Option("--remove-not-completed", "-rnc")
    ] = False,
    remove_cancelled: Annotated[
        bool, typer.Option("--remove-cancelled", "-rc")
    ] = False,
    remove_deleted: Annotated[bool, typer.Option("--remove-deleted", "-rdel")] = False,
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rcol")] = False,
) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each task
    modified_tasks = []
    for task_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("tasks", task_id)

        # Handle tag modifications
        updated_tags = None
        if add_tags is not None or remove_tag_list is not None:
            task = TASK_REPO.get_task(real_id)
            current_tags = task["tags"] if task["tags"] is not None else []
            updated_tags = list(current_tags)

            if add_tags is not None:
                updated_tags.extend(add_tags)

            if remove_tag_list is not None:
                updated_tags = [
                    tag for tag in updated_tags if tag not in remove_tag_list
                ]

            # Set to None if empty, otherwise keep the list
            updated_tags = updated_tags if len(updated_tags) > 0 else None

        # Handle project modifications
        updated_projects = None
        if add_projects is not None or remove_project_list is not None:
            task = TASK_REPO.get_task(real_id)
            current_projects = task["projects"] if task["projects"] is not None else []
            updated_projects = list(current_projects)

            if add_projects is not None:
                updated_projects.extend(add_projects)

            if remove_project_list is not None:
                updated_projects = [
                    p for p in updated_projects if p not in remove_project_list
                ]

            # Set to None if empty, otherwise keep the list
            updated_projects = updated_projects if len(updated_projects) > 0 else None

        real_cloned_from_id: Optional[EntityId] = (
            ID_MAP_REPO.get_real_id("tasks", cloned_from_id)
            if cloned_from_id is not None
            else None
        )
        real_timespan_id: Optional[EntityId] = (
            ID_MAP_REPO.get_real_id("timespans", timespan_id)
            if timespan_id is not None
            else None
        )

        TASK_REPO.modify_task(
            real_id,
            real_cloned_from_id,
            real_timespan_id,
            description,
            updated_projects,
            updated_tags,
            priority,
            color,
            duration_from_str_optional(estimate),
            scheduled,
            due,
            started,
            completed,
            not_completed,
            cancelled,
            deleted,
            remove_cloned_from_id,
            remove_timespan_id,
            remove_description,
            remove_projects,
            remove_tags,
            remove_priority,
            remove_color,
            remove_estimate,
            remove_scheduled,
            remove_due,
            remove_started,
            remove_completed,
            remove_not_completed,
            remove_cancelled,
            remove_deleted,
        )

        task = TASK_REPO.get_task(real_id)
        modified_tasks.append(task)

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    if config["use_git_versioning"]:
        task_descriptions = [f"{t['id']}: {t['description']}" for t in modified_tasks]
        version.create_data_checkpoint(
            f"modify task(s): {', '.join(task_descriptions)}"
        )

    for task in modified_tasks:
        task_report.single_task_view(active_context_name, task, time_audits)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("complete, c", no_args_is_help=True)
def complete(id: str) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each task
    completed_tasks = []
    for task_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("tasks", task_id)

        TASK_REPO.modify_task(
            real_id,
            None,  # cloned_from_id
            None,  # timespan_id
            None,  # description
            None,  # projects
            None,  # tags
            None,  # priority
            None,  # color
            None,  # estimate
            None,  # scheduled
            None,  # due
            None,  # started
            now_utc(),  # completed
            None,  # not_completed
            None,  # cancelled
            None,  # deleted
            False,  # remove_cloned_from_id
            False,  # remove_timespan_id
            False,  # remove_description
            False,  # remove_projects
            False,  # remove_tags
            False,  # remove_priority
            False,  # remove_color
            False,  # remove_estimate
            False,  # remove_scheduled
            False,  # remove_due
            False,  # remove_started
            False,  # remove_completed
            False,  # remove_not_completed
            False,  # remove_cancelled
            False,  # remove_deleted
        )

        task = TASK_REPO.get_task(real_id)
        completed_tasks.append(task)

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    if config["use_git_versioning"]:
        task_descriptions = [f"{t['id']}: {t['description']}" for t in completed_tasks]
        version.create_data_checkpoint(
            f"complete task(s): {', '.join(task_descriptions)}"
        )

    for task in completed_tasks:
        task_report.single_task_view(active_context_name, task, time_audits)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("not-complete, nc", no_args_is_help=True)
def not_complete(id: str) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each task
    not_completed_tasks = []
    for task_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("tasks", task_id)

        TASK_REPO.modify_task(
            real_id,
            None,  # cloned_from_id
            None,  # timespan_id
            None,  # description
            None,  # projects
            None,  # tags
            None,  # priority
            None,  # color
            None,  # estimate
            None,  # scheduled
            None,  # due
            None,  # started
            None,  # completed
            now_utc(),  # not_completed
            None,  # cancelled
            None,  # deleted
            False,  # remove_cloned_from_id
            False,  # remove_timespan_id
            False,  # remove_description
            False,  # remove_projects
            False,  # remove_tags
            False,  # remove_priority
            False,  # remove_color
            False,  # remove_estimate
            False,  # remove_scheduled
            False,  # remove_due
            False,  # remove_started
            False,  # remove_completed
            False,  # remove_not_completed
            False,  # remove_cancelled
            False,  # remove_deleted
        )

        task = TASK_REPO.get_task(real_id)
        not_completed_tasks.append(task)

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    if config["use_git_versioning"]:
        task_descriptions = [
            f"{t['id']}: {t['description']}" for t in not_completed_tasks
        ]
        version.create_data_checkpoint(
            f"not-complete task(s): {', '.join(task_descriptions)}"
        )

    for task in not_completed_tasks:
        task_report.single_task_view(active_context_name, task, time_audits)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("cancel, ca", no_args_is_help=True)
def cancel(id: str) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each task
    cancelled_tasks = []
    for task_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("tasks", task_id)

        TASK_REPO.modify_task(
            real_id,
            None,  # cloned_from_id
            None,  # timespan_id
            None,  # description
            None,  # projects
            None,  # tags
            None,  # priority
            None,  # color
            None,  # estimate
            None,  # scheduled
            None,  # due
            None,  # started
            None,  # completed
            None,  # not_completed
            now_utc(),  # cancelled
            None,  # deleted
            False,  # remove_cloned_from_id
            False,  # remove_timespan_id
            False,  # remove_description
            False,  # remove_projects
            False,  # remove_tags
            False,  # remove_priority
            False,  # remove_color
            False,  # remove_estimate
            False,  # remove_scheduled
            False,  # remove_due
            False,  # remove_started
            False,  # remove_completed
            False,  # remove_not_completed
            False,  # remove_cancelled
            False,  # remove_deleted
        )

        task = TASK_REPO.get_task(real_id)
        cancelled_tasks.append(task)

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    if config["use_git_versioning"]:
        task_descriptions = [f"{t['id']}: {t['description']}" for t in cancelled_tasks]
        version.create_data_checkpoint(
            f"cancel task(s): {', '.join(task_descriptions)}"
        )

    for task in cancelled_tasks:
        task_report.single_task_view(active_context_name, task, time_audits)

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

    # Process each task
    deleted_tasks = []
    for task_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("tasks", task_id)

        TASK_REPO.modify_task(
            real_id,
            None,  # cloned_from_id
            None,  # timespan_id
            None,  # description
            None,  # projects
            None,  # tags
            None,  # priority
            None,  # color
            None,  # estimate
            None,  # scheduled
            None,  # due
            None,  # started
            None,  # completed
            None,  # not_completed
            None,  # cancelled
            now_utc(),  # deleted
            False,  # remove_cloned_from_id
            False,  # remove_timespan_id
            False,  # remove_description
            False,  # remove_projects
            False,  # remove_tags
            False,  # remove_priority
            False,  # remove_color
            False,  # remove_estimate
            False,  # remove_scheduled
            False,  # remove_due
            False,  # remove_started
            False,  # remove_completed
            False,  # remove_not_completed
            False,  # remove_cancelled
            False,  # remove_deleted
        )

        task = TASK_REPO.get_task(real_id)
        deleted_tasks.append(task)

    time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    if config["use_git_versioning"]:
        task_descriptions = [f"{t['id']}: {t['description']}" for t in deleted_tasks]
        version.create_data_checkpoint(
            f"delete task(s): {', '.join(task_descriptions)}"
        )

    for task in deleted_tasks:
        task_report.single_task_view(active_context_name, task, time_audits)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("clone, cl", no_args_is_help=True)
def clone(
    id: int,
    scheduled: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--scheduled",
            "-s",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    due: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--due",
            "-d",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
) -> None:
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    real_id = ID_MAP_REPO.get_real_id("tasks", id)
    config = CONFIGURATION_REPO.get_config()

    # Get the task to clone
    source_task = TASK_REPO.get_task(real_id)

    # Create new task with template
    cloned_task = get_task_template()

    # Copy all fields except scheduled and due
    cloned_task["cloned_from_id"] = real_id
    cloned_task["timespan_id"] = source_task["timespan_id"]
    cloned_task["description"] = source_task["description"]
    cloned_task["projects"] = source_task["projects"]
    cloned_task["tags"] = source_task["tags"]
    cloned_task["priority"] = source_task["priority"]
    cloned_task["estimate"] = source_task["estimate"]
    cloned_task["color"] = source_task["color"]
    cloned_task["scheduled"] = scheduled
    cloned_task["due"] = due

    # Save the cloned task
    new_id = TASK_REPO.save_new_task(cloned_task)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"clone task: {real_id} -> {new_id}: {cloned_task['description']}"
        )

    new_task = TASK_REPO.get_task(new_id)
    time_audits = TIME_AUDIT_REPO.get_all_time_audits()

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    task_report.single_task_view(active_context_name, new_task, time_audits)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("track, tr", no_args_is_help=True)
def track(
    id: str,
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
) -> None:
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    config = CONFIGURATION_REPO.get_config()

    # Parse comma-separated task IDs
    task_ids_parsed: list[int] = parse_id_list(id)
    real_ids: list[EntityId] = [
        ID_MAP_REPO.get_real_id("tasks", tid) for tid in task_ids_parsed
    ]

    # Look up all tasks and validate they exist
    tasks = [TASK_REPO.get_task(rid) for rid in real_ids]

    # Stop any currently open time audits
    all_time_audits = TIME_AUDIT_REPO.get_all_time_audits()
    current_time = now_utc()
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
                current_time,
                None,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
            )

    # Merge description from all tasks (or use --description flag)
    if description is not None:
        merged_description = description
    else:
        merged_description = " + ".join(
            task["description"] for task in tasks if task["description"] is not None
        )

    # Merge projects from all tasks (deduplicated)
    merged_projects: Optional[list[str]] = None
    for task in tasks:
        if task["projects"] is not None:
            if merged_projects is None:
                merged_projects = []
            for p in task["projects"]:
                if p not in merged_projects:
                    merged_projects.append(p)

    # Merge with context auto_added_projects
    if active_context["auto_added_projects"] is not None:
        if merged_projects is None:
            merged_projects = active_context["auto_added_projects"]
        else:
            for proj in active_context["auto_added_projects"]:
                if proj not in merged_projects:
                    merged_projects.append(proj)

    # Merge tags from all tasks (deduplicated)
    merged_tags: Optional[list[str]] = None
    for task in tasks:
        if task["tags"] is not None:
            if merged_tags is None:
                merged_tags = []
            for t in task["tags"]:
                if t not in merged_tags:
                    merged_tags.append(t)

    # Merge with context auto_added_tags
    if active_context["auto_added_tags"] is not None:
        if merged_tags is None:
            merged_tags = active_context["auto_added_tags"]
        else:
            for tag in active_context["auto_added_tags"]:
                if tag not in merged_tags:
                    merged_tags.append(tag)

    # Color: random if config enabled, otherwise None (don't take from tasks)
    time_audit_color = None
    if config["random_color_for_time_audits"]:
        time_audit_color = get_random_color()

    # Create new time audit
    time_audit = get_time_audit_template()
    time_audit["description"] = merged_description
    time_audit["projects"] = merged_projects
    time_audit["tags"] = merged_tags
    time_audit["color"] = time_audit_color
    time_audit["start"] = current_time
    time_audit["end"] = None
    time_audit["task_ids"] = real_ids

    time_audit_id = TIME_AUDIT_REPO.save_new_time_audit(time_audit)
    new_time_audit = TIME_AUDIT_REPO.get_time_audit(time_audit_id)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"track task: {','.join(str(rid) for rid in real_ids)}: {new_time_audit['description']}"
        )

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    time_audit_report.single_time_audit_report(active_context_name, new_time_audit)


@app.command("log, lg", no_args_is_help=True)
def log(
    task_id: int,
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
    Add a log entry for a task using an editor.
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    real_id = ID_MAP_REPO.get_real_id("tasks", task_id)
    config = CONFIGURATION_REPO.get_config()

    # Get the task
    task = TASK_REPO.get_task(real_id)

    # Open editor to get log text
    text = open_editor_for_text()

    if not text:
        raise typer.Exit(0)

    log_entry = create_log_for_entity(
        text=text,
        reference_type=EntityType.TASK,
        reference_id=real_id,
        entity_projects=task["projects"],
        entity_tags=task["tags"],
        timestamp=timestamp,
        add_tags=add_tags,
        color=None,
    )

    log_id = LOG_REPO.save_new_log(log_entry)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add log for task {real_id}: {log_id}")

    new_log = LOG_REPO.get_log(log_id)

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    log_report.single_log_report(active_context_name, new_log)


@app.command("note, nt", no_args_is_help=True)
def note(
    task_id: int,
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
    Add a note for a task
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    real_id = ID_MAP_REPO.get_real_id("tasks", task_id)
    config = CONFIGURATION_REPO.get_config()

    # Get the task
    task = TASK_REPO.get_task(real_id)

    # Open editor for note text
    text = open_editor_for_text()
    if text is None:
        typer.echo("Note creation cancelled (no text provided)")
        return

    # Start with task tags
    note_tags = task["tags"] if task["tags"] is not None else []
    note_tags = list(note_tags)  # Make a copy

    # Add context tags if they're not already in the task tags
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
    note_entry["projects"] = task["projects"]
    note_entry["tags"] = final_tags
    note_entry["timestamp"] = (
        python_to_pendulum_utc_optional(timestamp)
        if timestamp is not None
        else now_utc()
    )
    note_entry["reference_type"] = EntityType.TASK
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
        version.create_data_checkpoint(f"add note for task {real_id}: {note_id}")

    new_note = NOTE_REPO.get_note(note_id)

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    note_report.single_note_report(active_context_name, new_note)


@app.command("color, co")
def color() -> None:
    """Add random colors to all tasks with null colors."""
    from rich.console import Console

    version = Version()

    config = CONFIGURATION_REPO.get_config()
    console = Console()

    # Get all tasks
    all_tasks = TASK_REPO.get_all_tasks()

    # Filter tasks with null color
    tasks_without_color = [task for task in all_tasks if task["color"] is None]

    if len(tasks_without_color) == 0:
        console.print("[yellow]No tasks with null colors found.[/yellow]")
        return

    # Add random colors to tasks without color
    for task in tasks_without_color:
        TASK_REPO.modify_task(
            task["id"],  # type: ignore[arg-type]
            None,  # cloned_from_id
            None,  # timespan_id
            None,  # description
            None,  # projects
            None,  # tags
            None,  # priority
            get_random_color(),  # color
            None,  # estimate
            None,  # scheduled
            None,  # due
            None,  # started
            None,  # completed
            None,  # not_completed
            None,  # cancelled
            None,  # deleted
            False,  # remove_cloned_from_id
            False,  # remove_timespan_id
            False,  # remove_description
            False,  # remove_projects
            False,  # remove_tags
            False,  # remove_priority
            False,  # remove_color
            False,  # remove_estimate
            False,  # remove_scheduled
            False,  # remove_due
            False,  # remove_started
            False,  # remove_completed
            False,  # remove_not_completed
            False,  # remove_cancelled
            False,  # remove_deleted
        )

    console.print(
        f"[green]Added random colors to {len(tasks_without_color)} task(s).[/green]"
    )

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"add random colors to {len(tasks_without_color)} task(s)"
        )
