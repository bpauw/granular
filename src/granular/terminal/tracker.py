# SPDX-License-Identifier: MIT

from typing import Annotated, Optional, cast

import pendulum
import typer

from granular.color import get_random_color
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.context import CONTEXT_REPO
from granular.repository.entry import ENTRY_REPO
from granular.repository.id_map import ID_MAP_REPO
from granular.repository.tracker import TRACKER_REPO
from granular.service.entry import (
    EntryValidationError,
    create_entry_for_tracker,
    parse_entry_value,
    validate_entry_allowed,
    validate_entry_value,
)
from granular.template.tracker import get_tracker_template
from granular.terminal.completion import complete_project, complete_tag
from granular.terminal.custom_typer import ContextAwareTyperGroup
from granular.terminal.parse import parse_datetime, parse_id_list
from granular.time import now_utc, python_to_pendulum_utc_optional
from granular.version.version import Version
from granular.view.terminal_dispatch import show_cached_dispatch
from granular.view.view.views import entry as entry_report
from granular.view.view.views import tracker as tracker_report

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


# ─────────────────────────────────────────────────────────────
# Tracker Management
# ─────────────────────────────────────────────────────────────


@app.command("add, a", no_args_is_help=True)
def add(
    name: str,
    entry_type: Annotated[
        str,
        typer.Option(
            "--type",
            "-t",
            help="intra_day, daily, weekly, monthly, quarterly",
        ),
    ] = "daily",
    value_type: Annotated[
        str,
        typer.Option(
            "--value",
            "-v",
            help="checkin, quantitative, multi_select, pips",
        ),
    ] = "checkin",
    unit: Annotated[
        Optional[str],
        typer.Option("--unit", "-u", help="Unit for quantitative trackers"),
    ] = None,
    scale_min: Annotated[
        Optional[int],
        typer.Option("--scale-min", help="Minimum value for scale-based multi_select"),
    ] = None,
    scale_max: Annotated[
        Optional[int],
        typer.Option("--scale-max", help="Maximum value for scale-based multi_select"),
    ] = None,
    options: Annotated[
        Optional[list[str]],
        typer.Option(
            "--option",
            "-o",
            help="Named options for multi_select (repeatable)",
        ),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d"),
    ] = None,
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
            "-tg",
            help="accepts multiple tag options",
            autocompletion=complete_tag,
        ),
    ] = None,
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
) -> None:
    """Create a new tracker."""
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])
    config = CONFIGURATION_REPO.get_config()

    # Validate entry_type
    valid_entry_types = ["intra_day", "daily", "weekly", "monthly", "quarterly"]
    if entry_type not in valid_entry_types:
        typer.echo(
            f"Invalid entry type: {entry_type}. Valid options: {', '.join(valid_entry_types)}"
        )
        raise typer.Exit(1)

    # Validate value_type
    valid_value_types = ["checkin", "quantitative", "multi_select", "pips"]
    if value_type not in valid_value_types:
        typer.echo(
            f"Invalid value type: {value_type}. Valid options: {', '.join(valid_value_types)}"
        )
        raise typer.Exit(1)

    # Merge tags with context auto_added_tags
    tracker_tags = active_context["auto_added_tags"]
    if tags is not None:
        if tracker_tags is None:
            tracker_tags = tags
        else:
            tracker_tags = list(tracker_tags) + tags

    # Determine project: use provided project, or auto_added_project from context
    tracker_project = project
    if tracker_project is None and active_context["auto_added_project"] is not None:
        tracker_project = active_context["auto_added_project"]

    # Determine color: use provided color, or random if config enabled
    tracker_color = color
    if tracker_color is None and config.get("random_color_for_trackers", False):
        tracker_color = get_random_color()

    tracker = get_tracker_template()
    tracker["name"] = name
    tracker["description"] = description
    tracker["entry_type"] = entry_type  # type: ignore[typeddict-item]
    tracker["value_type"] = value_type  # type: ignore[typeddict-item]
    tracker["unit"] = unit
    tracker["scale_min"] = scale_min
    tracker["scale_max"] = scale_max
    tracker["options"] = options
    tracker["project"] = tracker_project
    tracker["tags"] = tracker_tags
    tracker["color"] = tracker_color

    id = TRACKER_REPO.save_new_tracker(tracker)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add tracker: {id}: {name}")

    new_tracker = TRACKER_REPO.get_tracker(id)

    tracker_report.single_tracker_view(active_context_name, new_tracker)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("modify, m", no_args_is_help=True)
def modify(
    id: str,
    name: Annotated[Optional[str], typer.Option("--name", "-n")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
    entry_type: Annotated[
        Optional[str],
        typer.Option(
            "--type",
            "-t",
            help="intra_day, daily, weekly, monthly, quarterly",
        ),
    ] = None,
    value_type: Annotated[
        Optional[str],
        typer.Option(
            "--value",
            "-v",
            help="checkin, quantitative, multi_select, pips",
        ),
    ] = None,
    unit: Annotated[Optional[str], typer.Option("--unit", "-u")] = None,
    scale_min: Annotated[Optional[int], typer.Option("--scale-min")] = None,
    scale_max: Annotated[Optional[int], typer.Option("--scale-max")] = None,
    options: Annotated[
        Optional[list[str]],
        typer.Option("--option", "-o"),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            autocompletion=complete_project,
        ),
    ] = None,
    add_tags: Annotated[
        Optional[list[str]],
        typer.Option(
            "--add-tag",
            "-at",
            autocompletion=complete_tag,
        ),
    ] = None,
    remove_tag_list: Annotated[
        Optional[list[str]],
        typer.Option(
            "--remove-tag",
            "-rt",
            autocompletion=complete_tag,
        ),
    ] = None,
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    remove_description: Annotated[
        bool, typer.Option("--remove-description", "-rd")
    ] = False,
    remove_unit: Annotated[bool, typer.Option("--remove-unit", "-ru")] = False,
    remove_scale_min: Annotated[
        bool, typer.Option("--remove-scale-min", "-rsmin")
    ] = False,
    remove_scale_max: Annotated[
        bool, typer.Option("--remove-scale-max", "-rsmax")
    ] = False,
    remove_options: Annotated[bool, typer.Option("--remove-options", "-ro")] = False,
    remove_project: Annotated[bool, typer.Option("--remove-project", "-rp")] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rtgs")] = False,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rcol")] = False,
) -> None:
    """Modify a tracker."""
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    modified_trackers = []
    for tracker_id in ids:
        real_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)

        # Handle tag modifications
        updated_tags = None
        if add_tags is not None or remove_tag_list is not None:
            tracker = TRACKER_REPO.get_tracker(real_id)
            current_tags = tracker["tags"] if tracker["tags"] is not None else []
            updated_tags = list(current_tags)

            if add_tags is not None:
                updated_tags.extend(add_tags)

            if remove_tag_list is not None:
                updated_tags = [
                    tag for tag in updated_tags if tag not in remove_tag_list
                ]

            updated_tags = updated_tags if len(updated_tags) > 0 else None

        TRACKER_REPO.modify_tracker(
            real_id,
            name,
            description,
            entry_type,
            value_type,
            unit,
            scale_min,
            scale_max,
            options,
            project,
            updated_tags,
            color,
            None,  # archived
            None,  # deleted
            remove_description,
            remove_unit,
            remove_scale_min,
            remove_scale_max,
            remove_options,
            remove_project,
            remove_tags,
            remove_color,
            False,  # remove_archived
            False,  # remove_deleted
        )

        tracker = TRACKER_REPO.get_tracker(real_id)
        modified_trackers.append(tracker)

    if config["use_git_versioning"]:
        tracker_names = [f"{t['id']}: {t['name']}" for t in modified_trackers]
        version.create_data_checkpoint(f"modify tracker(s): {', '.join(tracker_names)}")

    for tracker in modified_trackers:
        tracker_report.single_tracker_view(active_context_name, tracker)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("delete, d", no_args_is_help=True)
def delete(id: str) -> None:
    """Soft-delete a tracker."""
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    ids: list[int] = parse_id_list(id)
    deleted_trackers = []

    for tracker_id in ids:
        real_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)

        TRACKER_REPO.modify_tracker(
            real_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,  # archived
            now_utc(),  # deleted
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,  # remove_archived
            False,  # remove_deleted
        )

        tracker = TRACKER_REPO.get_tracker(real_id)
        deleted_trackers.append(tracker)

    if config["use_git_versioning"]:
        tracker_names = [f"{t['id']}: {t['name']}" for t in deleted_trackers]
        version.create_data_checkpoint(f"delete tracker(s): {', '.join(tracker_names)}")

    for tracker in deleted_trackers:
        tracker_report.single_tracker_view(active_context_name, tracker)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("archive, ar", no_args_is_help=True)
def archive(id: str) -> None:
    """Archive a tracker (keeps history, hides from today view)."""
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    ids: list[int] = parse_id_list(id)
    archived_trackers = []

    for tracker_id in ids:
        real_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)

        TRACKER_REPO.modify_tracker(
            real_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            now_utc(),  # archived
            None,  # deleted
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,  # remove_archived
            False,  # remove_deleted
        )

        tracker = TRACKER_REPO.get_tracker(real_id)
        archived_trackers.append(tracker)

    if config["use_git_versioning"]:
        tracker_names = [f"{t['id']}: {t['name']}" for t in archived_trackers]
        version.create_data_checkpoint(
            f"archive tracker(s): {', '.join(tracker_names)}"
        )

    for tracker in archived_trackers:
        tracker_report.single_tracker_view(active_context_name, tracker)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("unarchive, ua", no_args_is_help=True)
def unarchive(id: str) -> None:
    """Unarchive a tracker."""
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    ids: list[int] = parse_id_list(id)
    unarchived_trackers = []

    for tracker_id in ids:
        real_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)

        TRACKER_REPO.modify_tracker(
            real_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,  # archived
            None,  # deleted
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            True,  # remove_archived
            False,  # remove_deleted
        )

        tracker = TRACKER_REPO.get_tracker(real_id)
        unarchived_trackers.append(tracker)

    if config["use_git_versioning"]:
        tracker_names = [f"{t['id']}: {t['name']}" for t in unarchived_trackers]
        version.create_data_checkpoint(
            f"unarchive tracker(s): {', '.join(tracker_names)}"
        )

    for tracker in unarchived_trackers:
        tracker_report.single_tracker_view(active_context_name, tracker)

    if config["cache_view"]:
        show_cached_dispatch()


# ─────────────────────────────────────────────────────────────
# Entry Management
# ─────────────────────────────────────────────────────────────


@app.command("entry, e", no_args_is_help=True)
def entry(
    tracker_id: int,
    value: Annotated[
        Optional[str],
        typer.Option(
            "--value",
            "-v",
            help="Value for quantitative, multi_select, or pips trackers",
        ),
    ] = None,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="Time of entry (default: now)",
        ),
    ] = None,
    date: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--date",
            "-d",
            parser=parse_datetime,
            help="Date of entry (default: today)",
        ),
    ] = None,
    add_tags: Annotated[
        Optional[list[str]],
        typer.Option(
            "--add-tag",
            "-at",
            help="Additional tags for this entry",
            autocompletion=complete_tag,
        ),
    ] = None,
) -> None:
    """Record an entry for a tracker."""
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    # Resolve tracker ID
    real_tracker_id: int = ID_MAP_REPO.get_real_id("trackers", tracker_id)
    tracker = TRACKER_REPO.get_tracker(real_tracker_id)

    # Determine timestamp
    entry_timestamp: pendulum.DateTime
    if timestamp is not None:
        entry_timestamp = cast(
            pendulum.DateTime, python_to_pendulum_utc_optional(timestamp)
        )
    elif date is not None:
        # Use date with current time
        entry_timestamp = cast(pendulum.DateTime, python_to_pendulum_utc_optional(date))
    else:
        entry_timestamp = now_utc()

    # Parse and validate value
    try:
        parsed_value = parse_entry_value(tracker, value)
        validate_entry_value(tracker, parsed_value)
    except EntryValidationError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    # Check if entry is allowed based on entry_type constraints
    existing_entries = ENTRY_REPO.get_entries_for_tracker(real_tracker_id)
    try:
        validate_entry_allowed(tracker, entry_timestamp, existing_entries)
    except EntryValidationError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    # Merge context auto_added_tags
    entry_add_tags = add_tags
    if active_context["auto_added_tags"] is not None:
        if entry_add_tags is None:
            entry_add_tags = active_context["auto_added_tags"]
        else:
            entry_add_tags = list(entry_add_tags) + [
                t for t in active_context["auto_added_tags"] if t not in entry_add_tags
            ]

    # Create the entry
    entry_obj = create_entry_for_tracker(
        tracker=tracker,
        timestamp=entry_timestamp,
        value=parsed_value,
        add_tags=entry_add_tags,
    )

    entry_id = ENTRY_REPO.save_new_entry(entry_obj)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"add entry for tracker {tracker['name']}: {entry_id}"
        )

    new_entry = ENTRY_REPO.get_entry(entry_id)

    entry_report.single_entry_view(active_context_name, new_entry, tracker)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("entry-modify, em", no_args_is_help=True)
def entry_modify(
    id: str,
    value: Annotated[
        Optional[str],
        typer.Option(
            "--value",
            "-v",
            help="New value for the entry",
        ),
    ] = None,
    timestamp: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--timestamp",
            "-ts",
            parser=parse_datetime,
            help="New timestamp for entry",
        ),
    ] = None,
    project: Annotated[
        Optional[str],
        typer.Option(
            "--project",
            "-p",
            autocompletion=complete_project,
        ),
    ] = None,
    add_tags: Annotated[
        Optional[list[str]],
        typer.Option(
            "--add-tag",
            "-at",
            autocompletion=complete_tag,
        ),
    ] = None,
    remove_tag_list: Annotated[
        Optional[list[str]],
        typer.Option(
            "--remove-tag",
            "-rt",
            autocompletion=complete_tag,
        ),
    ] = None,
    color: Annotated[Optional[str], typer.Option("--color", "-col")] = None,
    remove_value: Annotated[bool, typer.Option("--remove-value", "-rv")] = False,
    remove_project: Annotated[bool, typer.Option("--remove-project", "-rp")] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rtgs")] = False,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rcol")] = False,
) -> None:
    """Modify an entry."""
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    modified_entries = []
    for entry_id in ids:
        real_id: int = ID_MAP_REPO.get_real_id("entries", entry_id)
        entry_obj = ENTRY_REPO.get_entry(real_id)
        tracker = TRACKER_REPO.get_tracker(entry_obj["tracker_id"])

        # Parse and validate value if provided
        parsed_value = None
        if value is not None:
            try:
                parsed_value = parse_entry_value(tracker, value)
                validate_entry_value(tracker, parsed_value)
            except EntryValidationError as e:
                typer.echo(f"Error: {e}")
                raise typer.Exit(1)

        # Handle timestamp conversion
        entry_timestamp = None
        if timestamp is not None:
            entry_timestamp = cast(
                pendulum.DateTime, python_to_pendulum_utc_optional(timestamp)
            )

        # Handle tag modifications
        updated_tags = None
        if add_tags is not None or remove_tag_list is not None:
            current_tags = entry_obj["tags"] if entry_obj["tags"] is not None else []
            updated_tags = list(current_tags)

            if add_tags is not None:
                updated_tags.extend(add_tags)

            if remove_tag_list is not None:
                updated_tags = [
                    tag for tag in updated_tags if tag not in remove_tag_list
                ]

            updated_tags = updated_tags if len(updated_tags) > 0 else None

        ENTRY_REPO.modify_entry(
            real_id,
            None,  # tracker_id - not modifiable
            entry_timestamp,
            parsed_value,
            project,
            updated_tags,
            color,
            None,  # deleted
            remove_value,
            remove_project,
            remove_tags,
            remove_color,
            False,  # remove_deleted
        )

        modified_entry = ENTRY_REPO.get_entry(real_id)
        modified_entries.append((modified_entry, tracker))

    if config["use_git_versioning"]:
        entry_ids_str = ", ".join(str(e["id"]) for e, _ in modified_entries)
        version.create_data_checkpoint(f"modify entry(ies): {entry_ids_str}")

    for entry_obj, tracker in modified_entries:
        entry_report.single_entry_view(active_context_name, entry_obj, tracker)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("entry-delete, ed", no_args_is_help=True)
def entry_delete(
    entry_id: int,
) -> None:
    """Delete an entry."""
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()
    active_context_name = cast(str, active_context["name"])

    real_entry_id: int = ID_MAP_REPO.get_real_id("entries", entry_id)
    entry_obj = ENTRY_REPO.get_entry(real_entry_id)
    tracker = TRACKER_REPO.get_tracker(entry_obj["tracker_id"])

    ENTRY_REPO.modify_entry(
        real_entry_id,
        None,  # tracker_id
        None,  # timestamp
        None,  # value
        None,  # project
        None,  # tags
        None,  # color
        now_utc(),  # deleted
        False,  # remove_value
        False,  # remove_project
        False,  # remove_tags
        False,  # remove_color
        False,  # remove_deleted
    )

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"delete entry: {real_entry_id}")

    deleted_entry = ENTRY_REPO.get_entry(real_entry_id)

    entry_report.single_entry_view(active_context_name, deleted_entry, tracker)

    if config["cache_view"]:
        show_cached_dispatch()
