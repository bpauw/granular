# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import NotRequired, Optional, TypedDict

from yaml import load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader  # type: ignore[assignment]
import platformdirs

APP_NAME = "granular"

CONFIG_PATH = platformdirs.user_config_path(APP_NAME)
APP_CONFIG_PATH = CONFIG_PATH / "config.yaml"

# These will be set dynamically by load_data_paths()
DATA_PATH: Path = platformdirs.user_data_path(APP_NAME)
DATA_MIGRATE_PATH: Path = DATA_PATH / "migrate.yaml"
DATA_TASKS_PATH: Path = DATA_PATH / "tasks.yaml"
DATA_TIME_AUDIT_PATH: Path = DATA_PATH / "time_audits.yaml"
DATA_EVENTS_PATH: Path = DATA_PATH / "events.yaml"
DATA_CONTEXT_PATH: Path = DATA_PATH / "contexts.yaml"
DATA_TAGS_PATH: Path = DATA_PATH / "tags.yaml"
DATA_PROJECTS_PATH: Path = DATA_PATH / "projects.yaml"
DATA_CUSTOM_VIEWS_PATH: Path = DATA_PATH / "custom-views.yaml"
DATA_TIMESPANS_PATH: Path = DATA_PATH / "timespans.yaml"
DATA_NOTES_PATH: Path = DATA_PATH / "notes.yaml"
DATA_LOGS_PATH: Path = DATA_PATH / "logs.yaml"
DATA_ID_MAP_PATH: Path = DATA_PATH / "id_map.yaml"
DATA_TRACKERS_PATH: Path = DATA_PATH / "trackers.yaml"
DATA_ENTRIES_PATH: Path = DATA_PATH / "entries.yaml"
DATA_DISPATCH_PATH: Path = DATA_PATH / "dispatch.yaml"


class NoteFolderConfig(TypedDict):
    name: str
    base_path: str


class Configuration(TypedDict):
    use_git_versioning: bool
    show_header: bool
    ical_sync_weeks: int
    ics_paths: Optional[list[str]]
    random_color_for_tasks: bool
    random_color_for_time_audits: bool
    random_color_for_events: bool
    random_color_for_timespans: bool
    random_color_for_logs: bool
    random_color_for_trackers: NotRequired[bool]
    data_path: Optional[str]
    clear_ids_on_view: bool
    cache_view: bool
    note_folders: NotRequired[Optional[list[NoteFolderConfig]]]
    external_notes_by_default: NotRequired[bool]
    note_timestamp_prefix_format: NotRequired[str]
    sync_note_frontmatter: NotRequired[bool]


def load_data_path_configuration() -> None:
    """
    Load the configuration and set the DATA_PATH variables dynamically.

    This must be called after the config file exists and before any
    repositories are instantiated.
    """
    global \
        DATA_PATH, \
        DATA_MIGRATE_PATH, \
        DATA_TASKS_PATH, \
        DATA_TIME_AUDIT_PATH, \
        DATA_EVENTS_PATH, \
        DATA_CONTEXT_PATH, \
        DATA_TAGS_PATH, \
        DATA_PROJECTS_PATH, \
        DATA_CUSTOM_VIEWS_PATH, \
        DATA_TIMESPANS_PATH, \
        DATA_NOTES_PATH, \
        DATA_LOGS_PATH, \
        DATA_ID_MAP_PATH, \
        DATA_TRACKERS_PATH, \
        DATA_ENTRIES_PATH, \
        DATA_DISPATCH_PATH

    if not APP_CONFIG_PATH.is_file():
        # Config doesn't exist yet, use defaults
        return

    config: Configuration = load(APP_CONFIG_PATH.read_text(), Loader=Loader)
    data_path_setting = config.get("data_path")

    # Resolve the data path
    if data_path_setting is not None:
        DATA_PATH = Path(data_path_setting)

        # Update all the data file paths
        DATA_MIGRATE_PATH = DATA_PATH / "migrate.yaml"
        DATA_TASKS_PATH = DATA_PATH / "tasks.yaml"
        DATA_TIME_AUDIT_PATH = DATA_PATH / "time_audits.yaml"
        DATA_EVENTS_PATH = DATA_PATH / "events.yaml"
        DATA_CONTEXT_PATH = DATA_PATH / "contexts.yaml"
        DATA_TAGS_PATH = DATA_PATH / "tags.yaml"
        DATA_PROJECTS_PATH = DATA_PATH / "projects.yaml"
        DATA_CUSTOM_VIEWS_PATH = DATA_PATH / "custom-views.yaml"
        DATA_TIMESPANS_PATH = DATA_PATH / "timespans.yaml"
        DATA_NOTES_PATH = DATA_PATH / "notes.yaml"
        DATA_LOGS_PATH = DATA_PATH / "logs.yaml"
        DATA_ID_MAP_PATH = DATA_PATH / "id_map.yaml"
        DATA_TRACKERS_PATH = DATA_PATH / "trackers.yaml"
        DATA_ENTRIES_PATH = DATA_PATH / "entries.yaml"
        DATA_DISPATCH_PATH = DATA_PATH / "dispatch.yaml"
