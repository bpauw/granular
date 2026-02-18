# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict

import pendulum

from granular.model.entity_id import EntityId


class Timespan(TypedDict):
    id: Optional[EntityId]
    entity_type: str
    description: Optional[str]
    created: pendulum.DateTime
    updated: pendulum.DateTime
    deleted: Optional[pendulum.DateTime]
    start: Optional[pendulum.DateTime]
    end: Optional[pendulum.DateTime]
    projects: Optional[list[str]]
    tags: Optional[list[str]]
    color: Optional[str]
    completed: Optional[pendulum.DateTime]
    not_completed: Optional[pendulum.DateTime]
    cancelled: Optional[pendulum.DateTime]
