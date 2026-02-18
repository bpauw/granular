# SPDX-License-Identifier: MIT

from granular.model.entity_type import EntityType
from granular.model.timespan import Timespan
from granular.time import now_utc


def get_timespan_template() -> Timespan:
    now = now_utc()
    return {
        "id": None,
        "entity_type": EntityType.TIMESPAN,
        "description": None,
        "created": now,
        "updated": now,
        "deleted": None,
        "start": None,
        "end": None,
        "projects": None,
        "tags": None,
        "color": None,
        "completed": None,
        "not_completed": None,
        "cancelled": None,
    }
