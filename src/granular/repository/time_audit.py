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
from granular.model.entity_id import EntityId, generate_entity_id


class TimeAuditRepository:
    def __init__(self) -> None:
        self._time_audits: Optional[list[TimeAudit]] = None
        self.is_dirty = False
        self._dirty_ids: set[str] = set()
        self._deleted_ids: set[str] = set()

    @property
    def time_audits(self) -> list[TimeAudit]:
        if self._time_audits is None:
            self.__load_data()
        if self._time_audits is None:
            raise ValueError()
        return self._time_audits

    def __load_data(self) -> None:
        self._time_audits = []
        for file_path in configuration.DATA_TIME_AUDIT_DIR.iterdir():
            if file_path.suffix != ".yaml" or file_path.name == ".gitkeep":
                continue
            raw_time_audit = load(file_path.read_text(), Loader=Loader)
            if raw_time_audit is not None:
                self._time_audits.append(
                    self.__convert_time_audit_for_deserialization(raw_time_audit)
                )

    def __save_data(self) -> None:
        # Write dirty entities
        for time_audit in self.time_audits:
            if time_audit["id"] in self._dirty_ids:
                serializable_time_audit = self.__convert_time_audit_for_serialization(
                    deepcopy(time_audit)
                )
                file_path = (
                    configuration.DATA_TIME_AUDIT_DIR / f"{time_audit['id']}.yaml"
                )
                file_path.write_text(dump(serializable_time_audit, Dumper=Dumper))

        # Remove hard-deleted entity files
        for entity_id in self._deleted_ids:
            file_path = configuration.DATA_TIME_AUDIT_DIR / f"{entity_id}.yaml"
            if file_path.exists():
                file_path.unlink()

        # Clear tracking sets
        self._dirty_ids.clear()
        self._deleted_ids.clear()

    def flush(self) -> bool:
        if self._time_audits is not None and self.is_dirty:
            self.__save_data()
            self.is_dirty = False
            return True
        return False

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

    def save_new_time_audit(self, time_audit: TimeAudit) -> EntityId:
        self.is_dirty = True

        time_audit["id"] = generate_entity_id()

        # Deduplicate tags
        if time_audit["tags"] is not None:
            time_audit["tags"] = list(dict.fromkeys(time_audit["tags"]))

        self.time_audits.append(time_audit)
        self._dirty_ids.add(time_audit["id"])

        # Update tag and project caches (additive only)
        if time_audit["tags"] is not None:
            TAG_REPO.add_tags(time_audit["tags"])
        if time_audit["projects"] is not None:
            PROJECT_REPO.add_projects(time_audit["projects"])

        return time_audit["id"]

    def modify_time_audit(
        self,
        id: EntityId,
        description: Optional[str],
        projects: Optional[list[str]],
        tags: Optional[list[str]],
        color: Optional[str],
        start: Optional[pendulum.DateTime],
        end: Optional[pendulum.DateTime],
        deleted: Optional[pendulum.DateTime],
        remove_description: bool,
        remove_projects: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_start: bool,
        remove_end: bool,
        remove_deleted: bool,
        add_task_ids: Optional[list[EntityId]] = None,
        remove_task_ids: Optional[list[EntityId]] = None,
        remove_all_task_ids: bool = False,
    ) -> None:
        self.is_dirty = True
        self._dirty_ids.add(id)

        time_audit = [
            time_audit for time_audit in self.time_audits if time_audit["id"] == id
        ][0]
        # Set updated timestamp to current moment
        time_audit["updated"] = time.now_utc()
        if description is not None:
            time_audit["description"] = description
        if projects is not None:
            deduplicated_projects = list(dict.fromkeys(projects))
            time_audit["projects"] = deduplicated_projects
            PROJECT_REPO.add_projects(deduplicated_projects)
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
        if deleted is not None:
            time_audit["deleted"] = deleted

        if remove_description:
            time_audit["description"] = None
        if remove_projects:
            time_audit["projects"] = None
        if remove_tags:
            time_audit["tags"] = None
        if remove_color:
            time_audit["color"] = None
        if remove_start:
            time_audit["start"] = None
        if remove_end:
            time_audit["end"] = None
        if remove_deleted:
            time_audit["deleted"] = None

        # Handle task_ids modifications
        if add_task_ids is not None:
            current = time_audit["task_ids"]
            if current is None:
                time_audit["task_ids"] = list(add_task_ids)
            else:
                combined = list(current)
                for tid in add_task_ids:
                    if tid not in combined:
                        combined.append(tid)
                time_audit["task_ids"] = combined

        if remove_task_ids is not None:
            current = time_audit["task_ids"]
            if current is not None:
                filtered = [tid for tid in current if tid not in remove_task_ids]
                time_audit["task_ids"] = filtered if len(filtered) > 0 else None

        if remove_all_task_ids:
            time_audit["task_ids"] = None

    def get_all_time_audits(self) -> list[TimeAudit]:
        return deepcopy(self.time_audits)

    def get_active_time_audits(self) -> list[TimeAudit]:
        return [
            time_audit
            for time_audit in deepcopy(self.time_audits)
            if time_audit["deleted"] is None
        ]

    def get_time_audit(self, id: EntityId) -> TimeAudit:
        return deepcopy(
            [time_audit for time_audit in self.time_audits if time_audit["id"] == id][0]
        )

    def get_adjacent_time_audit_before(self, id: EntityId) -> Optional[TimeAudit]:
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

    def get_adjacent_time_audit_after(self, id: EntityId) -> Optional[TimeAudit]:
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
        self, id: EntityId, new_start: pendulum.DateTime
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
        self, id: EntityId, new_end: pendulum.DateTime
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
