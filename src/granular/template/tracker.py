# SPDX-License-Identifier: MIT

from granular.model.entity_type import EntityType
from granular.model.tracker import Tracker
from granular.time import now_utc


def get_tracker_template() -> Tracker:
    now = now_utc()
    return {
        "id": None,
        "entity_type": EntityType.TRACKER,
        "name": "",
        "description": None,
        "entry_type": "daily",
        "value_type": "checkin",
        "unit": None,
        "scale_min": None,
        "scale_max": None,
        "options": None,
        "projects": None,
        "tags": None,
        "color": None,
        "created": now,
        "updated": now,
        "archived": None,
        "deleted": None,
    }
