# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Any, Optional, cast

import pendulum
from yaml import dump, load

try:
    from yaml import CDumper as Dumper  # noqa: F401
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration, time
from granular.model.tracker import Tracker
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.model.entity_id import EntityId, generate_entity_id


class TrackerRepository:
    def __init__(self) -> None:
        self._trackers: Optional[list[Tracker]] = None
        self.is_dirty = False

    @property
    def trackers(self) -> list[Tracker]:
        if self._trackers is None:
            self.__load_data()
        if self._trackers is None:
            raise ValueError()
        return self._trackers

    def __load_data(self) -> None:
        trackers_data = load(
            configuration.DATA_TRACKERS_PATH.read_text(), Loader=Loader
        )
        raw_trackers = trackers_data["trackers"]
        self._trackers = [
            self.__convert_tracker_for_deserialization(tracker)
            for tracker in raw_trackers
        ]

    def __save_data(self, trackers: list[Tracker]) -> None:
        serializable_trackers = [
            self.__convert_tracker_for_serialization(tracker)
            for tracker in deepcopy(trackers)
        ]
        trackers_data = {"trackers": serializable_trackers}
        configuration.DATA_TRACKERS_PATH.write_text(dump(trackers_data, Dumper=Dumper))

    def flush(self) -> bool:
        if self._trackers is not None and self.is_dirty:
            self.__save_data(self._trackers)
            return True
        return False

    def __convert_tracker_for_serialization(self, tracker: Tracker) -> dict[str, Any]:
        serializable_tracker = cast(dict[str, Any], tracker)
        serializable_tracker["created"] = time.datetime_to_iso_str(
            serializable_tracker["created"]
        )
        serializable_tracker["updated"] = time.datetime_to_iso_str(
            serializable_tracker["updated"]
        )
        serializable_tracker["archived"] = time.datetime_to_iso_str_optional(
            serializable_tracker["archived"]
        )
        serializable_tracker["deleted"] = time.datetime_to_iso_str_optional(
            serializable_tracker["deleted"]
        )
        return serializable_tracker

    def __convert_tracker_for_deserialization(self, tracker: dict[str, Any]) -> Tracker:
        deserializable_tracker = tracker
        deserializable_tracker["created"] = time.datetime_from_str(
            deserializable_tracker["created"]
        )
        deserializable_tracker["updated"] = time.datetime_from_str(
            deserializable_tracker["updated"]
        )
        deserializable_tracker["archived"] = time.datetime_from_str_optional(
            deserializable_tracker["archived"]
        )
        deserializable_tracker["deleted"] = time.datetime_from_str_optional(
            deserializable_tracker["deleted"]
        )
        return cast(Tracker, deserializable_tracker)

    def save_new_tracker(self, tracker: Tracker) -> EntityId:
        self.is_dirty = True

        tracker["id"] = generate_entity_id()

        # Deduplicate tags
        if tracker["tags"] is not None:
            tracker["tags"] = list(dict.fromkeys(tracker["tags"]))

        self.trackers.append(tracker)

        # Update tag and project caches (additive only)
        if tracker["tags"] is not None:
            TAG_REPO.add_tags(tracker["tags"])
        if tracker["projects"] is not None:
            PROJECT_REPO.add_projects(tracker["projects"])

        return tracker["id"]

    def modify_tracker(
        self,
        id: EntityId,
        name: Optional[str],
        description: Optional[str],
        entry_type: Optional[str],
        value_type: Optional[str],
        unit: Optional[str],
        scale_min: Optional[int],
        scale_max: Optional[int],
        options: Optional[list[str]],
        projects: Optional[list[str]],
        tags: Optional[list[str]],
        color: Optional[str],
        archived: Optional[pendulum.DateTime],
        deleted: Optional[pendulum.DateTime],
        remove_description: bool,
        remove_unit: bool,
        remove_scale_min: bool,
        remove_scale_max: bool,
        remove_options: bool,
        remove_projects: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_archived: bool,
        remove_deleted: bool,
    ) -> None:
        self.is_dirty = True

        tracker = [tracker for tracker in self.trackers if tracker["id"] == id][0]
        # Set updated timestamp to current moment
        tracker["updated"] = time.now_utc()
        if name is not None:
            tracker["name"] = name
        if description is not None:
            tracker["description"] = description
        if entry_type is not None:
            tracker["entry_type"] = entry_type  # type: ignore[typeddict-item]
        if value_type is not None:
            tracker["value_type"] = value_type  # type: ignore[typeddict-item]
        if unit is not None:
            tracker["unit"] = unit
        if scale_min is not None:
            tracker["scale_min"] = scale_min
        if scale_max is not None:
            tracker["scale_max"] = scale_max
        if options is not None:
            tracker["options"] = options
        if projects is not None:
            deduplicated_projects = list(dict.fromkeys(projects))
            tracker["projects"] = deduplicated_projects
            PROJECT_REPO.add_projects(deduplicated_projects)
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            tracker["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
        if color is not None:
            tracker["color"] = color
        if archived is not None:
            tracker["archived"] = archived
        if deleted is not None:
            tracker["deleted"] = deleted

        if remove_description:
            tracker["description"] = None
        if remove_unit:
            tracker["unit"] = None
        if remove_scale_min:
            tracker["scale_min"] = None
        if remove_scale_max:
            tracker["scale_max"] = None
        if remove_options:
            tracker["options"] = None
        if remove_projects:
            tracker["projects"] = None
        if remove_tags:
            tracker["tags"] = None
        if remove_color:
            tracker["color"] = None
        if remove_archived:
            tracker["archived"] = None
        if remove_deleted:
            tracker["deleted"] = None

    def get_all_trackers(self) -> list[Tracker]:
        return deepcopy(self.trackers)

    def get_tracker(self, id: EntityId) -> Tracker:
        return deepcopy(
            [tracker for tracker in self.trackers if tracker["id"] == id][0]
        )


TRACKER_REPO = TrackerRepository()
