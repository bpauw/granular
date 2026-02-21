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
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.model.entity_id import EntityId, generate_entity_id


class EntryRepository:
    def __init__(self) -> None:
        self._entries: Optional[list[Entry]] = None
        self.is_dirty = False
        self._dirty_ids: set[str] = set()
        self._deleted_ids: set[str] = set()

    @property
    def entries(self) -> list[Entry]:
        if self._entries is None:
            self.__load_data()
        if self._entries is None:
            raise ValueError()
        return self._entries

    def __load_data(self) -> None:
        self._entries = []
        for file_path in configuration.DATA_ENTRIES_DIR.iterdir():
            if file_path.suffix != ".yaml" or file_path.name == ".gitkeep":
                continue
            raw_entry = load(file_path.read_text(), Loader=Loader)
            if raw_entry is not None:
                self._entries.append(
                    self.__convert_entry_for_deserialization(raw_entry)
                )

    def __save_data(self) -> None:
        # Write dirty entities
        for entry in self.entries:
            if entry["id"] in self._dirty_ids:
                serializable_entry = self.__convert_entry_for_serialization(
                    deepcopy(entry)
                )
                file_path = configuration.DATA_ENTRIES_DIR / f"{entry['id']}.yaml"
                file_path.write_text(dump(serializable_entry, Dumper=Dumper))

        # Remove hard-deleted entity files
        for entity_id in self._deleted_ids:
            file_path = configuration.DATA_ENTRIES_DIR / f"{entity_id}.yaml"
            if file_path.exists():
                file_path.unlink()

        # Clear tracking sets
        self._dirty_ids.clear()
        self._deleted_ids.clear()

    def flush(self) -> bool:
        if self._entries is not None and self.is_dirty:
            self.__save_data()
            self.is_dirty = False
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
        self._dirty_ids.add(entry["id"])

        # Update tag and project caches (additive only)
        if entry["tags"] is not None:
            TAG_REPO.add_tags(entry["tags"])
        if entry["projects"] is not None:
            PROJECT_REPO.add_projects(entry["projects"])

        return entry["id"]

    def modify_entry(
        self,
        id: EntityId,
        tracker_id: Optional[EntityId],
        timestamp: Optional[pendulum.DateTime],
        value: Optional[Union[int, float, str]],
        projects: Optional[list[str]],
        tags: Optional[list[str]],
        color: Optional[str],
        deleted: Optional[pendulum.DateTime],
        remove_value: bool,
        remove_projects: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_deleted: bool,
    ) -> None:
        self.is_dirty = True
        self._dirty_ids.add(id)

        entry = [entry for entry in self.entries if entry["id"] == id][0]
        # Set updated timestamp to current moment
        entry["updated"] = time.now_utc()
        if tracker_id is not None:
            entry["tracker_id"] = tracker_id
        if timestamp is not None:
            entry["timestamp"] = timestamp
        if value is not None:
            entry["value"] = value
        if projects is not None:
            deduplicated_projects = list(dict.fromkeys(projects))
            entry["projects"] = deduplicated_projects
            PROJECT_REPO.add_projects(deduplicated_projects)
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
        if remove_projects:
            entry["projects"] = None
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
