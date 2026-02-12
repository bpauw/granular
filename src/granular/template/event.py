# SPDX-License-Identifier: MIT

from granular.model.entity_type import EntityType
from granular.model.event import Event
from granular.time import now_utc


def get_event_template() -> Event:
    now = now_utc()
    return {
        "id": None,
        "entity_type": EntityType.EVENT,
        "title": None,
        "description": None,
        "location": None,
        "project": None,
        "tags": None,
        "color": None,
        "start": now,
        "end": None,
        "all_day": False,
        "created": now,
        "updated": now,
        "deleted": None,
        "ical_source": None,
        "ical_uid": None,
    }
