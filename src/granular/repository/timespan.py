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
from granular.repository.tag import TAG_REPO


class TimespanRepository:
    def __init__(self) -> None:
        self._timespans: Optional[list[Timespan]] = None
        self._next_id: Optional[int] = None
        self.is_dirty = False

    @property
    def timespans(self) -> list[Timespan]:
        if self._timespans is None:
            self.__load_data()
        if self._timespans is None:
            raise ValueError()
        return self._timespans

    @property
    def next_id(self) -> int:
        if self._next_id is None:
            self.__load_data()
        if self._next_id is None:
            raise ValueError()
        return self._next_id

    @next_id.setter
    def next_id(self, value: int) -> None:
        self._next_id = value

    def __load_data(self) -> None:
        timespans_data = load(
            configuration.DATA_TIMESPANS_PATH.read_text(), Loader=Loader
        )
        self._next_id = int(timespans_data["next_id"])
        raw_timespans = timespans_data["timespans"]
        self._timespans = [
            self.__convert_timespan_for_deserialization(timespan)
            for timespan in raw_timespans
        ]

    def __save_data(self, timespans: list[Timespan], next_id: int) -> None:
        serializable_timespans = [
            self.__convert_timespan_for_serialization(timespan)
            for timespan in deepcopy(timespans)
        ]
        timespans_data = {"next_id": next_id, "timespans": serializable_timespans}
        configuration.DATA_TIMESPANS_PATH.write_text(
            dump(timespans_data, Dumper=Dumper)
        )

    def flush(self) -> bool:
        if self._timespans is not None and self._next_id is not None and self.is_dirty:
            self.__save_data(self._timespans, self._next_id)
            return True
        return False

    def __get_next_id(self) -> int:
        return_id = self.next_id
        self.next_id += 1
        return return_id

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

    def save_new_timespan(self, timespan: Timespan) -> int:
        self.is_dirty = True

        timespan["id"] = self.__get_next_id()

        # Deduplicate tags
        if timespan["tags"] is not None:
            timespan["tags"] = list(dict.fromkeys(timespan["tags"]))

        self.timespans.append(timespan)

        # Update tag cache (additive only)
        if timespan["tags"] is not None:
            TAG_REPO.add_tags(timespan["tags"])

        return timespan["id"]

    def modify_timespan(
        self,
        id: int,
        description: Optional[str],
        project: Optional[str],
        tags: Optional[list[str]],
        color: Optional[str],
        start: Optional[pendulum.DateTime],
        end: Optional[pendulum.DateTime],
        completed: Optional[pendulum.DateTime],
        not_completed: Optional[pendulum.DateTime],
        cancelled: Optional[pendulum.DateTime],
        deleted: Optional[pendulum.DateTime],
        remove_description: bool,
        remove_project: bool,
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

        timespan = [timespan for timespan in self.timespans if timespan["id"] == id][0]
        # Set updated timestamp to current moment
        timespan["updated"] = time.now_utc()
        if description is not None:
            timespan["description"] = description
        if project is not None:
            timespan["project"] = project
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
        if remove_project:
            timespan["project"] = None
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

    def get_timespan(self, id: int) -> Timespan:
        return deepcopy(
            [timespan for timespan in self.timespans if timespan["id"] == id][0]
        )


TIMESPAN_REPO = TimespanRepository()
