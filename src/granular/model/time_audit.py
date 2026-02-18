# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict

import pendulum

from granular.model.entity_id import EntityId


class TimeAudit(TypedDict):
    id: Optional[EntityId]
    entity_type: str
    description: Optional[str]
    projects: Optional[list[str]]
    tags: Optional[list[str]]
    color: Optional[str]
    start: Optional[pendulum.DateTime]
    end: Optional[pendulum.DateTime]
    task_id: Optional[EntityId]
    created: pendulum.DateTime
    updated: pendulum.DateTime
    deleted: Optional[pendulum.DateTime]
