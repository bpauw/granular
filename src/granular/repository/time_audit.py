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
from granular.model.time_audit import TimeAudit
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO


class TimeAuditRepository:
    def __init__(self) -> None:
        self._time_audits: Optional[list[TimeAudit]] = None
        self._next_id: Optional[int] = None
        self.is_dirty = False

    @property
    def time_audits(self) -> list[TimeAudit]:
        if self._time_audits is None:
            self.__load_data()
        if self._time_audits is None:
            raise ValueError()
        return self._time_audits

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
        time_audits_data = load(
            configuration.DATA_TIME_AUDIT_PATH.read_text(), Loader=Loader
        )
        self._next_id = int(time_audits_data["next_id"])
        raw_time_audits = time_audits_data["time_audits"]
        self._time_audits = [
            self.__convert_time_audit_for_deserialization(time_audit)
            for time_audit in raw_time_audits
        ]

    def __save_data(self, time_audits: list[TimeAudit], next_id: int) -> None:
        serializable_time_audits = [
            self.__convert_time_audit_for_serialization(time_audit)
            for time_audit in deepcopy(time_audits)
        ]
        time_audits_data = {
            "next_id": next_id,
            "time_audits": serializable_time_audits,
        }
        configuration.DATA_TIME_AUDIT_PATH.write_text(
            dump(time_audits_data, Dumper=Dumper)
        )

    def flush(self) -> bool:
        if (
            self._time_audits is not None
            and self._next_id is not None
            and self.is_dirty
        ):
            self.__save_data(self._time_audits, self._next_id)
            return True
        return False

    def __get_next_id(self) -> int:
        return_id = self.next_id
        self.next_id += 1
        return return_id

    def __convert_time_audit_for_serialization(
        self, time_audit: TimeAudit
    ) -> dict[str, Any]:
        serializable_time_audit = cast(dict[str, Any], time_audit)
        serializable_time_audit["start"] = time.datetime_to_iso_str_optional(
            serializable_time_audit["start"]
        )
        serializable_time_audit["end"] = time.datetime_to_iso_str_optional(
            serializable_time_audit["end"]
        )
        serializable_time_audit["created"] = time.datetime_to_iso_str(
            serializable_time_audit["created"]
        )
        serializable_time_audit["updated"] = time.datetime_to_iso_str(
            serializable_time_audit["updated"]
        )
        serializable_time_audit["deleted"] = time.datetime_to_iso_str_optional(
            serializable_time_audit["deleted"]
        )
        return serializable_time_audit

    def __convert_time_audit_for_deserialization(
        self, time_audit: dict[str, Any]
    ) -> TimeAudit:
        deserializable_time_audit = time_audit
        deserializable_time_audit["start"] = time.datetime_from_str_optional(
            deserializable_time_audit["start"]
        )
        deserializable_time_audit["end"] = time.datetime_from_str_optional(
            deserializable_time_audit["end"]
        )
        deserializable_time_audit["created"] = time.datetime_from_str(
            deserializable_time_audit["created"]
        )
        deserializable_time_audit["updated"] = time.datetime_from_str(
            deserializable_time_audit["updated"]
        )
        deserializable_time_audit["deleted"] = time.datetime_from_str_optional(
            deserializable_time_audit["deleted"]
        )
        return cast(TimeAudit, deserializable_time_audit)

    def save_new_time_audit(self, time_audit: TimeAudit) -> int:
        self.is_dirty = True

        time_audit["id"] = self.__get_next_id()

        # Deduplicate tags
        if time_audit["tags"] is not None:
            time_audit["tags"] = list(dict.fromkeys(time_audit["tags"]))

        self.time_audits.append(time_audit)

        # Update tag and project caches (additive only)
        if time_audit["tags"] is not None:
            TAG_REPO.add_tags(time_audit["tags"])
        if time_audit["project"] is not None:
            PROJECT_REPO.add_project(time_audit["project"])

        return time_audit["id"]

    def modify_time_audit(
        self,
        id: int,
        description: Optional[str],
        project: Optional[str],
        tags: Optional[list[str]],
        color: Optional[str],
        start: Optional[pendulum.DateTime],
        end: Optional[pendulum.DateTime],
        task_id: Optional[int],
        deleted: Optional[pendulum.DateTime],
        remove_description: bool,
        remove_project: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_start: bool,
        remove_end: bool,
        remove_task_id: bool,
        remove_deleted: bool,
    ) -> None:
        self.is_dirty = True

        time_audit = [
            time_audit for time_audit in self.time_audits if time_audit["id"] == id
        ][0]
        # Set updated timestamp to current moment
        time_audit["updated"] = time.now_utc()
        if description is not None:
            time_audit["description"] = description
        if project is not None:
            time_audit["project"] = project
            PROJECT_REPO.add_project(project)
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            time_audit["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
        if color is not None:
            time_audit["color"] = color
        if start is not None:
            time_audit["start"] = start
        if end is not None:
            time_audit["end"] = end
        if task_id is not None:
            time_audit["task_id"] = task_id
        if deleted is not None:
            time_audit["deleted"] = deleted

        if remove_description:
            time_audit["description"] = None
        if remove_project:
            time_audit["project"] = None
        if remove_tags:
            time_audit["tags"] = None
        if remove_color:
            time_audit["color"] = None
        if remove_start:
            time_audit["start"] = None
        if remove_end:
            time_audit["end"] = None
        if remove_task_id:
            time_audit["task_id"] = None
        if remove_deleted:
            time_audit["deleted"] = None

    def get_all_time_audits(self) -> list[TimeAudit]:
        return deepcopy(self.time_audits)

    def get_active_time_audits(self) -> list[TimeAudit]:
        return [
            time_audit
            for time_audit in deepcopy(self.time_audits)
            if time_audit["deleted"] is None
        ]

    def get_time_audit(self, id: int) -> TimeAudit:
        return deepcopy(
            [time_audit for time_audit in self.time_audits if time_audit["id"] == id][0]
        )

    def get_adjacent_time_audit_before(self, id: int) -> Optional[TimeAudit]:
        """
        Get the time audit that comes immediately before the specified time audit,
        based on start time. Returns None if no previous audit exists.
        Only considers non-deleted time audits.
        """
        target_audit = self.get_time_audit(id)

        # Get all non-deleted time audits
        active_audits = [
            audit
            for audit in self.time_audits
            if audit["deleted"] is None and audit["id"] != id
        ]

        # Filter to only audits that start before or at the same time as target
        if target_audit["start"] is None:
            return None

        previous_audits = [
            audit
            for audit in active_audits
            if audit["start"] is not None and audit["start"] <= target_audit["start"]
        ]

        if not previous_audits:
            return None

        # Sort by start time descending and return the most recent one
        previous_audits.sort(
            key=lambda a: cast(pendulum.DateTime, a["start"]), reverse=True
        )
        return deepcopy(previous_audits[0])

    def get_adjacent_time_audit_after(self, id: int) -> Optional[TimeAudit]:
        """
        Get the time audit that comes immediately after the specified time audit,
        based on start time. Returns None if no next audit exists.
        Only considers non-deleted time audits.
        """
        target_audit = self.get_time_audit(id)

        # Get all non-deleted time audits
        active_audits = [
            audit
            for audit in self.time_audits
            if audit["deleted"] is None and audit["id"] != id
        ]

        # Filter to only audits that start after the target
        if target_audit["start"] is None:
            return None

        next_audits = [
            audit
            for audit in active_audits
            if audit["start"] is not None and audit["start"] > target_audit["start"]
        ]

        if not next_audits:
            return None

        # Sort by start time ascending and return the earliest one
        next_audits.sort(key=lambda a: cast(pendulum.DateTime, a["start"]))
        return deepcopy(next_audits[0])

    def move_adjacent_start(
        self, id: int, new_start: pendulum.DateTime
    ) -> tuple[TimeAudit, Optional[TimeAudit]]:
        """
        Move the start time of a time audit and adjust the end time of the
        previous adjacent audit (if one exists).

        Returns a tuple of (modified_audit, modified_adjacent_audit).
        The second element is None if no adjacent audit was modified.
        """
        self.is_dirty = True

        # Get the previous adjacent audit before modifying anything
        previous_audit = self.get_adjacent_time_audit_before(id)

        # Modify the target audit's start time
        self.modify_time_audit(
            id,
            None,
            None,
            None,
            None,
            new_start,
            None,
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
        )

        # If there's a previous audit, update its end time
        modified_previous = None
        if previous_audit is not None and previous_audit["id"] is not None:
            self.modify_time_audit(
                previous_audit["id"],
                None,
                None,
                None,
                None,
                None,
                new_start,
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
            )
            modified_previous = self.get_time_audit(previous_audit["id"])

        modified_target = self.get_time_audit(id)

        return (modified_target, modified_previous)

    def move_adjacent_end(
        self, id: int, new_end: pendulum.DateTime
    ) -> tuple[TimeAudit, Optional[TimeAudit]]:
        """
        Move the end time of a time audit and adjust the start time of the
        next adjacent audit (if one exists).

        Returns a tuple of (modified_audit, modified_adjacent_audit).
        The second element is None if no adjacent audit was modified.
        """
        self.is_dirty = True

        # Get the next adjacent audit before modifying anything
        next_audit = self.get_adjacent_time_audit_after(id)

        # Modify the target audit's end time
        self.modify_time_audit(
            id,
            None,
            None,
            None,
            None,
            None,
            new_end,
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
        )

        # If there's a next audit, update its start time
        modified_next = None
        if next_audit is not None and next_audit["id"] is not None:
            self.modify_time_audit(
                next_audit["id"],
                None,
                None,
                None,
                None,
                new_end,
                None,
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
            )
            modified_next = self.get_time_audit(next_audit["id"])

        modified_target = self.get_time_audit(id)

        return (modified_target, modified_next)


TIME_AUDIT_REPO = TimeAuditRepository()
