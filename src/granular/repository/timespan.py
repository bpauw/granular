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
from granular.model.timespan import Timespan
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.model.entity_id import EntityId, generate_entity_id


class TimespanRepository:
    def __init__(self) -> None:
        self._timespans: Optional[list[Timespan]] = None
        self.is_dirty = False
        self._dirty_ids: set[str] = set()
        self._deleted_ids: set[str] = set()

    @property
    def timespans(self) -> list[Timespan]:
        if self._timespans is None:
            self.__load_data()
        if self._timespans is None:
            raise ValueError()
        return self._timespans

    def __load_data(self) -> None:
        self._timespans = []
        for file_path in configuration.DATA_TIMESPANS_DIR.iterdir():
            if file_path.suffix != ".yaml" or file_path.name == ".gitkeep":
                continue
            raw_timespan = load(file_path.read_text(), Loader=Loader)
            if raw_timespan is not None:
                self._timespans.append(
                    self.__convert_timespan_for_deserialization(raw_timespan)
                )

    def __save_data(self) -> None:
        # Write dirty entities
        for timespan in self.timespans:
            if timespan["id"] in self._dirty_ids:
                serializable_timespan = self.__convert_timespan_for_serialization(
                    deepcopy(timespan)
                )
                file_path = configuration.DATA_TIMESPANS_DIR / f"{timespan['id']}.yaml"
                file_path.write_text(dump(serializable_timespan, Dumper=Dumper))

        # Remove hard-deleted entity files
        for entity_id in self._deleted_ids:
            file_path = configuration.DATA_TIMESPANS_DIR / f"{entity_id}.yaml"
            if file_path.exists():
                file_path.unlink()

        # Clear tracking sets
        self._dirty_ids.clear()
        self._deleted_ids.clear()

    def flush(self) -> bool:
        if self._timespans is not None and self.is_dirty:
            self.__save_data()
            self.is_dirty = False
            return True
        return False

    def __convert_timespan_for_serialization(
        self, timespan: Timespan
    ) -> dict[str, Any]:
        serializable_timespan = cast(dict[str, Any], timespan)
        serializable_timespan["created"] = time.datetime_to_iso_str(
            serializable_timespan["created"]
        )
        serializable_timespan["updated"] = time.datetime_to_iso_str(
            serializable_timespan["updated"]
        )
        serializable_timespan["deleted"] = time.datetime_to_iso_str_optional(
            serializable_timespan["deleted"]
        )
        serializable_timespan["start"] = time.datetime_to_iso_str_optional(
            serializable_timespan["start"]
        )
        serializable_timespan["end"] = time.datetime_to_iso_str_optional(
            serializable_timespan["end"]
        )
        serializable_timespan["completed"] = time.datetime_to_iso_str_optional(
            serializable_timespan["completed"]
        )
        serializable_timespan["not_completed"] = time.datetime_to_iso_str_optional(
            serializable_timespan["not_completed"]
        )
        serializable_timespan["cancelled"] = time.datetime_to_iso_str_optional(
            serializable_timespan["cancelled"]
        )
        return serializable_timespan

    def __convert_timespan_for_deserialization(
        self, timespan: dict[str, Any]
    ) -> Timespan:
        deserializable_timespan = timespan
        deserializable_timespan["created"] = time.datetime_from_str(
            deserializable_timespan["created"]
        )
        deserializable_timespan["updated"] = time.datetime_from_str(
            deserializable_timespan["updated"]
        )
        deserializable_timespan["deleted"] = time.datetime_from_str_optional(
            deserializable_timespan["deleted"]
        )
        deserializable_timespan["start"] = time.datetime_from_str_optional(
            deserializable_timespan["start"]
        )
        deserializable_timespan["end"] = time.datetime_from_str_optional(
            deserializable_timespan["end"]
        )
        deserializable_timespan["completed"] = time.datetime_from_str_optional(
            deserializable_timespan["completed"]
        )
        deserializable_timespan["not_completed"] = time.datetime_from_str_optional(
            deserializable_timespan["not_completed"]
        )
        deserializable_timespan["cancelled"] = time.datetime_from_str_optional(
            deserializable_timespan["cancelled"]
        )
        return cast(Timespan, deserializable_timespan)

    def save_new_timespan(self, timespan: Timespan) -> EntityId:
        self.is_dirty = True

        timespan["id"] = generate_entity_id()

        # Deduplicate tags
        if timespan["tags"] is not None:
            timespan["tags"] = list(dict.fromkeys(timespan["tags"]))

        self.timespans.append(timespan)
        self._dirty_ids.add(timespan["id"])

        # Update tag and project caches (additive only)
        if timespan["tags"] is not None:
            TAG_REPO.add_tags(timespan["tags"])
        if timespan["projects"] is not None:
            PROJECT_REPO.add_projects(timespan["projects"])

        return timespan["id"]

    def modify_timespan(
        self,
        id: EntityId,
        description: Optional[str],
        projects: Optional[list[str]],
        tags: Optional[list[str]],
        color: Optional[str],
        start: Optional[pendulum.DateTime],
        end: Optional[pendulum.DateTime],
        completed: Optional[pendulum.DateTime],
        not_completed: Optional[pendulum.DateTime],
        cancelled: Optional[pendulum.DateTime],
        deleted: Optional[pendulum.DateTime],
        remove_description: bool,
        remove_projects: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_start: bool,
        remove_end: bool,
        remove_completed: bool,
        remove_not_completed: bool,
        remove_cancelled: bool,
        remove_deleted: bool,
    ) -> None:
        self.is_dirty = True
        self._dirty_ids.add(id)

        timespan = [timespan for timespan in self.timespans if timespan["id"] == id][0]
        # Set updated timestamp to current moment
        timespan["updated"] = time.now_utc()
        if description is not None:
            timespan["description"] = description
        if projects is not None:
            deduplicated_projects = list(dict.fromkeys(projects))
            timespan["projects"] = deduplicated_projects
            PROJECT_REPO.add_projects(deduplicated_projects)
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            timespan["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
        if color is not None:
            timespan["color"] = color
        if start is not None:
            timespan["start"] = start
        if end is not None:
            timespan["end"] = end
        if completed is not None:
            timespan["completed"] = completed
        if not_completed is not None:
            timespan["not_completed"] = not_completed
        if cancelled is not None:
            timespan["cancelled"] = cancelled
        if deleted is not None:
            timespan["deleted"] = deleted

        if remove_description:
            timespan["description"] = None
        if remove_projects:
            timespan["projects"] = None
        if remove_tags:
            timespan["tags"] = None
        if remove_color:
            timespan["color"] = None
        if remove_start:
            timespan["start"] = None
        if remove_end:
            timespan["end"] = None
        if remove_completed:
            timespan["completed"] = None
        if remove_not_completed:
            timespan["not_completed"] = None
        if remove_cancelled:
            timespan["cancelled"] = None
        if remove_deleted:
            timespan["deleted"] = None

    def get_all_timespans(self) -> list[Timespan]:
        return deepcopy(self.timespans)

    def get_timespan(self, id: EntityId) -> Timespan:
        return deepcopy(
            [timespan for timespan in self.timespans if timespan["id"] == id][0]
        )


TIMESPAN_REPO = TimespanRepository()
