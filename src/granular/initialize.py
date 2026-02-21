# SPDX-License-Identifier: MIT

from typing import Any

from yaml import dump

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper  # type: ignore[assignment]

from granular import configuration, time
from granular import state as app_state
from granular.migrate import migrate
from granular.model.entity_id import generate_entity_id
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
    # Single-file data stores (not converted to directories)
    if not configuration.DATA_MIGRATE_PATH.is_file():
        configuration.DATA_MIGRATE_PATH.touch()
        migrate: dict[str, Any] = {"version": 0}
        configuration.DATA_MIGRATE_PATH.write_text(dump(migrate, Dumper=Dumper))
    if not configuration.DATA_CUSTOM_VIEWS_PATH.is_file():
        configuration.DATA_CUSTOM_VIEWS_PATH.touch()
        custom_views: dict[str, Any] = {"custom_views": []}
        configuration.DATA_CUSTOM_VIEWS_PATH.write_text(
            dump(custom_views, Dumper=Dumper)
        )
    if not configuration.DATA_TAGS_PATH.is_file():
        configuration.DATA_TAGS_PATH.touch()
        tags: dict[str, Any] = {"tags": []}
        configuration.DATA_TAGS_PATH.write_text(dump(tags, Dumper=Dumper))
    if not configuration.DATA_PROJECTS_PATH.is_file():
        configuration.DATA_PROJECTS_PATH.touch()
        projects: dict[str, Any] = {"projects": []}
        configuration.DATA_PROJECTS_PATH.write_text(dump(projects, Dumper=Dumper))
    if not configuration.DATA_ID_MAP_PATH.is_file():
        configuration.DATA_ID_MAP_PATH.touch()
        id_map: IdMap = get_id_map_template()
        configuration.DATA_ID_MAP_PATH.write_text(dump(id_map, Dumper=Dumper))

    # Directory-based entity stores (one file per entity)
    if not configuration.DATA_TASKS_DIR.is_dir():
        configuration.DATA_TASKS_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_TASKS_DIR / ".gitkeep").touch()
    if not configuration.DATA_TIME_AUDIT_DIR.is_dir():
        configuration.DATA_TIME_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_TIME_AUDIT_DIR / ".gitkeep").touch()
    if not configuration.DATA_EVENTS_DIR.is_dir():
        configuration.DATA_EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_EVENTS_DIR / ".gitkeep").touch()
    if not configuration.DATA_TIMESPANS_DIR.is_dir():
        configuration.DATA_TIMESPANS_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_TIMESPANS_DIR / ".gitkeep").touch()
    if not configuration.DATA_NOTES_DIR.is_dir():
        configuration.DATA_NOTES_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_NOTES_DIR / ".gitkeep").touch()
    if not configuration.DATA_LOGS_DIR.is_dir():
        configuration.DATA_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_LOGS_DIR / ".gitkeep").touch()
    if not configuration.DATA_TRACKERS_DIR.is_dir():
        configuration.DATA_TRACKERS_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_TRACKERS_DIR / ".gitkeep").touch()
    if not configuration.DATA_ENTRIES_DIR.is_dir():
        configuration.DATA_ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_ENTRIES_DIR / ".gitkeep").touch()

    # Contexts directory with default context
    if not configuration.DATA_CONTEXT_DIR.is_dir():
        configuration.DATA_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        (configuration.DATA_CONTEXT_DIR / ".gitkeep").touch()
        default_context_id = generate_entity_id()
        now = time.datetime_to_iso_str(time.now_utc())
        default_context: dict[str, Any] = {
            "id": default_context_id,
            "name": "default",
            "active": True,
            "auto_added_tags": None,
            "filter": None,
            "created": now,
            "updated": now,
        }
        context_file = configuration.DATA_CONTEXT_DIR / f"{default_context_id}.yaml"
        context_file.write_text(dump(default_context, Dumper=Dumper))


def __ensure_migrations() -> None:
    migrate.run_required_migrations()
