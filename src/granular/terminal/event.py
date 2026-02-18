# SPDX-License-Identifier: MIT

from typing import Annotated, Optional, cast

import icalevents.icalevents
import pendulum
import typer

from granular.color import get_random_color
from granular.model.entity_id import EntityId
from granular.model.entity_type import EntityType
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.context import CONTEXT_REPO
from granular.repository.event import EVENT_REPO
from granular.repository.id_map import ID_MAP_REPO
from granular.repository.log import LOG_REPO
from granular.repository.note import NOTE_REPO
from granular.service.log import create_log_for_entity
from granular.template.event import get_event_template
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
from granular.view.view.views import event as event_report
from granular.view.view.views import log as log_report
from granular.view.view.views import note as note_report

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


@app.command("add, a", no_args_is_help=True)
def add(
    title: Annotated[str, typer.Argument(help="event title")],
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
    location: Annotated[Optional[str], typer.Option("--location", "-l")] = None,
    projects: Annotated[
        Optional[list[str]],
        typer.Option(
            "--project",
            "-p",
            help="valid input: project.subproject (repeatable)",
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
            help="valid inputs: YYYY-MM-DD HH:mm, YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    all_day: Annotated[bool, typer.Option("--all-day", "-a")] = False,
    ical_source: Annotated[Optional[str], typer.Option("--ical-source")] = None,
    ical_uid: Annotated[Optional[str], typer.Option("--ical-uid")] = None,
) -> None:
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    config = CONFIGURATION_REPO.get_config()

    event_tags = active_context["auto_added_tags"]
    if tags is not None:
        if event_tags is None:
            event_tags = tags
        else:
            event_tags += tags

    # Determine projects: merge auto_added_projects from context with provided projects
    entity_projects = active_context["auto_added_projects"]
    if projects is not None:
        if entity_projects is None:
            entity_projects = projects
        else:
            entity_projects += projects

    # Determine color: use provided color, or random if config enabled
    event_color = color
    if event_color is None and config["random_color_for_events"]:
        event_color = get_random_color()

    event = get_event_template()
    event["title"] = title
    event["description"] = description
    event["location"] = location
    event["projects"] = entity_projects
    event["tags"] = event_tags
    event["color"] = event_color
    if start is not None:
        event["start"] = start.in_tz("UTC") or now_utc()
    else:
        # For all-day events without explicit start, use midnight of current day in local timezone
        if all_day:
            event["start"] = pendulum.now("local").start_of("day").in_tz("UTC")
        else:
            event["start"] = now_utc()
    event["end"] = end.in_tz("UTC") if end is not None else None
    event["all_day"] = all_day
    event["ical_source"] = ical_source
    event["ical_uid"] = ical_uid

    id = EVENT_REPO.save_new_event(event)
    new_event = EVENT_REPO.get_event(id)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add event: {id}: {new_event['title']}")

    event_report.single_event_view(active_context_name, new_event)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("modify, m", no_args_is_help=True)
def modify(
    id: str,
    title: Annotated[Optional[str], typer.Option("--title", "-t")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d")] = None,
    location: Annotated[Optional[str], typer.Option("--location", "-l")] = None,
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
            "-rT",
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
            help="valid inputs: YYYY-MM-DD HH:mm, YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    end: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--end",
            "-e",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD HH:mm, YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    all_day: Annotated[Optional[bool], typer.Option("--all-day", "-a")] = None,
    deleted: Annotated[
        Optional[pendulum.DateTime],
        typer.Option(
            "--deleted",
            "-del",
            parser=parse_datetime,
            help="valid inputs: YYYY-MM-DD, (H)H:mm, today, yesterday, tomorrow, or day offset like 1, -1",
        ),
    ] = None,
    ical_source: Annotated[Optional[str], typer.Option("--ical-source")] = None,
    ical_uid: Annotated[Optional[str], typer.Option("--ical-uid")] = None,
    remove_title: Annotated[bool, typer.Option("--remove-title", "-rt")] = False,
    remove_description: Annotated[
        bool, typer.Option("--remove-description", "-rd")
    ] = False,
    remove_location: Annotated[bool, typer.Option("--remove-location", "-rl")] = False,
    remove_projects: Annotated[
        bool, typer.Option("--remove-projects", "-rpjs", help="Clear all projects")
    ] = False,
    remove_tags: Annotated[bool, typer.Option("--remove-tags", "-rts")] = False,
    remove_color: Annotated[bool, typer.Option("--remove-color", "-rcol")] = False,
    remove_end: Annotated[bool, typer.Option("--remove-end", "-re")] = False,
    remove_deleted: Annotated[bool, typer.Option("--remove-deleted", "-rdel")] = False,
    remove_ical_source: Annotated[bool, typer.Option("--remove-ical-source")] = False,
    remove_ical_uid: Annotated[bool, typer.Option("--remove-ical-uid")] = False,
) -> None:
    config = CONFIGURATION_REPO.get_config()
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])

    # Parse ID list
    ids: list[int] = parse_id_list(id)

    # Process each event
    modified_events = []
    for event_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("events", event_id)

        # Handle tag modifications
        updated_tags = None
        if add_tags is not None or remove_tag_list is not None:
            event = EVENT_REPO.get_event(real_id)
            current_tags = event["tags"] if event["tags"] is not None else []
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
            event = EVENT_REPO.get_event(real_id)
            current_projects = (
                event["projects"] if event["projects"] is not None else []
            )
            updated_projects = list(current_projects)

            if add_projects is not None:
                updated_projects.extend(add_projects)

            if remove_project_list is not None:
                updated_projects = [
                    p for p in updated_projects if p not in remove_project_list
                ]

            # Set to None if empty, otherwise keep the list
            updated_projects = updated_projects if len(updated_projects) > 0 else None

        EVENT_REPO.modify_event(
            real_id,
            title,
            description,
            location,
            updated_projects,
            updated_tags,
            color,
            start,
            end,
            all_day,
            deleted,
            ical_source,
            ical_uid,
            remove_title,
            remove_description,
            remove_location,
            remove_projects,
            remove_tags,
            remove_color,
            remove_end,
            remove_deleted,
            remove_ical_source,
            remove_ical_uid,
        )

        event = EVENT_REPO.get_event(real_id)
        modified_events.append(event)

    if config["use_git_versioning"]:
        event_titles = [f"{e['id']}: {e['title']}" for e in modified_events]
        version.create_data_checkpoint(f"modify event(s): {', '.join(event_titles)}")

    for event in modified_events:
        event_report.single_event_view(active_context_name, event)

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

    # Process each event
    deleted_events = []
    for event_id in ids:
        real_id: EntityId = ID_MAP_REPO.get_real_id("events", event_id)

        EVENT_REPO.modify_event(
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
            False,
            False,
        )

        event = EVENT_REPO.get_event(real_id)
        deleted_events.append(event)

    if config["use_git_versioning"]:
        event_titles = [f"{e['id']}: {e['title']}" for e in deleted_events]
        version.create_data_checkpoint(f"delete event(s): {', '.join(event_titles)}")

    for event in deleted_events:
        event_report.single_event_view(active_context_name, event)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("sync-ics, si")
def sync_ics() -> None:
    """Sync events from iCal sources configured in config.ics_paths."""
    from pathlib import Path

    from rich.console import Console

    version = Version()

    config = CONFIGURATION_REPO.get_config()
    active_context = CONTEXT_REPO.get_active_context()
    console = Console()

    ics_paths = config["ics_paths"]
    if ics_paths is None or len(ics_paths) == 0:
        console.print("[yellow]No iCal sources configured in config.ics_paths[/yellow]")
        return

    sync_weeks = config["ical_sync_weeks"]
    start_date = pendulum.now("local").start_of("day")
    end_date = start_date.add(weeks=sync_weeks)

    events_created = 0
    events_updated = 0

    # Get auto-added tags from active context
    context_tags = active_context["auto_added_tags"]

    for ics_path in ics_paths:
        console.print(f"[cyan]Syncing from: {ics_path}[/cyan]")

        try:
            # Determine if this is a URL or file path
            is_url = ics_path.startswith("http://") or ics_path.startswith("https://")

            # Check if this is an iCloud URL (needs fix_apple=True)
            # fix_apple = "icloud.com" in ics_path.lower() if is_url else False
            fix_apple = True

            # Get events from the iCal source
            if is_url:
                ical_events = icalevents.icalevents.events(
                    url=ics_path,
                    start=start_date,
                    end=end_date,
                    fix_apple=fix_apple,
                )
            else:
                ical_events = icalevents.icalevents.events(
                    file=Path(ics_path),
                    start=start_date,
                    end=end_date,
                )

            for ical_event in ical_events:
                # Skip events without a start time
                if ical_event.start is None:
                    continue

                # Convert ical event times to UTC pendulum datetimes
                event_start = pendulum.instance(ical_event.start).in_tz("UTC")
                event_end = (
                    pendulum.instance(ical_event.end).in_tz("UTC")
                    if ical_event.end
                    else None
                )

                # Determine if it's an all-day event
                all_day = (
                    ical_event.all_day if hasattr(ical_event, "all_day") else False
                )

                # Check if event exists with matching ical_source, ical_uid, start, and end
                existing_event = EVENT_REPO.find_event_by_ical(
                    ics_path, ical_event.uid, event_start, event_end
                )

                if existing_event is not None:
                    # Merge existing tags with context tags
                    existing_tags = (
                        existing_event["tags"]
                        if existing_event["tags"] is not None
                        else []
                    )
                    merged_tags = list(
                        set(
                            existing_tags
                            + (context_tags if context_tags is not None else [])
                        )
                    )
                    updated_tags = merged_tags if len(merged_tags) > 0 else None

                    # Update existing event (excluding deleted and created)
                    EVENT_REPO.modify_event(
                        cast(EntityId, existing_event["id"]),
                        ical_event.summary,
                        ical_event.description,
                        ical_event.location,
                        None,  # projects
                        updated_tags,  # tags
                        None,  # color
                        event_start,
                        event_end,
                        all_day,
                        None,  # deleted
                        ics_path,  # ical_source
                        ical_event.uid,  # ical_uid
                        False,  # remove_title
                        False,  # remove_description
                        False,  # remove_location
                        False,  # remove_projects
                        False,  # remove_tags
                        False,  # remove_color
                        False,  # remove_end
                        False,  # remove_deleted
                        False,  # remove_ical_source
                        False,  # remove_ical_uid
                    )
                    events_updated += 1
                else:
                    # Create new event with context tags and optional random color
                    new_event = get_event_template()
                    new_event["title"] = ical_event.summary
                    new_event["description"] = ical_event.description
                    new_event["location"] = ical_event.location
                    new_event["start"] = event_start
                    new_event["end"] = event_end
                    new_event["all_day"] = all_day
                    new_event["ical_source"] = ics_path
                    new_event["ical_uid"] = ical_event.uid
                    new_event["tags"] = context_tags

                    # Apply auto_added_projects from context
                    if active_context["auto_added_projects"] is not None:
                        new_event["projects"] = active_context["auto_added_projects"]

                    # Apply random color if configured
                    if config["random_color_for_events"]:
                        new_event["color"] = get_random_color()

                    EVENT_REPO.save_new_event(new_event)
                    events_created += 1

        except Exception as e:
            console.print(f"[red]Error syncing {ics_path}: {e}[/red]")
            raise e

    console.print(
        f"[green]Sync complete: {events_created} created, {events_updated} updated[/green]"
    )

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"sync ics: {events_created} created, {events_updated} updated"
        )

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("hard-delete-ics-events, hd")
def hard_delete_ics_events() -> None:
    """Permanently delete all events imported from iCal sources."""
    from rich.console import Console

    version = Version()

    config = CONFIGURATION_REPO.get_config()
    console = Console()

    # Confirm with the user before proceeding
    console.print(
        "[yellow]WARNING: This will permanently delete all events with an iCal source.[/yellow]"
    )
    console.print("[yellow]This action cannot be undone.[/yellow]")

    confirm = typer.confirm("Are you sure you want to continue?")
    if not confirm:
        console.print("[cyan]Operation cancelled.[/cyan]")
        return

    deleted_count = EVENT_REPO.hard_delete_ical_events()

    console.print(f"[green]Successfully deleted {deleted_count} iCal events.[/green]")

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"hard delete ics events: {deleted_count} deleted"
        )

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("log, lg", no_args_is_help=True)
def log(
    event_id: int,
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
    Add a log entry for an event using an editor.
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    real_id = ID_MAP_REPO.get_real_id("events", event_id)
    config = CONFIGURATION_REPO.get_config()

    # Get the event
    event = EVENT_REPO.get_event(real_id)

    # Open editor to get log text
    text = open_editor_for_text()

    if not text:
        raise typer.Exit(0)

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    log_entry = create_log_for_entity(
        text=text,
        reference_type=EntityType.EVENT,
        reference_id=real_id,
        entity_projects=event["projects"],
        entity_tags=event["tags"],
        timestamp=timestamp,
        add_tags=add_tags,
        color=None,
    )

    log_id = LOG_REPO.save_new_log(log_entry)

    if config["use_git_versioning"]:
        version.create_data_checkpoint(f"add log for event {real_id}: {log_id}")

    new_log = LOG_REPO.get_log(log_id)

    log_report.single_log_report(active_context_name, new_log)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("note, nt", no_args_is_help=True)
def note(
    event_id: int,
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
    Add a note for an event
    """
    version = Version()

    active_context = CONTEXT_REPO.get_active_context()

    active_context_name = cast(str, active_context["name"])
    real_id = ID_MAP_REPO.get_real_id("events", event_id)
    config = CONFIGURATION_REPO.get_config()

    # Get the event
    event = EVENT_REPO.get_event(real_id)

    # Open editor for note text
    text = open_editor_for_text()
    if text is None:
        typer.echo("Note creation cancelled (no text provided)")
        return

    # Start with event tags
    note_tags = event["tags"] if event["tags"] is not None else []
    note_tags = list(note_tags)  # Make a copy

    # Add context tags if they're not already in the event tags
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
    note_entry["projects"] = event["projects"]
    note_entry["tags"] = final_tags
    note_entry["timestamp"] = (
        python_to_pendulum_utc_optional(timestamp)
        if timestamp is not None
        else now_utc()
    )
    note_entry["reference_type"] = EntityType.EVENT
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
        version.create_data_checkpoint(f"add note for event {real_id}: {note_id}")

    new_note = NOTE_REPO.get_note(note_id)

    if active_context_name is None:
        raise ValueError("context name cannot be None")

    note_report.single_note_report(active_context_name, new_note)

    if config["cache_view"]:
        show_cached_dispatch()


@app.command("color, co")
def color() -> None:
    """Add random colors to all events with null colors."""
    from rich.console import Console

    version = Version()

    config = CONFIGURATION_REPO.get_config()
    console = Console()

    # Get all events
    all_events = EVENT_REPO.get_all_events()

    # Filter events with null color
    events_without_color = [event for event in all_events if event["color"] is None]

    if len(events_without_color) == 0:
        console.print("[yellow]No events with null colors found.[/yellow]")
        return

    # Add random colors to events without color
    # Note: color command operates on real IDs directly since it works with all events from repository
    for event in events_without_color:
        EVENT_REPO.modify_event(
            event["id"],  # type: ignore[arg-type]
            None,  # title
            None,  # description
            None,  # location
            None,  # projects
            None,  # tags
            get_random_color(),  # color
            None,  # start
            None,  # end
            None,  # all_day
            None,  # deleted
            None,  # ical_source
            None,  # ical_uid
            False,  # remove_title
            False,  # remove_description
            False,  # remove_location
            False,  # remove_projects
            False,  # remove_tags
            False,  # remove_color
            False,  # remove_end
            False,  # remove_deleted
            False,  # remove_ical_source
            False,  # remove_ical_uid
        )

    console.print(
        f"[green]Added random colors to {len(events_without_color)} event(s).[/green]"
    )

    if config["use_git_versioning"]:
        version.create_data_checkpoint(
            f"add random colors to {len(events_without_color)} event(s)"
        )

    if config["cache_view"]:
        show_cached_dispatch()
