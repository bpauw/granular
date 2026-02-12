# SPDX-License-Identifier: MIT

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table
from yaml import dump

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper  # type: ignore[assignment]

from granular import configuration
from granular.repository.configuration import (
    CONFIGURATION_REPO,
)
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.service.project import sync_projects
from granular.service.tag import sync_tags
from granular.terminal.custom_typer import ContextAwareTyperGroup

app = typer.Typer(cls=ContextAwareTyperGroup, no_args_is_help=True)


@app.command("view, v")
def view() -> None:
    """Display current configuration settings."""
    config = CONFIGURATION_REPO.get_config()

    console = Console()
    table = Table()
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row(
        "use_git_versioning",
        "✓ Enabled" if config["use_git_versioning"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_tasks",
        "✓ Enabled" if config["random_color_for_tasks"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_time_audits",
        "✓ Enabled" if config["random_color_for_time_audits"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_events",
        "✓ Enabled" if config["random_color_for_events"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_timespans",
        "✓ Enabled" if config["random_color_for_timespans"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_logs",
        "✓ Enabled" if config["random_color_for_logs"] else "✗ Disabled",
    )
    table.add_row(
        "clear_ids_on_view",
        "✓ Enabled" if config["clear_ids_on_view"] else "✗ Disabled",
    )
    table.add_row("ical_sync_weeks", str(config["ical_sync_weeks"]))
    table.add_row(
        "ics_paths",
        ", ".join(config["ics_paths"]) if config["ics_paths"] else "None",
    )
    table.add_row("data_path", str(configuration.DATA_PATH))
    table.add_row(
        "external_notes_by_default",
        "✓ Enabled" if config.get("external_notes_by_default", False) else "✗ Disabled",
    )
    table.add_row(
        "note_timestamp_prefix_format",
        config.get("note_timestamp_prefix_format", "YYYYMMDD-HHmm"),
    )
    table.add_row(
        "sync_note_frontmatter",
        "✓ Enabled" if config.get("sync_note_frontmatter", True) else "✗ Disabled",
    )
    table.add_row(
        "cache_view",
        "✓ Enabled" if config.get("cache_view", True) else "✗ Disabled",
    )

    console.print(table)

    # Display note folders
    note_folders = config.get("note_folders", [])
    if note_folders:
        console.print("\n[bold]Note Folders[/bold]")
        folders_table = Table()
        folders_table.add_column("Name", style="cyan")
        folders_table.add_column("Base Path", style="magenta")
        for folder in note_folders:
            folders_table.add_row(folder["name"], folder["base_path"])
        console.print(folders_table)

    yaml_library_type = "untested"
    try:
        from yaml import CDumper as Dumper  # noqa: F401
        from yaml import CLoader as Loader  # noqa: F401

        yaml_library_type = "C"
    except ImportError:
        from yaml import Loader  # type: ignore[assignment] # noqa: F401

        yaml_library_type = "Python"

    console.print()
    console.print(f"YAML Library Type: {yaml_library_type}")


@app.command("set, s")
def set(
    ical_sync_weeks: Annotated[
        Optional[int],
        typer.Option(
            "--ical-sync-weeks",
            help="Number of weeks to sync for iCal integration",
        ),
    ] = None,
    ics_paths: Annotated[
        Optional[list[str]],
        typer.Option(
            "--ics-path",
            help="ICS file paths for iCal sync (accepts multiple)",
        ),
    ] = None,
    remove_ics_paths: Annotated[
        bool, typer.Option("--remove-ics-paths", help="Remove all ICS paths")
    ] = False,
    random_color_for_tasks: Annotated[
        Optional[bool],
        typer.Option(
            "--random-color-for-tasks/--no-random-color-for-tasks",
            help="Enable/disable random colors for new tasks",
        ),
    ] = None,
    random_color_for_time_audits: Annotated[
        Optional[bool],
        typer.Option(
            "--random-color-for-time-audits/--no-random-color-for-time-audits",
            help="Enable/disable random colors for new time audits",
        ),
    ] = None,
    random_color_for_events: Annotated[
        Optional[bool],
        typer.Option(
            "--random-color-for-events/--no-random-color-for-events",
            help="Enable/disable random colors for new events",
        ),
    ] = None,
    random_color_for_timespans: Annotated[
        Optional[bool],
        typer.Option(
            "--random-color-for-timespans/--no-random-color-for-timespans",
            help="Enable/disable random colors for new timespans",
        ),
    ] = None,
    random_color_for_logs: Annotated[
        Optional[bool],
        typer.Option(
            "--random-color-for-logs/--no-random-color-for-logs",
            help="Enable/disable random colors for new logs",
        ),
    ] = None,
    data_path: Annotated[
        Optional[str],
        typer.Option(
            "--data-path",
            help="Directory path for storing data files (None = current directory)",
        ),
    ] = None,
    remove_data_path: Annotated[
        bool,
        typer.Option(
            "--remove-data-path",
            help="Reset data path to None (use current directory)",
        ),
    ] = False,
    clear_ids_on_view: Annotated[
        Optional[bool],
        typer.Option(
            "--clear-ids-on-view/--no-clear-ids-on-view",
            help="Enable/disable automatic clearing of ID map before view commands",
        ),
    ] = None,
    external_notes_by_default: Annotated[
        Optional[bool],
        typer.Option(
            "--external-notes-by-default/--no-external-notes-by-default",
            help="Create external notes by default",
        ),
    ] = None,
    note_timestamp_prefix_format: Annotated[
        Optional[str],
        typer.Option(
            "--note-timestamp-prefix-format",
            help="Format string for note filename timestamp prefix (Pendulum format)",
        ),
    ] = None,
    sync_note_frontmatter: Annotated[
        Optional[bool],
        typer.Option(
            "--sync-note-frontmatter/--no-sync-note-frontmatter",
            help="Sync metadata to frontmatter in external notes",
        ),
    ] = None,
) -> None:
    """
    Update configuration settings.
    """

    # Update configuration
    CONFIGURATION_REPO.update_config(
        random_color_for_tasks=random_color_for_tasks,
        random_color_for_time_audits=random_color_for_time_audits,
        random_color_for_events=random_color_for_events,
        random_color_for_timespans=random_color_for_timespans,
        random_color_for_logs=random_color_for_logs,
        ical_sync_weeks=ical_sync_weeks,
        ics_paths=ics_paths,
        remove_ics_paths=remove_ics_paths,
        data_path=data_path,
        remove_data_path=remove_data_path,
        clear_ids_on_view=clear_ids_on_view,
        external_notes_by_default=external_notes_by_default,
        note_timestamp_prefix_format=note_timestamp_prefix_format,
        sync_note_frontmatter=sync_note_frontmatter,
    )

    # Display updated configuration
    config = CONFIGURATION_REPO.get_config()

    console = Console()
    console.print("[green]Configuration updated successfully![/green]\n")

    table = Table(title="Updated Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row(
        "random_color_for_tasks",
        "✓ Enabled" if config["random_color_for_tasks"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_time_audits",
        "✓ Enabled" if config["random_color_for_time_audits"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_events",
        "✓ Enabled" if config["random_color_for_events"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_timespans",
        "✓ Enabled" if config["random_color_for_timespans"] else "✗ Disabled",
    )
    table.add_row(
        "random_color_for_logs",
        "✓ Enabled" if config["random_color_for_logs"] else "✗ Disabled",
    )
    table.add_row(
        "clear_ids_on_view",
        "✓ Enabled" if config["clear_ids_on_view"] else "✗ Disabled",
    )
    table.add_row("ical_sync_weeks", str(config["ical_sync_weeks"]))
    table.add_row(
        "ics_paths",
        ", ".join(config["ics_paths"]) if config["ics_paths"] else "None",
    )
    table.add_row(
        "data_path",
        config["data_path"] if config["data_path"] else "None (current directory)",
    )

    console.print(table)


# Note folder management subcommand
note_folder_app = typer.Typer(no_args_is_help=True)
app.add_typer(note_folder_app, name="note-folder", help="Manage note folders")


@note_folder_app.command("add, a")
def add_note_folder(
    name: Annotated[str, typer.Option("--name", "-n", help="Folder name")],
    path: Annotated[str, typer.Option("--path", "-p", help="Base path for notes")],
) -> None:
    """Add a new note folder configuration."""
    config = CONFIGURATION_REPO.get_config()

    console = Console()
    note_folders = config.get("note_folders", [])
    if note_folders is None:
        note_folders = []

    # Check for duplicate name
    if any(f["name"] == name for f in note_folders):
        console.print(f"[red]Error: Folder '{name}' already exists[/red]")
        raise typer.Exit(1)

    # Add new folder
    note_folders.append({"name": name, "base_path": path})

    # Update config using internal access
    CONFIGURATION_REPO.config["note_folders"] = note_folders
    from granular import configuration as config_module

    config_module.APP_CONFIG_PATH.write_text(
        dump(CONFIGURATION_REPO.config, Dumper=Dumper)
    )

    console.print(f"[green]Added note folder '{name}' -> {path}[/green]")


@note_folder_app.command("list, ls")
def list_note_folders() -> None:
    """List all configured note folders."""
    config = CONFIGURATION_REPO.get_config()

    console = Console()
    note_folders = config.get("note_folders", [])

    if not note_folders:
        console.print("No note folders configured")
        return

    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Base Path", style="magenta")

    for folder in note_folders:
        table.add_row(folder["name"], folder["base_path"])

    console.print(table)


@note_folder_app.command("remove, rm")
def remove_note_folder(
    name: Annotated[str, typer.Argument(help="Folder name to remove")],
) -> None:
    """Remove a note folder from config."""
    config = CONFIGURATION_REPO.get_config()

    console = Console()
    note_folders = config.get("note_folders", [])
    if note_folders is None:
        note_folders = []

    original_count = len(note_folders)
    note_folders = [f for f in note_folders if f["name"] != name]

    if len(note_folders) == original_count:
        console.print(f"[red]Error: Folder '{name}' not found[/red]")
        raise typer.Exit(1)

    # Update config using internal access
    CONFIGURATION_REPO.config["note_folders"] = (
        note_folders if len(note_folders) > 0 else None
    )
    configuration.APP_CONFIG_PATH.write_text(
        dump(CONFIGURATION_REPO.config, Dumper=Dumper)
    )

    console.print(f"[green]Removed note folder '{name}'[/green]")


@note_folder_app.command("modify, m")
def modify_note_folder(
    name: Annotated[str, typer.Argument(help="Folder name to modify")],
    new_name: Annotated[Optional[str], typer.Option("--new-name")] = None,
    new_path: Annotated[Optional[str], typer.Option("--new-path")] = None,
) -> None:
    """Modify a note folder configuration."""
    config = CONFIGURATION_REPO.get_config()

    console = Console()
    note_folders = config.get("note_folders", [])
    if note_folders is None:
        note_folders = []

    folder = next((f for f in note_folders if f["name"] == name), None)
    if not folder:
        console.print(f"[red]Error: Folder '{name}' not found[/red]")
        raise typer.Exit(1)

    if new_name:
        # Check for duplicate name
        if any(f["name"] == new_name and f["name"] != name for f in note_folders):
            console.print(f"[red]Error: Folder '{new_name}' already exists[/red]")
            raise typer.Exit(1)
        folder["name"] = new_name
    if new_path:
        folder["base_path"] = new_path

    # Update config using internal access
    configuration.APP_CONFIG_PATH.write_text(
        dump(CONFIGURATION_REPO.config, Dumper=Dumper)
    )

    console.print(f"[green]Modified note folder '{name}'[/green]")


@app.command("resync-projects-and-tags, rpt")
def resync_projects_and_tags() -> None:
    """Clear and resync projects.yaml and tags.yaml from all entities."""
    console = Console()

    # Clear projects and tags
    PROJECT_REPO.set_all_projects([])
    TAG_REPO.set_all_tags([])

    # Resync from all entities
    sync_projects()
    sync_tags()

    # Flush changes to disk
    PROJECT_REPO.flush()
    TAG_REPO.flush()

    console.print("[green]Projects and tags resynced successfully![/green]")
