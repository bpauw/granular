# SPDX-License-Identifier: MIT

from granular.model.entity_type import EntityType
from granular.model.task import Task
from granular.time import now_utc


def get_task_template() -> Task:
    now = now_utc()
    return {
        "id": None,
        "entity_type": EntityType.TASK,
        "cloned_from_id": None,
        "timespan_id": None,
        "description": None,
        "project": None,
        "tags": None,
        "priority": None,
        "estimate": None,
        "color": None,
        "created": now,
        "updated": now,
        "scheduled": None,
        "due": None,
        "started": None,
        "completed": None,
        "not_completed": None,
        "cancelled": None,
        "deleted": None,
    }
