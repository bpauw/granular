# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Any, Optional, cast

import pendulum
from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration, time
from granular.model.log import Log
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.model.entity_id import EntityId, generate_entity_id


class LogRepository:
    def __init__(self) -> None:
        self._logs: Optional[list[Log]] = None
        self.is_dirty = False
        self._dirty_ids: set[str] = set()
        self._deleted_ids: set[str] = set()

    @property
    def logs(self) -> list[Log]:
        if self._logs is None:
            self.__load_data()
        if self._logs is None:
            raise ValueError()
        return self._logs

    def __load_data(self) -> None:
        self._logs = []
        for file_path in configuration.DATA_LOGS_DIR.iterdir():
            if file_path.suffix != ".yaml" or file_path.name == ".gitkeep":
                continue
            raw_log = load(file_path.read_text(), Loader=Loader)
            if raw_log is not None:
                self._logs.append(self.__convert_log_for_deserialization(raw_log))

    def __save_data(self) -> None:
        # Write dirty entities
        for log in self.logs:
            if log["id"] in self._dirty_ids:
                serializable_log = self.__convert_log_for_serialization(deepcopy(log))
                file_path = configuration.DATA_LOGS_DIR / f"{log['id']}.yaml"
                file_path.write_text(dump(serializable_log, Dumper=Dumper))

        # Remove hard-deleted entity files
        for entity_id in self._deleted_ids:
            file_path = configuration.DATA_LOGS_DIR / f"{entity_id}.yaml"
            if file_path.exists():
                file_path.unlink()

        # Clear tracking sets
        self._dirty_ids.clear()
        self._deleted_ids.clear()

    def flush(self) -> bool:
        if self._logs is not None and self.is_dirty:
            self.__save_data()
            self.is_dirty = False
            return True
        return False

    def __convert_log_for_serialization(self, log: Log) -> dict[str, Any]:
        serializable_log = cast(dict[str, Any], log)
        serializable_log["timestamp"] = time.datetime_to_iso_str_optional(
            serializable_log["timestamp"]
        )
        serializable_log["created"] = time.datetime_to_iso_str(
            serializable_log["created"]
        )
        serializable_log["updated"] = time.datetime_to_iso_str(
            serializable_log["updated"]
        )
        serializable_log["deleted"] = time.datetime_to_iso_str_optional(
            serializable_log["deleted"]
        )
        return serializable_log

    def __convert_log_for_deserialization(self, log: dict[str, Any]) -> Log:
        deserializable_log = log
        deserializable_log["timestamp"] = time.datetime_from_str_optional(
            deserializable_log["timestamp"]
        )
        deserializable_log["created"] = time.datetime_from_str(
            deserializable_log["created"]
        )
        deserializable_log["updated"] = time.datetime_from_str(
            deserializable_log["updated"]
        )
        deserializable_log["deleted"] = time.datetime_from_str_optional(
            deserializable_log["deleted"]
        )
        return cast(Log, deserializable_log)

    def save_new_log(self, log: Log) -> EntityId:
        self.is_dirty = True

        log["id"] = generate_entity_id()

        # Deduplicate tags
        if log["tags"] is not None:
            log["tags"] = list(dict.fromkeys(log["tags"]))

        self.logs.append(log)
        self._dirty_ids.add(log["id"])

        # Update tag and project caches (additive only)
        if log["tags"] is not None:
            TAG_REPO.add_tags(log["tags"])
        if log["projects"] is not None:
            PROJECT_REPO.add_projects(log["projects"])

        return log["id"]

    def modify_log(
        self,
        id: EntityId,
        reference_id: Optional[EntityId],
        reference_type: Optional[str],
        timestamp: Optional[pendulum.DateTime],
        text: Optional[str],
        projects: Optional[list[str]],
        tags: Optional[list[str]],
        color: Optional[str],
        deleted: Optional[pendulum.DateTime],
        remove_reference_id: bool,
        remove_reference_type: bool,
        remove_timestamp: bool,
        remove_text: bool,
        remove_projects: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_deleted: bool,
    ) -> None:
        self.is_dirty = True
        self._dirty_ids.add(id)

        log = [log for log in self.logs if log["id"] == id][0]
        # Set updated timestamp to current moment
        log["updated"] = time.now_utc()

        if reference_id is not None:
            log["reference_id"] = reference_id
        if reference_type is not None:
            log["reference_type"] = reference_type
        if timestamp is not None:
            log["timestamp"] = timestamp
        if text is not None:
            log["text"] = text
        if projects is not None:
            deduplicated_projects = list(dict.fromkeys(projects))
            log["projects"] = deduplicated_projects
            PROJECT_REPO.add_projects(deduplicated_projects)
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            log["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
        if color is not None:
            log["color"] = color
        if deleted is not None:
            log["deleted"] = deleted

        if remove_reference_id:
            log["reference_id"] = None
        if remove_reference_type:
            log["reference_type"] = None
        if remove_timestamp:
            log["timestamp"] = None
        if remove_text:
            log["text"] = None
        if remove_projects:
            log["projects"] = None
        if remove_tags:
            log["tags"] = None
        if remove_color:
            log["color"] = None
        if remove_deleted:
            log["deleted"] = None

    def get_all_logs(self) -> list[Log]:
        return deepcopy(self.logs)

    def get_log(self, id: EntityId) -> Log:
        return deepcopy([log for log in self.logs if log["id"] == id][0])


LOG_REPO = LogRepository()
