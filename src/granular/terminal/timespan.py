# SPDX-License-Identifier: MIT

from typing import Annotated, Optional, cast

import pendulum
import typer

from granular.color import get_random_color
from granular.model.entity_id import EntityId
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.context import CONTEXT_REPO
from granular.repository.id_map import ID_MAP_REPO
from granular.repository.timespan import TIMESPAN_REPO
from granular.template.timespan import get_timespan_template
from granular.terminal.completion import complete_project, complete_tag
from granular.terminal.custom_typer import ContextAwareTyperGroup
from granular.terminal.parse import parse_datetime, parse_id_list
from granular.time import now_utc, python_to_pendulum_utc_optional
from granular.version.version import Version
from granular.view.terminal_dispatch import show_cached_dispatch
from granular.view.view.views import timespan as timespan_report

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
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
) -> None:
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    config = CONFIGURATION_REPO.get_config()

    timespan_tags = active_context["auto_added_tags"]
    if tags is not None:
        if timespan_tags is None:
            timespan_tags = tags
        else:
            timespan_tags += tags

    # Determine project: use provided project, or auto_added_project from context
    timespan_project = project
    if timespan_project is None and active_context["auto_added_project"] is not None:
        timespan_project = active_context["auto_added_project"]

    # Determine color: use provided color, or random if config enabled
    timespan_color = color
    if timespan_color is None and config.get("random_color_for_timespans"):
        timespan_color = get_random_color()

    timespan = get_timespan_template()
    timespan["description"] = description
    timespan["project"] = timespan_project
    timespan["tags"] = timespan_tags
    timespan["color"] = timespan_color
    timespan["start"] = python_to_pendulum_utc_optional(start)
    timespan["end"] = python_to_pendulum_utc_optional(end)

    id = TIMESPAN_REPO.save_new_timespan(timespan)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add timespan: {id}: {description}")

    new_timespan = TIMESPAN_REPO.get_timespan(id)

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    timespan_report.single_timespan_view(active_context_name, new_timespan)

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
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    completed: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--completed",
            "-co",
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
    remove_description: Annotated[
        bool, typer.Option("--remove-description", "-rd")
    ] = False,
    remove_project: Annotated[bool, typer.Option("--remove-project", "-rp")] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rT")] = False,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rcol")] = False,
    remove_start: Annotated[bool, typer.Option("--remove-start", "-rs")] = False,
    remove_end: Annotated[bool, typer.Option("--remove-end", "-re")] = False,
    remove_completed: Annotated[
        bool, typer.Option("--remove-completed", "-rco")
    ] = False,
    remove_not_completed: Annotated[
        bool, typer.Option("--remove-not-completed", "-rnc")
    ] = False,
    remove_cancelled: Annotated[
        bool, typer.Option("--remove-cancelled", "-rca")
    ] = False,
    remove_deleted: Annotated[bool, typer.Option("--remove-deleted", "-rdel")] = False,
) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each timespan
    modified_timespans = []
    for timespan_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("timespans", timespan_id)

        timespan = TIMESPAN_REPO.get_timespan(real_id)
        tags = timespan["tags"]

        if add_tags is not None:
            if tags is None:
                tags = add_tags
            else:
                tags += add_tags

        if remove_tag_list is not None:
            if tags is not None:
                tags = [tag for tag in tags if tag not in remove_tag_list]

        TIMESPAN_REPO.modify_timespan(
            real_id,
            description,
            project,
            tags,
            color,
            python_to_pendulum_utc_optional(start),
            python_to_pendulum_utc_optional(end),
            python_to_pendulum_utc_optional(completed),
            python_to_pendulum_utc_optional(not_completed),
            python_to_pendulum_utc_optional(cancelled),
            python_to_pendulum_utc_optional(deleted),
            remove_description,
            remove_project,
            remove_tags,
            remove_color,
            remove_start,
            remove_end,
            remove_completed,
            remove_not_completed,
            remove_cancelled,
            remove_deleted,
        )

        timespan = TIMESPAN_REPO.get_timespan(real_id)
        modified_timespans.append(timespan)

    if config["use_git_versioning"]:
        timespan_descriptions = [
            f"{ts['id']}: {ts['description']}" for ts in modified_timespans
        ]
        version.create_data_checkpoint(
            f"modify timespan(s): {', '.join(timespan_descriptions)}"
        )

    for timespan in modified_timespans:
        timespan_report.single_timespan_view(active_context_name, timespan)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("complete, co", no_args_is_help=True)
def complete(id: str) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each timespan
    completed_timespans = []
    for timespan_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("timespans", timespan_id)

        TIMESPAN_REPO.modify_timespan(
            real_id,
            None,  # description
            None,  # project
            None,  # tags
            None,  # color
            None,  # start
            None,  # end
            now_utc(),  # completed
            None,  # not_completed
            None,  # cancelled
            None,  # deleted
            False,  # remove_description
            False,  # remove_project
            False,  # remove_tags
            False,  # remove_color
            False,  # remove_start
            False,  # remove_end
            False,  # remove_completed
            False,  # remove_not_completed
            False,  # remove_cancelled
            False,  # remove_deleted
        )

        timespan = TIMESPAN_REPO.get_timespan(real_id)
        completed_timespans.append(timespan)

    if config["use_git_versioning"]:
        timespan_descriptions = [
            f"{ts['id']}: {ts['description']}" for ts in completed_timespans
        ]
        version.create_data_checkpoint(
            f"complete timespan(s): {', '.join(timespan_descriptions)}"
        )

    for timespan in completed_timespans:
        timespan_report.single_timespan_view(active_context_name, timespan)

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

    # Process each timespan
    deleted_timespans = []
    for timespan_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("timespans", timespan_id)

        TIMESPAN_REPO.modify_timespan(
            real_id,
            None,  # description
            None,  # project
            None,  # tags
            None,  # color
            None,  # start
            None,  # end
            None,  # completed
            None,  # not_completed
            None,  # cancelled
            now_utc(),  # deleted
            False,  # remove_description
            False,  # remove_project
            False,  # remove_tags
            False,  # remove_color
            False,  # remove_start
            False,  # remove_end
            False,  # remove_completed
            False,  # remove_not_completed
            False,  # remove_cancelled
            False,  # remove_deleted
        )

        timespan = TIMESPAN_REPO.get_timespan(real_id)
        deleted_timespans.append(timespan)

    if config["use_git_versioning"]:
        timespan_descriptions = [
            f"{ts['id']}: {ts['description']}" for ts in deleted_timespans
        ]
        version.create_data_checkpoint(
            f"delete timespan(s): {', '.join(timespan_descriptions)}"
        )

    for timespan in deleted_timespans:
        timespan_report.single_timespan_view(active_context_name, timespan)

    if config["cache_view"]:
        show_cached_dispatch()
