# SPDX-License-Identifier: MIT

from typing import Any

from yaml import dump

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper  # type: ignore[assignment]

from granular import configuration
from granular import state as app_state
from granular.migrate import migrate
from granular.model.id_map import IdMap
from granular.repository.configuration import CONFIGURATION_REPO
from granular.template.id_map import get_id_map_template
from granular.version.version import Version
from granular.view import state as view_state


def initialize() -> None:
    configuration.CONFIG_PATH.mkdir(parents=True, exist_ok=True)
    configuration.load_data_path_configuration()
    configuration.DATA_PATH.mkdir(parents=True, exist_ok=True)

    __ensure_config_files()
    __ensure_data_files()

    config = CONFIGURATION_REPO.get_config()
    if config["use_git_versioning"]:
        version = Version()
        version.initialize_data_versioning()
    view_state.set_show_header(config["show_header"])
    app_state.set_clear_ids(config["clear_ids_on_view"])

    __ensure_migrations()


def __ensure_config_files() -> None:
    if not configuration.APP_CONFIG_PATH.is_file():
        configuration.APP_CONFIG_PATH.touch()
        config: configuration.Configuration = {
            "use_git_versioning": False,
            "show_header": True,
            "ical_sync_weeks": 4,
            "ics_paths": None,
            "random_color_for_tasks": False,
            "random_color_for_time_audits": False,
            "random_color_for_events": False,
            "random_color_for_timespans": False,
            "random_color_for_logs": False,
            "data_path": None,
            "clear_ids_on_view": True,
            "cache_view": False,
        }
        configuration.APP_CONFIG_PATH.write_text(dump(config, Dumper=Dumper))


def __ensure_data_files() -> None:
    if not configuration.DATA_MIGRATE_PATH.is_file():
        configuration.DATA_MIGRATE_PATH.touch()
        migrate: dict[str, Any] = {"version": 0}
        configuration.DATA_MIGRATE_PATH.write_text(dump(migrate, Dumper=Dumper))
    if not configuration.DATA_TASKS_PATH.is_file():
        configuration.DATA_TASKS_PATH.touch()
        tasks: dict[str, Any] = {"next_id": 1, "tasks": []}
        configuration.DATA_TASKS_PATH.write_text(dump(tasks, Dumper=Dumper))
    if not configuration.DATA_TIME_AUDIT_PATH.is_file():
        configuration.DATA_TIME_AUDIT_PATH.touch()
        time_audits: dict[str, Any] = {"next_id": 1, "time_audits": []}
        configuration.DATA_TIME_AUDIT_PATH.write_text(dump(time_audits, Dumper=Dumper))
    if not configuration.DATA_EVENTS_PATH.is_file():
        configuration.DATA_EVENTS_PATH.touch()
        events: dict[str, Any] = {"next_id": 1, "events": []}
        configuration.DATA_EVENTS_PATH.write_text(dump(events, Dumper=Dumper))
    if not configuration.DATA_REPORTS_PATH.is_file():
        configuration.DATA_REPORTS_PATH.touch()
        reports: dict[str, Any] = {"reports": []}
        configuration.DATA_REPORTS_PATH.write_text(dump(reports, Dumper=Dumper))
    if not configuration.DATA_CONTEXT_PATH.is_file():
        configuration.DATA_CONTEXT_PATH.touch()
        contexts: dict[str, Any] = {
            "next_id": 2,
            "contexts": [
                {
                    "id": 1,
                    "name": "default",
                    "active": True,
                    "auto_added_tags": None,
                    "filter": None,
                }
            ],
        }
        configuration.DATA_CONTEXT_PATH.write_text(dump(contexts, Dumper=Dumper))
    if not configuration.DATA_TAGS_PATH.is_file():
        configuration.DATA_TAGS_PATH.touch()
        tags: dict[str, Any] = {"tags": []}
        configuration.DATA_TAGS_PATH.write_text(dump(tags, Dumper=Dumper))
    if not configuration.DATA_PROJECTS_PATH.is_file():
        configuration.DATA_PROJECTS_PATH.touch()
        projects: dict[str, Any] = {"projects": []}
        configuration.DATA_PROJECTS_PATH.write_text(dump(projects, Dumper=Dumper))
    if not configuration.DATA_TIMESPANS_PATH.is_file():
        configuration.DATA_TIMESPANS_PATH.touch()
        timespans: dict[str, Any] = {"next_id": 1, "timespans": []}
        configuration.DATA_TIMESPANS_PATH.write_text(dump(timespans, Dumper=Dumper))
    if not configuration.DATA_NOTES_PATH.is_file():
        configuration.DATA_NOTES_PATH.touch()
        notes: dict[str, Any] = {"next_id": 1, "notes": []}
        configuration.DATA_NOTES_PATH.write_text(dump(notes, Dumper=Dumper))
    if not configuration.DATA_LOGS_PATH.is_file():
        configuration.DATA_LOGS_PATH.touch()
        logs: dict[str, Any] = {"next_id": 1, "logs": []}
        configuration.DATA_LOGS_PATH.write_text(dump(logs, Dumper=Dumper))
    if not configuration.DATA_ID_MAP_PATH.is_file():
        configuration.DATA_ID_MAP_PATH.touch()
        id_map: IdMap = get_id_map_template()
        configuration.DATA_ID_MAP_PATH.write_text(dump(id_map, Dumper=Dumper))
    if not configuration.DATA_TRACKERS_PATH.is_file():
        configuration.DATA_TRACKERS_PATH.touch()
        trackers: dict[str, Any] = {"next_id": 1, "trackers": []}
        configuration.DATA_TRACKERS_PATH.write_text(dump(trackers, Dumper=Dumper))
    if not configuration.DATA_ENTRIES_PATH.is_file():
        configuration.DATA_ENTRIES_PATH.touch()
        entries: dict[str, Any] = {"next_id": 1, "entries": []}
        configuration.DATA_ENTRIES_PATH.write_text(dump(entries, Dumper=Dumper))


def __ensure_migrations() -> None:
    migrate.run_required_migrations()
