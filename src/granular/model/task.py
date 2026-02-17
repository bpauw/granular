# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict

import pendulum

from granular.model.entity_id import EntityId


class Task(TypedDict):
    id: Optional[EntityId]
    entity_type: str
    cloned_from_id: Optional[EntityId]
    timespan_id: Optional[EntityId]
    description: Optional[str]
    project: Optional[str]
    tags: Optional[list[str]]
    priority: Optional[int]
    estimate: Optional[pendulum.Duration]
    color: Optional[str]
    created: pendulum.DateTime
    updated: pendulum.DateTime
    scheduled: Optional[pendulum.DateTime]
    due: Optional[pendulum.DateTime]
    started: Optional[pendulum.DateTime]
    completed: Optional[pendulum.DateTime]
    not_completed: Optional[pendulum.DateTime]
    cancelled: Optional[pendulum.DateTime]
    deleted: Optional[pendulum.DateTime]
