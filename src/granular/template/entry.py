# SPDX-License-Identifier: MIT

from granular.model.entity_id import UNSET_ENTITY_ID
from granular.model.entity_type import EntityType
from granular.model.entry import Entry
from granular.time import now_utc


def get_entry_template() -> Entry:
    now = now_utc()
    return {
        "id": None,
        "entity_type": EntityType.ENTRY,
        "tracker_id": UNSET_ENTITY_ID,  # Must be set
        "timestamp": now,
        "value": None,
        "projects": None,
        "tags": None,
        "color": None,
        "created": now,
        "updated": now,
        "deleted": None,
    }
