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
from granular.model.event import Event
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO


class EventRepository:
    def __init__(self) -> None:
        self._events: Optional[list[Event]] = None
        self._next_id: Optional[int] = None
        self.is_dirty = False

    @property
    def events(self) -> list[Event]:
        if self._events is None:
            self.__load_data()
        if self._events is None:
            raise ValueError()
        return self._events

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
        events_data = load(configuration.DATA_EVENTS_PATH.read_text(), Loader=Loader)
        self._next_id = int(events_data["next_id"])
        raw_events = events_data["events"]
        self._events = [
            self.__convert_event_for_deserialization(event) for event in raw_events
        ]

    def __save_data(self, events: list[Event], next_id: int) -> None:
        serializable_events = [
            self.__convert_event_for_serialization(event) for event in deepcopy(events)
        ]
        events_data = {
            "next_id": next_id,
            "events": serializable_events,
        }
        configuration.DATA_EVENTS_PATH.write_text(dump(events_data, Dumper=Dumper))

    def flush(self) -> bool:
        if self._events is not None and self._next_id is not None and self.is_dirty:
            self.__save_data(self._events, self._next_id)
            return True
        return False

    def __get_next_id(self) -> int:
        return_id = self.next_id
        self.next_id += 1
        return return_id

    def __convert_event_for_serialization(self, event: Event) -> dict[str, Any]:
        serializable_event = cast(dict[str, Any], event)
        serializable_event["start"] = time.datetime_to_iso_str(
            serializable_event["start"]
        )
        serializable_event["end"] = time.datetime_to_iso_str_optional(
            serializable_event["end"]
        )
        serializable_event["created"] = time.datetime_to_iso_str(
            serializable_event["created"]
        )
        serializable_event["updated"] = time.datetime_to_iso_str(
            serializable_event["updated"]
        )
        serializable_event["deleted"] = time.datetime_to_iso_str_optional(
            serializable_event["deleted"]
        )
        return serializable_event

    def __convert_event_for_deserialization(self, event: dict[str, Any]) -> Event:
        deserializable_event = event
        deserializable_event["start"] = time.datetime_from_str(
            deserializable_event["start"]
        )
        deserializable_event["end"] = time.datetime_from_str_optional(
            deserializable_event["end"]
        )
        deserializable_event["created"] = time.datetime_from_str(
            deserializable_event["created"]
        )
        deserializable_event["updated"] = time.datetime_from_str(
            deserializable_event["updated"]
        )
        deserializable_event["deleted"] = time.datetime_from_str_optional(
            deserializable_event["deleted"]
        )
        return cast(Event, deserializable_event)

    def save_new_event(self, event: Event) -> int:
        self.is_dirty = True

        event["id"] = self.__get_next_id()

        # Deduplicate tags
        if event["tags"] is not None:
            event["tags"] = list(dict.fromkeys(event["tags"]))

        self.events.append(event)

        # Update tag and project caches
        if event["tags"] is not None:
            TAG_REPO.add_tags(event["tags"])
        if event["project"] is not None:
            PROJECT_REPO.add_project(event["project"])

        return event["id"]

    def modify_event(
        self,
        id: int,
        title: Optional[str],
        description: Optional[str],
        location: Optional[str],
        project: Optional[str],
        tags: Optional[list[str]],
        color: Optional[str],
        start: Optional[pendulum.DateTime],
        end: Optional[pendulum.DateTime],
        all_day: Optional[bool],
        deleted: Optional[pendulum.DateTime],
        ical_source: Optional[str],
        ical_uid: Optional[str],
        remove_title: bool,
        remove_description: bool,
        remove_location: bool,
        remove_project: bool,
        remove_tags: bool,
        remove_color: bool,
        remove_end: bool,
        remove_deleted: bool,
        remove_ical_source: bool,
        remove_ical_uid: bool,
    ) -> None:
        self.is_dirty = True

        event = [event for event in self.events if event["id"] == id][0]
        # Set updated timestamp to current moment
        event["updated"] = time.now_utc()
        if title is not None:
            event["title"] = title
        if description is not None:
            event["description"] = description
        if location is not None:
            event["location"] = location
        if project is not None:
            event["project"] = project
            PROJECT_REPO.add_project(project)
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            event["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
        if color is not None:
            event["color"] = color
        if start is not None:
            event["start"] = start
        if end is not None:
            event["end"] = end
        if all_day is not None:
            event["all_day"] = all_day
        if deleted is not None:
            event["deleted"] = deleted

        if ical_source is not None:
            event["ical_source"] = ical_source
        if ical_uid is not None:
            event["ical_uid"] = ical_uid

        if remove_title:
            event["title"] = None
        if remove_description:
            event["description"] = None
        if remove_location:
            event["location"] = None
        if remove_project:
            event["project"] = None
        if remove_tags:
            event["tags"] = None
        if remove_color:
            event["color"] = None
        # Note: start cannot be removed as it's a required field
        if remove_end:
            event["end"] = None
        if remove_deleted:
            event["deleted"] = None
        if remove_ical_source:
            event["ical_source"] = None
        if remove_ical_uid:
            event["ical_uid"] = None

    def get_all_events(self) -> list[Event]:
        return deepcopy(self.events)

    def get_event(self, id: int) -> Event:
        return deepcopy([event for event in self.events if event["id"] == id][0])

    def find_event_by_ical(
        self,
        ical_source: str,
        ical_uid: str,
        start: Optional[pendulum.DateTime] = None,
        end: Optional[pendulum.DateTime] = None,
    ) -> Optional[Event]:
        """Find an event by its ical_source, ical_uid, and optionally start/end times.

        Parameters:
            ical_source: The iCal source URL or file path
            ical_uid: The iCal event UID
            start: Optional start datetime to match
            end: Optional end datetime to match

        Returns:
            Matching event or None
        """
        matching_events = [
            event
            for event in self.events
            if event["ical_source"] == ical_source
            and event["ical_uid"] == ical_uid
            and (start is None or event["start"] == start)
            and (end is None or event["end"] == end)
        ]
        if len(matching_events) == 0:
            return None
        return deepcopy(matching_events[0])

    def hard_delete_ical_events(self) -> int:
        """Permanently remove all events with a non-null ical_source.

        Returns:
            Number of events deleted
        """
        self.is_dirty = True

        initial_count = len(self.events)
        self._events = [event for event in self.events if event["ical_source"] is None]
        deleted_count = initial_count - len(self.events)

        return deleted_count


EVENT_REPO = EventRepository()
