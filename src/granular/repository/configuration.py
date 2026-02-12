# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Optional

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration


class ConfigurationRepository:
    def __init__(self) -> None:
        self._config: Optional[configuration.Configuration] = None
        self.is_dirty = False

    @property
    def config(self) -> configuration.Configuration:
        if self._config is None:
            self.__load_data()
        if self._config is None:
            raise ValueError()
        return self._config

    def __load_data(self) -> None:
        self._config = load(configuration.APP_CONFIG_PATH.read_text(), Loader=Loader)

        if self._config is None:
            raise ValueError()

        # Migration: Add data_path field if it doesn't exist
        if "data_path" not in self._config:
            self._config["data_path"] = None
        # Migration: Add random_color_for_logs field if it doesn't exist
        if "random_color_for_logs" not in self._config:
            self._config["random_color_for_logs"] = False
        # Migration: Add clear_ids_on_view field if it doesn't exist
        if "clear_ids_on_view" not in self._config:
            self._config["clear_ids_on_view"] = True
        # Migration: Add note_folders field if it doesn't exist
        if "note_folders" not in self._config:
            self._config["note_folders"] = None
        # Migration: Add external_notes_by_default field if it doesn't exist
        if "external_notes_by_default" not in self._config:
            self._config["external_notes_by_default"] = False
        # Migration: Add note_timestamp_prefix_format field if it doesn't exist
        if "note_timestamp_prefix_format" not in self._config:
            self._config["note_timestamp_prefix_format"] = "YYYYMMDD-HHmm"
        # Migration: Add sync_note_frontmatter field if it doesn't exist
        if "sync_note_frontmatter" not in self._config:
            self._config["sync_note_frontmatter"] = True
        # Migration: Add random_color_for_trackers field if it doesn't exist
        if "random_color_for_trackers" not in self._config:
            self._config["random_color_for_trackers"] = False
        if "cache_view" not in self._config:
            self._config["cache_view"] = False

    def __save_data(self, config: configuration.Configuration) -> None:
        configuration.APP_CONFIG_PATH.write_text(dump(config, Dumper=Dumper))

    def flush(self) -> None:
        if self._config is not None and self.is_dirty:
            self.__save_data(self._config)

    def get_config(self) -> configuration.Configuration:
        return deepcopy(self.config)

    def update_config(
        self,
        use_git_versioning: Optional[bool] = None,
        random_color_for_tasks: Optional[bool] = None,
        random_color_for_time_audits: Optional[bool] = None,
        random_color_for_events: Optional[bool] = None,
        random_color_for_timespans: Optional[bool] = None,
        random_color_for_logs: Optional[bool] = None,
        random_color_for_trackers: Optional[bool] = None,
        ical_sync_weeks: Optional[int] = None,
        ics_paths: Optional[list[str]] = None,
        remove_ics_paths: bool = False,
        data_path: Optional[str] = None,
        remove_data_path: bool = False,
        cache_view: Optional[bool] = None,
        clear_ids_on_view: Optional[bool] = None,
        external_notes_by_default: Optional[bool] = None,
        note_timestamp_prefix_format: Optional[str] = None,
        sync_note_frontmatter: Optional[bool] = None,
    ) -> None:
        self.is_dirty = True

        if use_git_versioning is not None:
            self.config["use_git_versioning"] = use_git_versioning
        if random_color_for_tasks is not None:
            self.config["random_color_for_tasks"] = random_color_for_tasks
        if random_color_for_time_audits is not None:
            self.config["random_color_for_time_audits"] = random_color_for_time_audits
        if random_color_for_events is not None:
            self.config["random_color_for_events"] = random_color_for_events
        if random_color_for_timespans is not None:
            self.config["random_color_for_timespans"] = random_color_for_timespans
        if random_color_for_logs is not None:
            self.config["random_color_for_logs"] = random_color_for_logs
        if random_color_for_trackers is not None:
            self.config["random_color_for_trackers"] = random_color_for_trackers
        if ical_sync_weeks is not None:
            self.config["ical_sync_weeks"] = ical_sync_weeks
        if ics_paths is not None:
            self.config["ics_paths"] = ics_paths
        if remove_ics_paths:
            self.config["ics_paths"] = None
        if data_path is not None:
            self.config["data_path"] = data_path
        if remove_data_path:
            self.config["data_path"] = None
        if cache_view is not None:
            self.config["cache_view"] = cache_view
        if clear_ids_on_view is not None:
            self.config["clear_ids_on_view"] = clear_ids_on_view
        if external_notes_by_default is not None:
            self.config["external_notes_by_default"] = external_notes_by_default
        if note_timestamp_prefix_format is not None:
            self.config["note_timestamp_prefix_format"] = note_timestamp_prefix_format
        if sync_note_frontmatter is not None:
            self.config["sync_note_frontmatter"] = sync_note_frontmatter


CONFIGURATION_REPO = ConfigurationRepository()
