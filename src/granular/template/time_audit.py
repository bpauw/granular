# SPDX-License-Identifier: MIT

from granular.model.entity_type import EntityType
from granular.model.time_audit import TimeAudit
from granular.time import now_utc


def get_time_audit_template() -> TimeAudit:
    now = now_utc()
    return {
        "id": None,
        "entity_type": EntityType.TIME_AUDIT,
        "description": None,
        "projects": None,
        "tags": None,
        "color": None,
        "start": None,
        "end": None,
        "task_id": None,
        "created": now,
        "updated": now,
        "deleted": None,
    }
