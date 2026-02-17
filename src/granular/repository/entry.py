# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Any, Optional, Union, cast

import pendulum
from yaml import dump, load

try:
    from yaml import CDumper as Dumper  # noqa: F401
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration, time
from granular.model.entry import Entry
from granular.repository.tag import TAG_REPO
from granular.model.entity_id import EntityId, generate_entity_id


class EntryRepository:
    def __init__(self) -> None:
        self._entries: Optional[list[Entry]] = None
        self.is_dirty = False

    @property
    def entries(self) -> list[Entry]:
        if self._entries is None:
            self.__load_data()
        if self._entries is None:
            raise ValueError()
        return self._entries

    def __load_data(self) -> None:
        entries_data = load(configuration.DATA_ENTRIES_PATH.read_text(), Loader=Loader)
        raw_entries = entries_data["entries"]
        self._entries = [
            self.__convert_entry_for_deserialization(entry) for entry in raw_entries
        ]

    def __save_data(self, entries: list[Entry]) -> None:
        serializable_entries = [
            self.__convert_entry_for_serialization(entry) for entry in deepcopy(entries)
        ]
        entries_data = {"entries": serializable_entries}
        configuration.DATA_ENTRIES_PATH.write_text(dump(entries_data, Dumper=Dumper))

    def flush(self) -> bool:
        if self._entries is not None and self.is_dirty:
            self.__save_data(self._entries)
            return True
        return False

    def __convert_entry_for_serialization(self, entry: Entry) -> dict[str, Any]:
        serializable_entry = cast(dict[str, Any], entry)
        serializable_entry["timestamp"] = time.datetime_to_iso_str(
            serializable_entry["timestamp"]
        )
        serializable_entry["created"] = time.datetime_to_iso_str(
            serializable_entry["created"]
        )
        serializable_entry["updated"] = time.datetime_to_iso_str(
            serializable_entry["updated"]
        )
        serializable_entry["deleted"] = time.datetime_to_iso_str_optional(
            serializable_entry["deleted"]
        )
        return serializable_entry

    def __convert_entry_for_deserialization(self, entry: dict[str, Any]) -> Entry:
        deserializable_entry = entry
        deserializable_entry["timestamp"] = time.datetime_from_str(
            deserializable_entry["timestamp"]
        )
        deserializable_entry["created"] = time.datetime_from_str(
            deserializable_entry["created"]
        )
        deserializable_entry["updated"] = time.datetime_from_str(
            deserializable_entry["updated"]
        )
        deserializable_entry["deleted"] = time.datetime_from_str_optional(
            deserializable_entry["deleted"]
        )
        return cast(Entry, deserializable_entry)

    def save_new_entry(self, entry: Entry) -> EntityId:
        self.is_dirty = True

        entry["id"] = generate_entity_id()

        # Deduplicate tags
        if entry["tags"] is not None:
            entry["tags"] = list(dict.fromkeys(entry["tags"]))

        self.entries.append(entry)

        # Update tag cache (additive only)
        if entry["tags"] is not None:
            TAG_REPO.add_tags(entry["tags"])

        return entry["id"]

    def modify_entry(
        self,
        id: EntityId,
        tracker_id: Optional[EntityId],
        timestamp: Optional[pendulum.DateTime],
        value: Optional[Union[int, float, str]],
        project: Optional[str],
        tags: Optional[list[str]],
        color: Optional[str],
        deleted: Optional[pendulum.DateTime],
        remove_value: bool,
        remove_project: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_deleted: bool,
    ) -> None:
        self.is_dirty = True

        entry = [entry for entry in self.entries if entry["id"] == id][0]
        # Set updated timestamp to current moment
        entry["updated"] = time.now_utc()
        if tracker_id is not None:
            entry["tracker_id"] = tracker_id
        if timestamp is not None:
            entry["timestamp"] = timestamp
        if value is not None:
            entry["value"] = value
        if project is not None:
            entry["project"] = project
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            entry["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
        if color is not None:
            entry["color"] = color
        if deleted is not None:
            entry["deleted"] = deleted

        if remove_value:
            entry["value"] = None
        if remove_project:
            entry["project"] = None
        if remove_tags:
            entry["tags"] = None
        if remove_color:
            entry["color"] = None
        if remove_deleted:
            entry["deleted"] = None

    def get_all_entries(self) -> list[Entry]:
        return deepcopy(self.entries)

    def get_entry(self, id: EntityId) -> Entry:
        return deepcopy([entry for entry in self.entries if entry["id"] == id][0])

    def get_entries_for_tracker(self, tracker_id: EntityId) -> list[Entry]:
        return deepcopy(
            [entry for entry in self.entries if entry["tracker_id"] == tracker_id]
        )


ENTRY_REPO = EntryRepository()
